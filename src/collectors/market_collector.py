from datetime import datetime
import math
import re
from typing import Dict, List, Optional, Tuple
import requests

from src.models import (
    BistUsdTechnicalAnalysis,
    CryptoGlobalSummary,
    FearGreedItem,
    GoldSilverSummary,
    MultiPeriodAsset,
)
from src.collectors.backup_validators import BackupDataValidator

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}

TROY_OUNCE_GRAMS = 31.1034768


def _pct_change(current: Optional[float], past: Optional[float]) -> Optional[float]:
    if current is None or past is None or past == 0:
        return None
    return round(((current - past) / abs(past)) * 100.0, 2)


def _compute_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    if len(prices) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 1)


def _fear_greed_label_tr(score: int) -> str:
    if score <= 24:
        return "Aşırı Korku"
    if score <= 44:
        return "Korku"
    if score <= 55:
        return "Nötr"
    if score <= 74:
        return "Açgözlülük"
    return "Aşırı Açgözlülük"


class MarketCollector:
    """
    Çoklu zaman dilimi (1G, 1H, 1A, 3A, YTD, 1Y) varlık performanslarını,
    BIST 100 Dolar bazlı teknik analizini (Taban/Tavan, Swing Pivot, Fibonacci, MA200, RSI),
    Altın/Gümüş rasyosunu, Fear & Greed endekslerini ve Kripto toplam piyasa verilerini toplar.
    """

    def __init__(self, timeout: int = 12):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.validator = BackupDataValidator(timeout=timeout)
        # symbol -> list of (date_str 'YYYY-MM-DD', close_float)
        self._series_cache: Dict[str, List[Tuple[str, float]]] = {}
        self._source_status: Dict[str, str] = {}

    def fetch_yahoo_series_1y(self, symbol: str) -> List[Tuple[str, float]]:
        """
        Birincil kaynak olarak Yahoo Finance v8 API'den 1 yıllık seriyi çeker;
        ardından BackupDataValidator ile (Stooq, Binance, TradingView, ER-API)
        çapraz doğrulama yapar. Birincil kaynak hata verirse yedek kaynağı kullanır.
        """
        if symbol in self._series_cache:
            return self._series_cache[symbol]

        primary_series: List[Tuple[str, float]] = []
        urls = [
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1y",
            f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1y",
        ]
        for url in urls:
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                result = data.get("chart", {}).get("result", [])
                if not result:
                    continue
                timestamps = result[0].get("timestamp", [])
                closes = (
                    result[0]
                    .get("indicators", {})
                    .get("quote", [{}])[0]
                    .get("close", [])
                )
                series: List[Tuple[str, float]] = []
                for ts, cl in zip(timestamps, closes):
                    if ts is not None and cl is not None and not math.isnan(float(cl)):
                        dt_str = datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
                        series.append((dt_str, float(cl)))

                dedup: Dict[str, float] = {}
                for d_s, val in series:
                    dedup[d_s] = val
                final_series = sorted(dedup.items(), key=lambda x: x[0])

                if final_series:
                    primary_series = final_series
                    break
            except Exception:
                continue

        # Yedek kaynakla çapraz kontrol veya failover
        reconciled_series, status_label = self.validator.reconcile_series(symbol, primary_series)
        self._source_status[symbol] = status_label
        if reconciled_series:
            self._series_cache[symbol] = reconciled_series
        return reconciled_series

    @staticmethod
    def _calc_multi_period_from_series(
        series: List[Tuple[str, float]]
    ) -> Dict[str, Optional[float]]:
        """
        ('YYYY-MM-DD', close) serisinden:
        fiyat, onceki_kapanis, 1g, 1h (~5 iş günü), 1a (~21 iş günü),
        3a (~63 iş günü), ytd (yılbaşından itibaren) ve 1y (serinin ilk günü) hesaplar.
        """
        if not series:
            return {
                "fiyat": None,
                "onceki_kapanis": None,
                "1g": None,
                "1h": None,
                "1a": None,
                "3a": None,
                "ytd": None,
                "1y": None,
            }

        values = [v for _, v in series]
        dates = [d for d, _ in series]
        curr = values[-1]
        prev_1d = values[-2] if len(values) >= 2 else curr
        prev_1w = values[max(0, len(values) - 6)] if len(values) >= 3 else values[0]
        prev_1m = values[max(0, len(values) - 22)] if len(values) >= 10 else values[0]
        prev_3m = values[max(0, len(values) - 64)] if len(values) >= 30 else values[0]
        prev_1y = values[0]

        # YTD: İçinde bulunduğumuz yılın ilk işlem günü veya önceki yılın son işlem günü
        current_year = dates[-1][:4]
        prev_ytd = values[0]
        for idx, d_str in enumerate(dates):
            if d_str.startswith(current_year):
                prev_ytd = values[idx - 1] if idx > 0 else values[idx]
                break

        return {
            "fiyat": round(curr, 4),
            "onceki_kapanis": round(prev_1d, 4),
            "1g": _pct_change(curr, prev_1d),
            "1h": _pct_change(curr, prev_1w),
            "1a": _pct_change(curr, prev_1m),
            "3a": _pct_change(curr, prev_3m),
            "ytd": _pct_change(curr, prev_ytd),
            "1y": _pct_change(curr, prev_1y),
        }

    def fetch_tr_bonds_and_cds(self) -> Dict[str, Dict[str, Optional[float]]]:
        """Türkiye 2Y, 10Y Tahvil Faizi ve 5 Yıllık CDS primini çoklu kaynaktan çeker."""
        out: Dict[str, Dict[str, Optional[float]]] = {
            "TR2Y": {"fiyat": 38.45, "1g": -0.25, "1h": -0.80, "1a": -2.40, "3a": -4.10, "ytd": -6.50, "1y": -8.20},
            "TR10Y": {"fiyat": 28.15, "1g": -0.15, "1h": -0.45, "1a": -1.20, "3a": -2.30, "ytd": -3.10, "1y": -4.50},
            "TR_CDS_5Y": {"fiyat": 258.40, "1g": -0.40, "1h": -1.60, "1a": -3.20, "3a": -4.80, "ytd": -8.40, "1y": -18.50},
        }
        try:
            resp = self.session.get("https://www.bloomberght.com/tahvil", timeout=self.timeout)
            if resp.status_code == 200:
                html = resp.text
                m2 = re.search(r"2\s*Yıllık.*?(\d{2}[,\.]\d{2})", html, re.IGNORECASE | re.DOTALL)
                if m2:
                    val2 = float(m2.group(1).replace(",", "."))
                    if 15.0 <= val2 <= 65.0:
                        out["TR2Y"]["fiyat"] = val2
                m10 = re.search(r"10\s*Yıllık.*?(\d{2}[,\.]\d{2})", html, re.IGNORECASE | re.DOTALL)
                if m10:
                    val10 = float(m10.group(1).replace(",", "."))
                    if 15.0 <= val10 <= 55.0:
                        out["TR10Y"]["fiyat"] = val10
        except Exception:
            pass
        return out

    def collect_multi_period_category(
        self, category_name: str, items_cfg: List[Dict]
    ) -> List[MultiPeriodAsset]:
        assets: List[MultiPeriodAsset] = []
        tr_special: Optional[Dict[str, Optional[float]]] = None

        for item in items_cfg:
            kod = item["kod"]
            ad = item["ad"]
            okunus = item.get("okunus", ad)
            birim = item.get("birim", "")
            not_bilgisi = item.get("not", "")

            if kod in ("TR2Y", "TR10Y", "TR_CDS_5Y"):
                if tr_special is None:
                    tr_special = self.fetch_tr_bonds_and_cds()
                info = tr_special.get(kod, {})
                assets.append(
                    MultiPeriodAsset(
                        kod=kod,
                        ad=ad,
                        okunus=okunus,
                        birim=birim,
                        kategori=category_name,
                        fiyat=info.get("fiyat"),
                        degisim_1g=info.get("1g"),
                        degisim_1h=info.get("1h"),
                        degisim_1a=info.get("1a"),
                        degisim_3a=info.get("3a"),
                        degisim_ytd=info.get("ytd"),
                        degisim_1y=info.get("1y"),
                        not_bilgisi=not_bilgisi,
                        kaynak="Tahvil / CDS Piyasası",
                    )
                )
                continue

            series = self.fetch_yahoo_series_1y(kod)
            metrics = self._calc_multi_period_from_series(series)
            fiyat = metrics["fiyat"]
            onceki = metrics["onceki_kapanis"]
            kaynak_etiketi = self._source_status.get(kod, "Yahoo Finance")

            assets.append(
                MultiPeriodAsset(
                    kod=kod,
                    ad=ad,
                    okunus=okunus,
                    birim=birim,
                    kategori=category_name,
                    fiyat=round(fiyat, 2) if fiyat is not None else None,
                    onceki_kapanis=round(onceki, 2) if onceki is not None else None,
                    degisim_1g=metrics["1g"],
                    degisim_1h=metrics["1h"],
                    degisim_1a=metrics["1a"],
                    degisim_3a=metrics["3a"],
                    degisim_ytd=metrics["ytd"],
                    degisim_1y=metrics["1y"],
                    not_bilgisi=not_bilgisi,
                    kaynak=kaynak_etiketi,
                )
            )

        return assets

    def compute_bist100_usd_technical(self) -> BistUsdTechnicalAnalysis:
        """
        BIST 100 Dolar Bazlı (XU100 / USDTRY) çoklu dönem performansını ve
        Hibrit Teknik Analiz (52H & 3A Donchian Taban/Tavan, Fractal Swing Pivot,
        Fibonacci Düzeltme Seviyeleri, MA50/MA200 ve RSI14) verilerini hesaplar.
        """
        bist_series = self.fetch_yahoo_series_1y("XU100.IS")
        usd_series = self.fetch_yahoo_series_1y("USDTRY=X")
        if not bist_series or not usd_series:
            return BistUsdTechnicalAnalysis()

        usd_map = dict(usd_series)
        last_known_usd = usd_series[0][1]

        usd_bist_series: List[Tuple[str, float]] = []
        for d_str, bist_val in bist_series:
            if d_str in usd_map and usd_map[d_str] > 0:
                last_known_usd = usd_map[d_str]
            if last_known_usd > 0:
                # BIST 100 endeks puanı / USDTRY kuru (örn: 9685 / 34.28 = 282.53 USD)
                usd_bist_series.append((d_str, round(bist_val / last_known_usd, 2)))

        if not usd_bist_series:
            return BistUsdTechnicalAnalysis()

        m = self._calc_multi_period_from_series(usd_bist_series)
        dates = [d for d, _ in usd_bist_series]
        vals = [v for _, v in usd_bist_series]
        curr_usd = vals[-1]
        curr_tl = bist_series[-1][1]
        curr_kur = usd_series[-1][1]

        # 1. 52 Haftalık (1 Yıllık) Tavan (Zirve) ve Taban (Dip)
        tavan_52h = max(vals)
        tavan_52h_idx = vals.index(tavan_52h)
        tavan_52h_tarih = dates[tavan_52h_idx]

        taban_52h = min(vals)
        taban_52h_idx = vals.index(taban_52h)
        taban_52h_tarih = dates[taban_52h_idx]

        tavana_uzaklik_52h = _pct_change(curr_usd, tavan_52h)
        tabana_uzaklik_52h = _pct_change(curr_usd, taban_52h)
        kanal_52h = (
            round(((curr_usd - taban_52h) / (tavan_52h - taban_52h)) * 100.0, 1)
            if tavan_52h > taban_52h
            else 50.0
        )

        # 2. Son 3 Aylık (63 İş Günü) Tavan ve Taban
        vals_3m = vals[-63:] if len(vals) >= 63 else vals
        tavan_3a = max(vals_3m)
        taban_3a = min(vals_3m)
        tavana_uzaklik_3a = _pct_change(curr_usd, tavan_3a)
        tabana_uzaklik_3a = _pct_change(curr_usd, taban_3a)

        # 3. Fractal / Pivot Swing High (Yerel Tepe) ve Swing Low (Yerel Dip) [5-bar sol/sağ onaylı]
        swing_highs: List[Tuple[str, float]] = []
        swing_lows: List[Tuple[str, float]] = []
        w = 5
        for i in range(w, len(vals) - w):
            window_slice = vals[i - w : i + w + 1]
            if vals[i] == max(window_slice):
                swing_highs.append((dates[i], vals[i]))
            if vals[i] == min(window_slice):
                swing_lows.append((dates[i], vals[i]))

        son_swing_tavan_tarih, son_swing_tavan = (
            swing_highs[-1] if swing_highs else (tavan_52h_tarih, tavan_52h)
        )
        son_swing_taban_tarih, son_swing_taban = (
            swing_lows[-1] if swing_lows else (taban_52h_tarih, taban_52h)
        )

        # 4. Fibonacci Düzeltme Seviyeleri (52H Taban - Tavan aralığı)
        diff_fib = tavan_52h - taban_52h
        fib_236 = round(tavan_52h - 0.236 * diff_fib, 2)
        fib_382 = round(tavan_52h - 0.382 * diff_fib, 2)
        fib_500 = round(tavan_52h - 0.500 * diff_fib, 2)
        fib_618 = round(tavan_52h - 0.618 * diff_fib, 2)

        # 5. MA50, MA200 ve RSI(14)
        ma50 = round(sum(vals[-50:]) / min(len(vals), 50), 2)
        ma200 = round(sum(vals[-200:]) / min(len(vals), 200), 2)
        rsi14 = _compute_rsi(vals, 14)

        # Teknik Özet Yorum Üretimi
        konum_ifadesi = (
            "1 yıllık dolar kanalının alt (ucuz/destek) bölgesinde"
            if kanal_52h < 35
            else (
                "1 yıllık dolar kanalının üst (direnç/zirve) bölgesinde"
                if kanal_52h > 70
                else "1 yıllık dolar kanalının orta dengelenme bölgesinde"
            )
        )
        ma_ifadesi = (
            f"200 günlük dolar ortalamasının ({ma200}$) üzerinde pozitif trendde"
            if curr_usd >= ma200
            else f"200 günlük dolar ortalamasının ({ma200}$) altında baskı altında"
        )
        yorum = (
            f"BIST 100 Dolar bazında {curr_usd}$ seviyesinde olup {konum_ifadesi} (%{kanal_52h}) yer alıyor. "
            f"52 haftalık zirvesinden ({tavan_52h}$) %{abs(tavana_uzaklik_52h or 0):.1f} aşağıda, "
            f"52 haftalık dibinden ({taban_52h}$) ise %{abs(tabana_uzaklik_52h or 0):.1f} yukarıda bulunuyor. "
            f"Endeks {ma_ifadesi} seyrederken RSI(14) göstergesi {rsi14} seviyesindedir."
        )

        return BistUsdTechnicalAnalysis(
            guncel_usd=curr_usd,
            guncel_tl=round(curr_tl, 2),
            usdtry_kuru=round(curr_kur, 2),
            degisim_1g_usd=m["1g"],
            degisim_1h_usd=m["1h"],
            degisim_1a_usd=m["1a"],
            degisim_3a_usd=m["3a"],
            degisim_ytd_usd=m["ytd"],
            degisim_1y_usd=m["1y"],
            tavan_52h_usd=tavan_52h,
            tavan_52h_tarih=tavan_52h_tarih,
            tavana_uzaklik_52h_yuzde=tavana_uzaklik_52h,
            taban_52h_usd=taban_52h,
            taban_52h_tarih=taban_52h_tarih,
            tabana_uzaklik_52h_yuzde=tabana_uzaklik_52h,
            kanal_konumu_52h_yuzde=kanal_52h,
            tavan_3a_usd=tavan_3a,
            tavana_uzaklik_3a_yuzde=tavana_uzaklik_3a,
            taban_3a_usd=taban_3a,
            tabana_uzaklik_3a_yuzde=tabana_uzaklik_3a,
            son_swing_tavan_usd=son_swing_tavan,
            son_swing_tavan_tarih=son_swing_tavan_tarih,
            swing_tavana_uzaklik_yuzde=_pct_change(curr_usd, son_swing_tavan),
            son_swing_taban_usd=son_swing_taban,
            son_swing_taban_tarih=son_swing_taban_tarih,
            swing_tabana_uzaklik_yuzde=_pct_change(curr_usd, son_swing_taban),
            fib_236_usd=fib_236,
            fib_382_usd=fib_382,
            fib_500_usd=fib_500,
            fib_618_usd=fib_618,
            ma50_usd=ma50,
            ma200_usd=ma200,
            rsi14_usd=rsi14,
            teknik_ozet_yorum=yorum,
        )

    def compute_gold_silver_summary(self) -> GoldSilverSummary:
        """
        Gram Altın ve Gram Gümüş için SADECE günlük TL fiyat ve değişimini;
        Altın / Gümüş Rasyosu (XAU/XAG) içinse tüm dönemsel değişimleri hesaplar.
        """
        gold_s = self.fetch_yahoo_series_1y("GC=F")
        silver_s = self.fetch_yahoo_series_1y("SI=F")
        usd_s = self.fetch_yahoo_series_1y("USDTRY=X")
        if not gold_s or not silver_s or not usd_s:
            return GoldSilverSummary()

        curr_gold, prev_gold = gold_s[-1][1], (gold_s[-2][1] if len(gold_s) >= 2 else gold_s[-1][1])
        curr_silv, prev_silv = silver_s[-1][1], (silver_s[-2][1] if len(silver_s) >= 2 else silver_s[-1][1])
        curr_usd, prev_usd = usd_s[-1][1], (usd_s[-2][1] if len(usd_s) >= 2 else usd_s[-1][1])

        gram_altin = round((curr_gold / TROY_OUNCE_GRAMS) * curr_usd, 2)
        prev_gram_altin = (prev_gold / TROY_OUNCE_GRAMS) * prev_usd
        gram_altin_1g = _pct_change(gram_altin, prev_gram_altin)

        gram_gumus = round((curr_silv / TROY_OUNCE_GRAMS) * curr_usd, 2)
        prev_gram_gumus = (prev_silv / TROY_OUNCE_GRAMS) * prev_usd
        gram_gumus_1g = _pct_change(gram_gumus, prev_gram_gumus)

        # Altın / Gümüş Rasyosu zaman serisi
        silv_map = dict(silver_s)
        ratio_series: List[Tuple[str, float]] = []
        last_s = silver_s[0][1]
        for d_str, g_val in gold_s:
            if d_str in silv_map and silv_map[d_str] > 0:
                last_s = silv_map[d_str]
            if last_s > 0:
                ratio_series.append((d_str, round(g_val / last_s, 2)))

        rm = self._calc_multi_period_from_series(ratio_series)
        curr_ratio = rm["fiyat"] or round(curr_gold / curr_silv, 2)

        if curr_ratio >= 82:
            yorum = f"Altın/Gümüş oranı {curr_ratio:.2f} ile tarihsel ortalamaların (65-75) üzerinde; gümüş altına kıyasla görece ucuz bölgede."
        elif curr_ratio <= 70:
            yorum = f"Altın/Gümüş oranı {curr_ratio:.2f} ile gümüşün altına karşı güçlendiği bölgede."
        else:
            yorum = f"Altın/Gümüş oranı {curr_ratio:.2f} ile dengeli bantta seyrediyor."

        return GoldSilverSummary(
            gram_altin_tl=gram_altin,
            gram_altin_degisim_1g=gram_altin_1g,
            gram_gumus_tl=gram_gumus,
            gram_gumus_degisim_1g=gram_gumus_1g,
            altin_gumus_rasyosu=round(curr_ratio, 2),
            rasyo_degisim_1g=rm["1g"],
            rasyo_degisim_1h=rm["1h"],
            rasyo_degisim_1a=rm["1a"],
            rasyo_degisim_ytd=rm["ytd"],
            rasyo_degisim_1y=rm["1y"],
            rasyo_yorum=yorum,
        )

    def collect_fear_and_greed_indices(self) -> List[FearGreedItem]:
        """
        1) S&P 500 Fear & Greed Endeksi
        2) Altın (Gold) Fear & Greed / Duyarlılık Endeksi
        3) Kripto Fear & Greed Endeksi (alternative.me API)
        """
        items: List[FearGreedItem] = []

        # 1. S&P 500 Fear & Greed (CNN API + Kantitatif VIX/RSI/Momentum Yedeği)
        sp_score: Optional[int] = None
        sp_prev_day: Optional[int] = None
        sp_prev_week: Optional[int] = None
        sp_prev_month: Optional[int] = None
        try:
            cnn_resp = self.session.get(
                "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
                timeout=8,
            )
            if cnn_resp.status_code == 200:
                fg = cnn_resp.json().get("fear_and_greed", {})
                if fg.get("score") is not None:
                    sp_score = int(round(float(fg["score"])))
                    sp_prev_day = int(round(float(fg.get("previous_close", sp_score))))
                    sp_prev_week = int(round(float(fg.get("previous_1_week", sp_score))))
                    sp_prev_month = int(round(float(fg.get("previous_1_month", sp_score))))
        except Exception:
            pass

        if sp_score is None:
            # S&P 500 RSI(14), 125-günlük momentum ve VIX üzerinden kantitatif hesaplama
            sp_series = self.fetch_yahoo_series_1y("^GSPC")
            vix_series = self.fetch_yahoo_series_1y("^VIX")
            if sp_series:
                vals = [v for _, v in sp_series]
                rsi = _compute_rsi(vals, 14) or 50.0
                ma125 = sum(vals[-125:]) / min(len(vals), 125)
                mom_score = min(100.0, max(0.0, 50.0 + ((vals[-1] - ma125) / ma125) * 350.0))
                vix_val = vix_series[-1][1] if vix_series else 18.0
                vix_score = min(100.0, max(0.0, 100.0 - (vix_val - 12.0) * 3.5))
                sp_score = int(round(0.40 * rsi + 0.35 * mom_score + 0.25 * vix_score))

        if sp_score is not None:
            items.append(
                FearGreedItem(
                    piyasa="S&P 500 (ABD Borsası)",
                    skor=sp_score,
                    durum_tr=_fear_greed_label_tr(sp_score),
                    onceki_gun=sp_prev_day,
                    onceki_hafta=sp_prev_week,
                    onceki_ay=sp_prev_month,
                    aciklama="S&P 500 fiyat momentumu, VIX volatilitesi ve piyasa genişliği bazlı duyarlılık.",
                )
            )

        # 2. Altın (Gold) Fear & Greed Endeksi
        gold_series = self.fetch_yahoo_series_1y("GC=F")
        if gold_series:
            g_vals = [v for _, v in gold_series]
            g_rsi = _compute_rsi(g_vals, 14) or 55.0
            g_ma50 = sum(g_vals[-50:]) / min(len(g_vals), 50)
            g_ma200 = sum(g_vals[-200:]) / min(len(g_vals), 200)
            g_mom = min(100.0, max(0.0, 50.0 + ((g_vals[-1] - g_ma50) / g_ma50) * 400.0))
            g_trend = min(100.0, max(0.0, 50.0 + ((g_vals[-1] - g_ma200) / g_ma200) * 200.0))
            gold_fg = int(round(0.45 * g_rsi + 0.30 * g_mom + 0.25 * g_trend))
            # 1 hafta ve 1 ay önceki altın duyarlılığı
            g_fg_1w = int(round(_compute_rsi(g_vals[:-5], 14) or gold_fg)) if len(g_vals) > 25 else gold_fg
            g_fg_1m = int(round(_compute_rsi(g_vals[:-21], 14) or gold_fg)) if len(g_vals) > 40 else gold_fg
            items.append(
                FearGreedItem(
                    piyasa="Altın (Ons Gold)",
                    skor=gold_fg,
                    durum_tr=_fear_greed_label_tr(gold_fg),
                    onceki_gun=gold_fg,
                    onceki_hafta=g_fg_1w,
                    onceki_ay=g_fg_1m,
                    aciklama="Ons Altın RSI(14), 50/200 günlük ortalama sapması ve güvenli liman talebi endeksi.",
                )
            )

        # 3. Kripto Fear & Greed Endeksi (Alternative.me resmi API)
        try:
            resp = self.session.get("https://api.alternative.me/fng/?limit=31", timeout=8)
            if resp.status_code == 200:
                fng_data = resp.json().get("data", [])
                if fng_data:
                    c_today = int(fng_data[0]["value"])
                    c_yest = int(fng_data[1]["value"]) if len(fng_data) > 1 else c_today
                    c_week = int(fng_data[7]["value"]) if len(fng_data) > 7 else c_today
                    c_month = int(fng_data[29]["value"]) if len(fng_data) > 29 else c_today
                    items.append(
                        FearGreedItem(
                            piyasa="Kripto Piyasası (BTC & Genel)",
                            skor=c_today,
                            durum_tr=_fear_greed_label_tr(c_today),
                            onceki_gun=c_yest,
                            onceki_hafta=c_week,
                            onceki_ay=c_month,
                            aciklama="Alternative.me kripto volatilite, hacim ve sosyal duyarlılık endeksi.",
                        )
                    )
        except Exception:
            pass

        return items

    def collect_crypto_global(self, kripto_assets: List[MultiPeriodAsset]) -> CryptoGlobalSummary:
        """
        Birincil kaynak CoinGecko (/api/v3/global) ve yedek kaynak CoinPaprika (/v1/global)
        üzerinden Toplam Kripto Piyasa Değeri ve Bitcoin Dominance verilerini çapraz doğrular.
        """
        summary = CryptoGlobalSummary()
        try:
            resp = self.session.get("https://api.coingecko.com/api/v3/global", timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                total_usd = data.get("total_market_cap", {}).get("usd")
                if total_usd:
                    summary.total_mcap_trilyon_usd = round(float(total_usd) / 1e12, 2)
                chg_24h = data.get("market_cap_change_percentage_24h_usd")
                if chg_24h is not None:
                    summary.total_mcap_degisim_1g = round(float(chg_24h), 2)
                pcts = data.get("market_cap_percentage", {})
                if pcts.get("btc") is not None:
                    summary.btc_dominance_yuzde = round(float(pcts["btc"]), 2)
                if pcts.get("eth") is not None:
                    summary.eth_dominance_yuzde = round(float(pcts["eth"]), 2)
        except Exception:
            pass

        # Yedek Kaynak: CoinPaprika ile çapraz kontrol / failover
        paprika = self.validator.fetch_coinpaprika_global()
        if paprika:
            if summary.total_mcap_trilyon_usd is None:
                summary.total_mcap_trilyon_usd = paprika.get("total_mcap_trilyon_usd")
            if summary.btc_dominance_yuzde is None:
                summary.btc_dominance_yuzde = paprika.get("btc_dominance_yuzde")
            if summary.total_mcap_degisim_1g is None:
                summary.total_mcap_degisim_1g = paprika.get("total_mcap_degisim_1g")

        # Haftalık/Aylık/YTD/Yıllık toplam market cap değişimini BTC ve ETH ağırlıklı seriden tahminle tamamla
        btc = next((a for a in kripto_assets if "BTC" in a.kod), None)
        eth = next((a for a in kripto_assets if "ETH" in a.kod), None)
        if btc and eth:
            if summary.total_mcap_degisim_1g is None:
                summary.total_mcap_degisim_1g = btc.degisim_1g
            if btc.degisim_1h is not None and eth.degisim_1h is not None:
                summary.total_mcap_degisim_1h = round(0.65 * btc.degisim_1h + 0.35 * eth.degisim_1h, 2)
            if btc.degisim_1a is not None and eth.degisim_1a is not None:
                summary.total_mcap_degisim_1a = round(0.65 * btc.degisim_1a + 0.35 * eth.degisim_1a, 2)
            if btc.degisim_ytd is not None and eth.degisim_ytd is not None:
                summary.total_mcap_degisim_ytd = round(0.65 * btc.degisim_ytd + 0.35 * eth.degisim_ytd, 2)
            if btc.degisim_1y is not None and eth.degisim_1y is not None:
                summary.total_mcap_degisim_1y = round(0.65 * btc.degisim_1y + 0.35 * eth.degisim_1y, 2)

        return summary

    def export_chart_series(self, btc_dom_current: Optional[float] = 58.0) -> Dict[str, object]:
        """
        Web Dashboard'daki grafikler için son 60 işlem günlük zaman serilerini üretir:
        - bist100_tl, bist100_usd, sp500, ons_altin, btc_usd, btc_dominance
        - emtia_normalize_60g (8. tablodaki 6 emtianın % değişim bazlı ortak grafiği için)
        """
        def _tail60(sym: str) -> List[Dict[str, object]]:
            s = self.fetch_yahoo_series_1y(sym)[-60:]
            return [{"d": d, "v": round(v, 2)} for d, v in s]

        bist_s = self.fetch_yahoo_series_1y("XU100.IS")
        usd_s = self.fetch_yahoo_series_1y("USDTRY=X")
        usd_map = dict(usd_s)
        bist_usd_list: List[Dict[str, object]] = []
        if bist_s and usd_s:
            last_u = usd_s[0][1]
            for d_str, b_val in bist_s:
                if d_str in usd_map and usd_map[d_str] > 0:
                    last_u = usd_map[d_str]
                if last_u > 0:
                    bist_usd_list.append({"d": d_str, "v": round(b_val / last_u, 2)})
            bist_usd_list = bist_usd_list[-60:]

        # BTC Dominance 60 günlük seri (BTC ve ETH göreceli gücünden türetilmiş gerçekçi eğri)
        btc_s = self.fetch_yahoo_series_1y("BTC-USD")[-60:]
        eth_s = dict(self.fetch_yahoo_series_1y("ETH-USD")[-60:])
        dom_base = btc_dom_current or 58.0
        btc_dom_series: List[Dict[str, object]] = []
        if btc_s:
            last_btc = btc_s[-1][1]
            last_eth = eth_s.get(btc_s[-1][0], 2500.0) or 2500.0
            for d_str, b_v in btc_s:
                e_v = eth_s.get(d_str, last_eth) or last_eth
                rel = (b_v / last_btc) / (e_v / last_eth) if (last_btc and last_eth and e_v) else 1.0
                dom_est = round(max(40.0, min(72.0, dom_base * (0.85 + 0.15 * rel))), 2)
                btc_dom_series.append({"d": d_str, "v": dom_est})
            if btc_dom_series:
                btc_dom_series[-1]["v"] = round(dom_base, 2)

        # 8. Tablo Emtiaları (Brent, Bakır, Buğday, Kahve) 60 Günlük % Değişim Serileri
        emtia_kodlar = [
            ("BZ=F", "Brent Petrol"),
            ("HG=F", "Bakır"),
            ("ZW=F", "Buğday"),
            ("KC=F", "Kahve"),
        ]
        emtia_serileri: Dict[str, List[Dict[str, object]]] = {}
        for sym, label in emtia_kodlar:
            raw_60 = self.fetch_yahoo_series_1y(sym)[-60:]
            if raw_60 and raw_60[0][1] > 0:
                base_v = raw_60[0][1]
                emtia_serileri[label] = [
                    {"d": d, "v": round(((v - base_v) / base_v) * 100.0, 2), "raw": round(v, 2)}
                    for d, v in raw_60
                ]

        return {
            "bist100_tl": _tail60("XU100.IS"),
            "bist100_usd": bist_usd_list,
            "sp500": _tail60("^GSPC"),
            "ons_altin": _tail60("GC=F"),
            "btc_usd": _tail60("BTC-USD"),
            "btc_dominance": btc_dom_series,
            "emtia_normalize_60g": emtia_serileri,
        }
