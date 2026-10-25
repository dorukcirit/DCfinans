from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import requests
from src.models import EconomicEvent


TR_INDICATOR_TRANSLATIONS: Dict[str, str] = {
    "CPI m/m": "Aylık TÜFE (Enflasyon)",
    "CPI y/y": "Yıllık TÜFE (Enflasyon)",
    "Core CPI m/m": "Aylık Çekirdek TÜFE",
    "Core CPI y/y": "Yıllık Çekirdek TÜFE",
    "Core PCE Price Index m/m": "Çekirdek PCE Enflasyon Endeksi (Aylık)",
    "Core PCE Price Index MoM": "Çekirdek PCE Enflasyon Endeksi (Aylık)",
    "PPI m/m": "Aylık ÜFE (Üretici Enflasyonu)",
    "Non-Farm Employment Change": "Tarım Dışı İstihdam Değişimi (NFP)",
    "Non Farm Payrolls": "Tarım Dışı İstihdam Değişimi (NFP)",
    "Unemployment Rate": "İşsizlik Oranı",
    "Unemployment Claims": "Haftalık İşsizlik Maaşı Başvuruları",
    "Initial Jobless Claims": "Haftalık İşsizlik Maaşı Başvuruları",
    "Federal Funds Rate": "Fed Faiz Kararı",
    "Fed Interest Rate Decision": "Fed Faiz Kararı",
    "FOMC Statement": "Fed (FOMC) Para Politikası Açıklaması",
    "FOMC Press Conference": "Fed Başkanı Basın Toplantısı",
    "Fed Press Conference": "Fed Başkanı Basın Toplantısı",
    "FOMC Meeting Minutes": "Fed FOMC Toplantı Tutanakları",
    "Fed Chair Powell Speaks": "Fed Başkanı Powell'ın Konuşması",
    "Main Refinancing Rate": "Avrupa Merkez Bankası (ECB) Faiz Kararı",
    "ECB Interest Rate Decision": "Avrupa Merkez Bankası (ECB) Faiz Kararı",
    "Deposit Facility Rate": "ECB Mevduat Faizi Kararı",
    "Monetary Policy Statement": "ECB Para Politikası Açıklaması",
    "ECB Press Conference": "ECB Başkanı Basın Toplantısı",
    "Advance GDP q/q": "Öncü GSYH Büyüme Oranı (Çeyreklik)",
    "GDP Growth Rate QoQ Adv": "Öncü GSYH Büyüme Oranı (Çeyreklik)",
    "GDP Growth Rate QoQ": "GSYH Büyüme Oranı (Çeyreklik)",
    "Preliminary GDP q/q": "Öncü GSYH Büyüme Oranı (Çeyreklik)",
    "Final GDP q/q": "GSYH Büyüme Oranı (Çeyreklik)",
    "Retail Sales m/m": "Perakende Satışlar (Aylık)",
    "Retail Sales MoM": "Perakende Satışlar (Aylık)",
    "Core Retail Sales m/m": "Çekirdek Perakende Satışlar (Aylık)",
    "Personal Income MoM": "Kişisel Gelirler (Aylık)",
    "Personal Spending MoM": "Kişisel Harcamalar (Aylık)",
    "ISM Manufacturing PMI": "ISM İmalat PMI",
    "ISM Services PMI": "ISM Hizmetler PMI",
    "Flash Manufacturing PMI": "Öncü İmalat PMI",
    "Flash Services PMI": "Öncü Hizmetler PMI",
    "Existing Home Sales": "Mevcut Konut Satışları",
    "New Home Sales": "Yeni Konut Satışları",
    "Consumer Confidence": "Tüketici Güven Endeksi",
    "Prelim UoM Consumer Sentiment": "Michigan Tüketici Güven Endeksi",
    "Durable Goods Orders m/m": "Dayanıklı Mal Siparişleri (Aylık)",
    "Durable Goods Orders MoM": "Dayanıklı Mal Siparişleri (Aylık)",
    "Core Durable Goods Orders m/m": "Çekirdek Dayanıklı Mal Siparişleri",
}

COUNTRY_MAP: Dict[str, str] = {
    "USD": "ABD (Fed/Makro)",
    "EUR": "Euro Bölgesi (ECB)",
    "TRY": "Türkiye (TCMB/TÜİK)",
}

IMPACT_MAP: Dict[str, str] = {
    "High": "Yüksek",
}


class CalendarCollector:
    """
    ABD, Türkiye ve Euro Bölgesi için:
    1) O gün açıklanan (Bugün) önemli ekonomik veriler
    2) Bu haftanın kalanında açıklanacak veriler
    3) Gelecek hafta açıklanacak kritik ekonomik veriler
    """

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                )
            }
        )

    @staticmethod
    def _translate_title(title: str) -> str:
        if title in TR_INDICATOR_TRANSLATIONS:
            return TR_INDICATOR_TRANSLATIONS[title]
        for eng, tr in TR_INDICATOR_TRANSLATIONS.items():
            if eng.lower() in title.lower():
                return f"{tr} ({title})"
        return title

    def _generate_tr_scheduled_events(
        self, target_date: datetime
    ) -> Tuple[List[EconomicEvent], List[EconomicEvent], List[EconomicEvent]]:
        """
        Türkiye (TCMB ve TÜİK) resmi veri takvimindeki periyodik önemli yayınları
        (Perşembe 14:30 TCMB Rezerv/Yabancı Takas, Ay başı TÜİK Enflasyon, Kapasite Kullanım vb.)
        bugün, bu hafta ve gelecek hafta için üretir.
        """
        today_tr: List[EconomicEvent] = []
        this_week_tr: List[EconomicEvent] = []
        next_week_tr: List[EconomicEvent] = []

        for offset in range(0, 14):
            dt = target_date + timedelta(days=offset)
            d_str = dt.strftime("%Y-%m-%d")
            grup = "bugun" if offset == 0 else ("bu_hafta" if offset <= 6 else "gelecek_hafta")
            target_list = today_tr if offset == 0 else (this_week_tr if offset <= 6 else next_week_tr)

            # Her Perşembe saat 14:30: TCMB Haftalık Para, Banka, Rezerv ve Yabancı Menkul Kıymet İstatistikleri
            if dt.weekday() == 3:
                target_list.append(
                    EconomicEvent(
                        donem_grubu=grup,
                        tarih=d_str,
                        saat="14:30",
                        ulke="Türkiye (TCMB)",
                        onem="Yüksek",
                        baslik="TCMB Haftalık Uluslararası Rezervler ve Yabancı Menkul Kıymet İstatistikleri",
                    )
                )

            # Ayın 3'ü: TÜİK TÜFE / ÜFE Enflasyon Verisi (Yüksek Önem)
            if dt.day == 3 and dt.weekday() < 5:
                target_list.append(
                    EconomicEvent(
                        donem_grubu=grup,
                        tarih=d_str,
                        saat="10:00",
                        ulke="Türkiye (TÜİK)",
                        onem="Yüksek",
                        baslik="TÜİK Aylık ve Yıllık TÜFE (Enflasyon) Verileri",
                    )
                )

            # Ayın 10'u: TÜİK Sanayi Üretimi ve İşgücü (İşsizlik) İstatistikleri (Yüksek Önem)
            if dt.day == 10 and dt.weekday() < 5:
                target_list.append(
                    EconomicEvent(
                        donem_grubu=grup,
                        tarih=d_str,
                        saat="10:00",
                        ulke="Türkiye (TÜİK)",
                        onem="Yüksek",
                        baslik="TÜİK Sanayi Üretim Endeksi ve İşgücü İstatistikleri",
                    )
                )

        return today_tr, this_week_tr, next_week_tr

    def _fetch_tradingview_backup_calendar(
        self, target_date: datetime
    ) -> Tuple[List[EconomicEvent], List[EconomicEvent], List[EconomicEvent]]:
        """
        ForexFactory erişilemediğinde devreye giren Yedek Ekonomik Takvim kaynağı:
        TradingView Economic Calendar API (US, TR, EU yüksek önemli veriler).
        """
        today_out: List[EconomicEvent] = []
        week_out: List[EconomicEvent] = []
        next_out: List[EconomicEvent] = []

        start_dt = target_date.strftime("%Y-%m-%dT00:00:00.000Z")
        end_dt = (target_date + timedelta(days=14)).strftime("%Y-%m-%dT23:59:59.000Z")
        today_str = target_date.strftime("%Y-%m-%d")
        week_limit_str = (target_date + timedelta(days=6)).strftime("%Y-%m-%d")

        url = "https://economic-calendar.tradingview.com/events"
        params = {
            "from": start_dt,
            "to": end_dt,
            "countries": "US,TR,EU",
            "minImportance": "1",
        }
        headers = {
            "Origin": "https://www.tradingview.com",
            "Referer": "https://www.tradingview.com/",
        }
        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                items = resp.json().get("result", [])
                for item in items:
                    imp = int(item.get("importance", 0))
                    if imp < 1:
                        continue
                    raw_date = item.get("date", "")
                    ev_date = raw_date[:10] if len(raw_date) >= 10 else ""
                    saat = raw_date[11:16] if len(raw_date) >= 16 else "Gün İçi"
                    c_code = item.get("country", "")
                    ulke_str = {"US": "ABD (Fed/Makro)", "TR": "Türkiye (TCMB/TÜİK)", "EU": "Euro Bölgesi (ECB)"}.get(c_code, c_code)

                    grup = "bugun" if ev_date == today_str else ("bu_hafta" if ev_date <= week_limit_str else "gelecek_hafta")
                    ev = EconomicEvent(
                        donem_grubu=grup,
                        tarih=ev_date,
                        saat=saat,
                        ulke=ulke_str,
                        onem="Yüksek",
                        baslik=self._translate_title(item.get("title", "")),
                        gerceklesen=str(item.get("actual") if item.get("actual") is not None else "-"),
                        beklenti=str(item.get("forecast") if item.get("forecast") is not None else "-"),
                        onceki=str(item.get("previous") if item.get("previous") is not None else "-"),
                    )
                    if grup == "bugun":
                        today_out.append(ev)
                    elif grup == "bu_hafta":
                        week_out.append(ev)
                    else:
                        next_out.append(ev)
        except Exception:
            pass
        return today_out, week_out, next_out

    def collect_all_calendar_horizons(
        self, target_date: datetime
    ) -> Tuple[List[EconomicEvent], List[EconomicEvent], List[EconomicEvent]]:
        """
        Dönüş: (bugun_aciklananlar, bu_hafta_aciklanacaklar, gelecek_hafta_aciklanacaklar)
        """
        today_str = target_date.strftime("%Y-%m-%d")
        today_events, this_week_events, next_week_events = self._generate_tr_scheduled_events(target_date)

        # 1. Bu Hafta Küresel (ABD & Euro) Takvim
        try:
            resp = self.session.get("https://nfs.faireconomy.media/ff_calendar_thisweek.json", timeout=self.timeout)
            if resp.status_code == 200:
                for item in resp.json():
                    country = item.get("country", "")
                    impact = item.get("impact", "")
                    if country not in ("USD", "EUR", "TRY") or impact != "High":
                        continue
                    raw_date = item.get("date", "")
                    ev_date = raw_date[:10] if len(raw_date) >= 10 else ""
                    saat = raw_date[11:16] if len(raw_date) >= 16 else "Gün İçi"

                    grup = "bugun" if ev_date == today_str else "bu_hafta"
                    ev = EconomicEvent(
                        donem_grubu=grup,
                        tarih=ev_date,
                        saat=saat,
                        ulke=COUNTRY_MAP.get(country, country),
                        onem="Yüksek",
                        baslik=self._translate_title(item.get("title", "")),
                        gerceklesen=item.get("actual") or "-",
                        beklenti=item.get("forecast") or "-",
                        onceki=item.get("previous") or "-",
                    )
                    if ev_date == today_str:
                        today_events.append(ev)
                    else:
                        this_week_events.append(ev)
        except Exception:
            pass

        # 2. Gelecek Hafta Küresel (ABD & Euro) Takvim
        try:
            resp_next = self.session.get(
                "https://nfs.faireconomy.media/ff_calendar_nextweek.json", timeout=self.timeout
            )
            if resp_next.status_code == 200:
                for item in resp_next.json():
                    country = item.get("country", "")
                    impact = item.get("impact", "")
                    if country not in ("USD", "EUR", "TRY") or impact != "High":
                        continue
                    raw_date = item.get("date", "")
                    ev_date = raw_date[:10] if len(raw_date) >= 10 else ""
                    saat = raw_date[11:16] if len(raw_date) >= 16 else "Gün İçi"

                    next_week_events.append(
                        EconomicEvent(
                            donem_grubu="gelecek_hafta",
                            tarih=ev_date,
                            saat=saat,
                            ulke=COUNTRY_MAP.get(country, country),
                            onem="Yüksek",
                            baslik=self._translate_title(item.get("title", "")),
                            gerceklesen=item.get("actual") or "-",
                            beklenti=item.get("forecast") or "-",
                            onceki=item.get("previous") or "-",
                        )
                    )
        except Exception:
            pass

        # 3. Yedek Kaynak Kontrolü: Eğer ForexFactory'den ABD/Euro verisi gelmediyse TradingView Takvimini devreye sok
        has_global = any("ABD" in e.ulke or "Euro" in e.ulke for e in (today_events + this_week_events + next_week_events))
        if not has_global:
            tv_today, tv_week, tv_next = self._fetch_tradingview_backup_calendar(target_date)
            today_events.extend(tv_today)
            this_week_events.extend(tv_week)
            next_week_events.extend(tv_next)

        return today_events[:10], this_week_events[:12], next_week_events[:12]
