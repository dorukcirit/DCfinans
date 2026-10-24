from typing import Dict, List, Optional
import requests
from src.models import TefasTopFund


def _infer_fund_scope(fon_ad: str, api_scope: str = "") -> str:
    """Fon unvanından veya TEFAS şemsiye türünden fonun kapsamını/stratejisini belirler."""
    u = (fon_ad or "").upper()
    s = (api_scope or "").strip()
    if "TEKNOLOJİ" in u or "YARI İLETKEN" in u or "SİBER" in u:
        return "Teknoloji & Yabancı/Yerli Hisse Kapsamı"
    if "ALTIN" in u or "KIYMETLİ MADEN" in u or "GÜMÜŞ" in u:
        return "Altın & Kıymetli Madenler Kapsamı"
    if "BANKA" in u or "FİNANS" in u:
        return "Bankacılık & Finans Sektörü Hisse Kapsamı"
    if "İHRACATÇI" in u or "TEMETTÜ" in u or "BIST" in u or "HİSSE SENEDİ" in u:
        return "Yerli Hisse Senedi (BIST) Kapsamı"
    if "YABANCI" in u or "AMERİKA" in u or "AVRUPA" in u or "G20" in u:
        return "Yabancı Hisse / Küresel Piyasalar Kapsamı"
    if "PARA PİYASASI" in u:
        return "Para Piyasası & Kısa Vadeli Likidite Kapsamı"
    if "BORÇLANMA" in u or "TAHVİL" in u or "EUROBOND" in u or "DÖVİZ" in u:
        return "Tahvil / Eurobond & Borçlanma Araçları Kapsamı"
    if "KATILIM" in u or "KİRA SERTİFİKASI" in u:
        return "Katılım (Faizsiz) Finans Kapsamı"
    if "FON SEPETİ" in u:
        return "Fon Sepeti / Çoklu Varlık Kapsamı"
    if "DEĞİŞKEN" in u:
        return "Değişken / Aktif Dağılım Kapsamı"
    return s if s else "Yatırım Fonu (Genel Kapsam)"


class TefasCollector:
    """
    TEFAS üzerinden:
    1) Son 1 Gün, 1 Hafta, 1 Ay, Yılbaşından İtibaren (YTD) ve Son 1 Yıl
       en çok kazandıran fonları (adı, kodu ve kapsamı ile) çeker.
    2) Kullanıcının takip listesindeki fonların çoklu dönem getirilerini çeker.
    """

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "tr-TR,tr;q=0.9",
            }
        )

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        if val is None or val == "":
            return None
        try:
            return round(float(val), 2)
        except Exception:
            return None

    def fetch_all_comparison_returns(self) -> List[Dict]:
        """TEFAS BindComparisonFundReturns uç noktasından tüm yatırım fonlarının dönemsel getirilerini çeker."""
        url = "https://www.tefas.gov.tr/api/DB/BindComparisonFundReturns"
        payload = {
            "calismatipi": "2",
            "fontip": "YAT",
            "sfontur": "",
            "kurucukod": "",
            "fongrup": "",
            "bastarih": "Başlangıç",
            "bittarih": "Bitiş",
            "fonturkod": "",
            "fonunvantip": "",
            "strperiod": "1,1,1,1,1,1,1",
            "islemdurum": "1",
        }
        headers = {
            "Referer": "https://www.tefas.gov.tr/FonKarsilastirma.aspx",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        try:
            resp = self.session.post(url, data=payload, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except Exception:
            pass
        return []

    def collect_top_and_watchlist_funds(
        self, watchlist_cfg: List[Dict], top_n: int = 4
    ) -> tuple[Dict[str, List[TefasTopFund]], List[TefasTopFund]]:
        """
        Dönüş: (donemsel_liderler_dict, takip_edilen_fonlar_listesi)
        donemsel_liderler_dict anahtarları: 'gunluk', 'haftalik', 'aylik', 'ytd', 'yillik'
        """
        raw_rows = self.fetch_all_comparison_returns()
        period_defs = [
            ("gunluk", "Son 1 Gün", "GETIRI1G"),
            ("haftalik", "Son 1 Hafta", "GETIRI1H"),
            ("aylik", "Son 1 Ay", "GETIRI1A"),
            ("ytd", "Yılbaşından İtibaren (YTD)", "GETIRIYB"),
            ("yillik", "Son 1 Yıl", "GETIRI1Y"),
        ]

        leaders: Dict[str, List[TefasTopFund]] = {k: [] for k, _, _ in period_defs}
        watchlist_out: List[TefasTopFund] = []

        if not raw_rows:
            return leaders, watchlist_out

        for key, label, field_name in period_defs:
            valid = [r for r in raw_rows if self._safe_float(r.get(field_name)) is not None]
            sorted_rows = sorted(valid, key=lambda r: float(r.get(field_name, -9999)), reverse=True)
            for idx, r in enumerate(sorted_rows[:top_n], start=1):
                ad = (r.get("FONUNVAN") or "").strip()
                kapsam = _infer_fund_scope(ad, r.get("FONTURACIKLAMA", ""))
                leaders[key].append(
                    TefasTopFund(
                        donem_etiketi=label,
                        sira=idx,
                        kod=(r.get("FONKODU") or "").strip(),
                        ad=ad,
                        kapsam_turu=kapsam,
                        ilgili_donem_getiri_yuzde=self._safe_float(r.get(field_name)) or 0.0,
                        getiri_1g=self._safe_float(r.get("GETIRI1G")),
                        getiri_1h=self._safe_float(r.get("GETIRI1H")),
                        getiri_1a=self._safe_float(r.get("GETIRI1A")),
                        getiri_ytd=self._safe_float(r.get("GETIRIYB")),
                        getiri_1y=self._safe_float(r.get("GETIRI1Y")),
                    )
                )

        by_code = {(r.get("FONKODU") or "").strip().upper(): r for r in raw_rows}
        for idx, item in enumerate(watchlist_cfg, start=1):
            kod = item["kod"].upper()
            r = by_code.get(kod)
            if r:
                ad = (r.get("FONUNVAN") or item["ad"]).strip()
                kapsam = item.get("kapsam") or _infer_fund_scope(ad, r.get("FONTURACIKLAMA", ""))
                watchlist_out.append(
                    TefasTopFund(
                        donem_etiketi="Takip Listesi",
                        sira=idx,
                        kod=kod,
                        ad=ad,
                        kapsam_turu=kapsam,
                        ilgili_donem_getiri_yuzde=self._safe_float(r.get("GETIRI1G")) or 0.0,
                        getiri_1g=self._safe_float(r.get("GETIRI1G")),
                        getiri_1h=self._safe_float(r.get("GETIRI1H")),
                        getiri_1a=self._safe_float(r.get("GETIRI1A")),
                        getiri_ytd=self._safe_float(r.get("GETIRIYB")),
                        getiri_1y=self._safe_float(r.get("GETIRI1Y")),
                    )
                )

        return leaders, watchlist_out
