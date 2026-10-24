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
    "PPI m/m": "Aylık ÜFE (Üretici Enflasyonu)",
    "Non-Farm Employment Change": "Tarım Dışı İstihdam Değişimi (NFP)",
    "Unemployment Rate": "İşsizlik Oranı",
    "Unemployment Claims": "Haftalık İşsizlik Maaşı Başvuruları",
    "Federal Funds Rate": "Fed Faiz Kararı",
    "FOMC Statement": "Fed (FOMC) Para Politikası Açıklaması",
    "FOMC Press Conference": "Fed Başkanı Basın Toplantısı",
    "FOMC Meeting Minutes": "Fed FOMC Toplantı Tutanakları",
    "Fed Chair Powell Speaks": "Fed Başkanı Powell'ın Konuşması",
    "Main Refinancing Rate": "Avrupa Merkez Bankası (ECB) Faiz Kararı",
    "Monetary Policy Statement": "ECB Para Politikası Açıklaması",
    "ECB Press Conference": "ECB Başkanı Basın Toplantısı",
    "Advance GDP q/q": "Öncü GSYH Büyüme Oranı (Çeyreklik)",
    "Preliminary GDP q/q": "Öncü GSYH Büyüme Oranı (Çeyreklik)",
    "Final GDP q/q": "GSYH Büyüme Oranı (Çeyreklik)",
    "Retail Sales m/m": "Perakende Satışlar (Aylık)",
    "Core Retail Sales m/m": "Çekirdek Perakende Satışlar (Aylık)",
    "ISM Manufacturing PMI": "ISM İmalat PMI",
    "ISM Services PMI": "ISM Hizmetler PMI",
    "Flash Manufacturing PMI": "Öncü İmalat PMI",
    "Flash Services PMI": "Öncü Hizmetler PMI",
    "Existing Home Sales": "Mevcut Konut Satışları",
    "New Home Sales": "Yeni Konut Satışları",
    "Consumer Confidence": "Tüketici Güven Endeksi",
    "Prelim UoM Consumer Sentiment": "Michigan Tüketici Güven Endeksi",
    "Durable Goods Orders m/m": "Dayanıklı Mal Siparişleri (Aylık)",
    "Core Durable Goods Orders m/m": "Çekirdek Dayanıklı Mal Siparişleri",
}

COUNTRY_MAP: Dict[str, str] = {
    "USD": "ABD (Fed/Makro)",
    "EUR": "Euro Bölgesi (ECB)",
    "TRY": "Türkiye (TCMB/TÜİK)",
}

IMPACT_MAP: Dict[str, str] = {
    "High": "Yüksek",
    "Medium": "Orta",
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

            # Ayın 3'ü (veya hafta sonuna gelirse ilk Pazartesi): TÜİK TÜFE / ÜFE Enflasyon Verisi
            if dt.day in (3, 4) and dt.weekday() < 5:
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

            # Ayın 10'u civarı: TÜİK Sanayi Üretimi ve İşgücü (İşsizlik) İstatistikleri
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

            # Ayın 22-26'sı arası: Reel Kesim Güven Endeksi ve Kapasite Kullanım Oranı
            if dt.day == 25 and dt.weekday() < 5:
                target_list.append(
                    EconomicEvent(
                        donem_grubu=grup,
                        tarih=d_str,
                        saat="10:00",
                        ulke="Türkiye (TCMB)",
                        onem="Orta",
                        baslik="TCMB Reel Kesim Güven Endeksi ve İmalat Sanayi Kapasite Kullanım Oranı",
                    )
                )

            # Ayın son iş günü: TÜİK Dış Ticaret ve Ekonomik Güven Endeksi
            if dt.day in (29, 30, 31) and dt.weekday() < 5:
                target_list.append(
                    EconomicEvent(
                        donem_grubu=grup,
                        tarih=d_str,
                        saat="10:00",
                        ulke="Türkiye (TÜİK)",
                        onem="Orta",
                        baslik="TÜİK Ekonomik Güven Endeksi ve Dış Ticaret Dengesi",
                    )
                )

        return today_tr, this_week_tr, next_week_tr

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
                    if country not in ("USD", "EUR", "TRY") or impact not in ("High", "Medium"):
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
                        onem=IMPACT_MAP.get(impact, "Orta"),
                        baslik=self._translate_title(item.get("title", "")),
                        gerceklesen=item.get("actual") or "-",
                        beklenti=item.get("forecast") or "-",
                        onceki=item.get("previous") or "-",
                    )
                    if ev_date == today_str:
                        today_events.append(ev)
                    elif impact == "High":
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

        return today_events[:10], this_week_events[:12], next_week_events[:12]
