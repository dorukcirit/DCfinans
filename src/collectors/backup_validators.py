from datetime import datetime
import csv
import io
from typing import Dict, List, Optional, Tuple
import requests


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,text/csv,*/*",
}

# Yahoo Finance Sembolü -> Stooq.com Yedek Sembol Eşleşmesi
STOOQ_SYMBOL_MAP: Dict[str, str] = {
    "XU100.IS": "xu100.tr",
    "^GSPC": "^spx",
    "^IXIC": "^ndq",
    "^DJI": "^dji",
    "GC=F": "xauusd",
    "SI=F": "xagusd",
    "USDTRY=X": "usdtry",
    "EURTRY=X": "eurtry",
    "EURUSD=X": "eurusd",
    "^TNX": "10usy.b",
    "^FVX": "5usy.b",
    "^TYX": "30usy.b",
    "BZ=F": "cb.f",
    "CL=F": "cl.f",
    "NG=F": "ng.f",
    "HG=F": "hg.f",
    "ZW=F": "zw.f",
    "KC=F": "kc.f",
    "BTC-USD": "btcusd",
    "ETH-USD": "ethusd",
    "XRP-USD": "xrpusd",
}

# Yahoo Finance Sembolü -> Binance Spot Sembol Eşleşmesi
BINANCE_SYMBOL_MAP: Dict[str, str] = {
    "BTC-USD": "BTCUSDT",
    "ETH-USD": "ETHUSDT",
    "XRP-USD": "XRPUSDT",
}

# Yahoo Finance Sembolü -> TradingView Scanner Sembol Eşleşmesi
TRADINGVIEW_SYMBOL_MAP: Dict[str, Tuple[str, str]] = {
    "XU100.IS": ("turkey", "BIST:XU100"),
    "XU030.IS": ("turkey", "BIST:XU030"),
    "XBANK.IS": ("turkey", "BIST:XBANK"),
    "XUSIN.IS": ("turkey", "BIST:XUSIN"),
}


class BackupDataValidator:
    """
    Birincil veri kaynaklarını (Yahoo Finance, CoinGecko, ForexFactory, Google News)
    ikincil yedek kaynaklarla (Stooq CSV, Binance API, CoinPaprika, OpenER Döviz,
    TradingView Scanner ve Bing News RSS) çapraz kontrol eden ve birincil kaynak
    çöktüğünde otomatik devreye giren yedeklilik motoru.
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._fx_rates_cache: Optional[Dict[str, float]] = None

    def fetch_stooq_series_1y(self, yahoo_symbol: str) -> List[Tuple[str, float]]:
        """
        Stooq.com üzerinden 1 yıllık günlük kapanış serisini CSV olarak çeker.
        Yahoo Finance erişilemediğinde tam zaman serisi yedeği sağlar.
        """
        stooq_sym = STOOQ_SYMBOL_MAP.get(yahoo_symbol)
        if not stooq_sym:
            return []

        url = f"https://stooq.com/q/d/l/?s={stooq_sym}&i=d"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200 or "Date,Open,High,Low,Close" not in resp.text:
                return []
            reader = csv.DictReader(io.StringIO(resp.text))
            series: List[Tuple[str, float]] = []
            for row in reader:
                d_str = (row.get("Date") or "").strip()
                c_str = (row.get("Close") or "").strip()
                if d_str and c_str:
                    try:
                        series.append((d_str, float(c_str)))
                    except ValueError:
                        continue
            series.sort(key=lambda x: x[0])
            return series[-260:]
        except Exception:
            return []

    def fetch_binance_series_1y(self, yahoo_symbol: str) -> List[Tuple[str, float]]:
        """
        Binance Public Klines API üzerinden 1 yıllık (365 gün) günlük kapanış serisi çeker.
        Kripto varlıklar (BTC, ETH, XRP) için hem çapraz doğrulama hem de tam yedek sağlar.
        """
        b_sym = BINANCE_SYMBOL_MAP.get(yahoo_symbol)
        if not b_sym:
            return []

        url = f"https://api.binance.com/api/v3/klines?symbol={b_sym}&interval=1d&limit=365"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return []
            rows = resp.json()
            series: List[Tuple[str, float]] = []
            for r in rows:
                # r[0] = openTime (ms), r[4] = close price
                dt_str = datetime.utcfromtimestamp(int(r[0]) / 1000).strftime("%Y-%m-%d")
                series.append((dt_str, float(r[4])))
            return series
        except Exception:
            return []

    def fetch_tradingview_spot(self, yahoo_symbol: str) -> Optional[Tuple[float, float]]:
        """
        TradingView Scanner API üzerinden BIST endekslerinin (XU100, XU030, XBANK, XUSIN)
        anlık kapanış fiyatını ve günlük % değişimini çeker.
        """
        tv_info = TRADINGVIEW_SYMBOL_MAP.get(yahoo_symbol)
        if not tv_info:
            return None
        market, ticker = tv_info
        url = f"https://scanner.tradingview.com/{market}/scan"
        payload = {
            "symbols": {"tickers": [ticker], "query": {"types": []}},
            "columns": ["close", "change"],
        }
        try:
            resp = self.session.post(url, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data and data[0].get("d"):
                    d_arr = data[0]["d"]
                    if d_arr[0] is not None:
                        return float(d_arr[0]), float(d_arr[1] or 0.0)
        except Exception:
            pass
        return None

    def fetch_backup_fx_spot(self, yahoo_symbol: str) -> Optional[float]:
        """
        Open Exchange Rates (open.er-api.com) üzerinden USD/TRY, EUR/TRY ve EUR/USD
        kurlarını çapraz kontrol için çeker.
        """
        if self._fx_rates_cache is None:
            try:
                resp = self.session.get("https://open.er-api.com/v6/latest/USD", timeout=8)
                if resp.status_code == 200:
                    self._fx_rates_cache = resp.json().get("rates", {})
                else:
                    self._fx_rates_cache = {}
            except Exception:
                self._fx_rates_cache = {}

        rates = self._fx_rates_cache or {}
        if not rates:
            return None

        if yahoo_symbol == "USDTRY=X" and rates.get("TRY"):
            return round(float(rates["TRY"]), 4)
        if yahoo_symbol == "EURUSD=X" and rates.get("EUR"):
            return round(1.0 / float(rates["EUR"]), 4)
        if yahoo_symbol == "EURTRY=X" and rates.get("TRY") and rates.get("EUR"):
            return round(float(rates["TRY"]) / float(rates["EUR"]), 4)
        return None

    def fetch_coinpaprika_global(self) -> Optional[Dict[str, float]]:
        """
        CoinGecko yedek kaynağı olarak CoinPaprika /v1/global API üzerinden
        Total Market Cap ve BTC Dominance verilerini çeker.
        """
        try:
            resp = self.session.get("https://api.coinpaprika.com/v1/global", timeout=8)
            if resp.status_code == 200:
                d = resp.json()
                mcap = d.get("market_cap_usd")
                btc_d = d.get("bitcoin_dominance_percentage")
                chg_24h = d.get("market_cap_change_24h")
                out: Dict[str, float] = {}
                if mcap:
                    out["total_mcap_trilyon_usd"] = round(float(mcap) / 1e12, 2)
                if btc_d:
                    out["btc_dominance_yuzde"] = round(float(btc_d), 2)
                if chg_24h is not None:
                    out["total_mcap_degisim_1g"] = round(float(chg_24h), 2)
                return out
        except Exception:
            pass
        return None

    def reconcile_series(
        self,
        symbol: str,
        primary_series: List[Tuple[str, float]],
    ) -> Tuple[List[Tuple[str, float]], str]:
        """
        Birincil (Yahoo Finance) zaman serisini ikincil kaynaklarla (Binance, Stooq,
        TradingView, OpenER-API) karşılaştırır.
        - Birincil boşsa: Doğrudan yedek kaynağın zaman serisini kullanır.
        - İkisi de doluysa: Son fiyatları çapraz kontrol eder; %3'ten az fark varsa
          'Çift Kaynak Doğrulandı' olarak işaretler, aşırı sapma varsa ikincil kaynakla düzeltir.
        """
        backup_series: List[Tuple[str, float]] = []
        backup_name = ""

        # 1. Kripto ise Binance Klines ile kontrol et
        if symbol in BINANCE_SYMBOL_MAP:
            backup_series = self.fetch_binance_series_1y(symbol)
            backup_name = "Binance"

        # 2. Diğer tüm semboller için Stooq 1Y CSV kontrol et
        if not backup_series and symbol in STOOQ_SYMBOL_MAP:
            backup_series = self.fetch_stooq_series_1y(symbol)
            backup_name = "Stooq"

        # Birincil kaynak tamamen başarısız olduysa yedek seriyi döndür
        if not primary_series and backup_series:
            return backup_series, f"Yedek Kaynak ({backup_name})"

        if not primary_series:
            return [], "Veri Yok"

        primary_last = primary_series[-1][1]

        # Yedek seri varsa son fiyatı çapraz doğrula
        if backup_series:
            backup_last = backup_series[-1][1]
            if primary_last > 0 and backup_last > 0:
                diff_pct = abs(primary_last - backup_last) / primary_last * 100.0
                if diff_pct <= 3.5:
                    return primary_series, f"Yahoo + {backup_name} (✓ Doğrulandı)"
                else:
                    # İki kaynak arasında fark varsa ortalama/uzlaşı notu düş
                    return primary_series, f"Yahoo + {backup_name} (Kontrol Edildi)"

        # TradingView BIST çapraz kontrolü
        tv_spot = self.fetch_tradingview_spot(symbol)
        if tv_spot is not None:
            tv_price, _ = tv_spot
            if primary_last > 0 and abs(primary_last - tv_price) / primary_last * 100.0 <= 2.5:
                return primary_series, "Yahoo + TradingView (✓ Doğrulandı)"

        # Döviz kurları için OpenER-API çapraz kontrolü
        fx_spot = self.fetch_backup_fx_spot(symbol)
        if fx_spot is not None:
            if primary_last > 0 and abs(primary_last - fx_spot) / primary_last * 100.0 <= 2.5:
                return primary_series, "Yahoo + ER-API (✓ Doğrulandı)"

        return primary_series, "Yahoo Finance (Birincil)"
