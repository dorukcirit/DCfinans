from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


def classify_trend(pct: Optional[float], threshold: float = 0.20) -> str:
    """Yüzdesel değişime göre 'Artış', 'Azalış' veya 'Yatay' döner."""
    if pct is None:
        return "Veri Yok"
    if pct > threshold:
        return "Artış"
    if pct < -threshold:
        return "Azalış"
    return "Yatay"


def trend_icon(pct: Optional[float], threshold: float = 0.20) -> str:
    if pct is None:
        return "➖"
    if pct > threshold:
        return "🟢 Artış"
    if pct < -threshold:
        return "🔴 Azalış"
    return "⚪ Yatay"


@dataclass
class MultiPeriodAsset:
    """
    Günlük (1D), 1 Hafta (1W), 1 Ay (1M), 3 Ay (3M), Yılbaşından İtibaren (YTD)
    ve 1 Yıl (1Y) performanslarını ve yönlerini barındıran gelişmiş varlık modeli.
    """
    kod: str
    ad: str
    okunus: str
    birim: str
    kategori: str  # "bist", "abd_endeks", "altin_gumus_usd", "doviz", "tahvil_cds", "emtia", "kripto"
    fiyat: Optional[float] = None
    onceki_kapanis: Optional[float] = None
    degisim_1g: Optional[float] = None
    degisim_1h: Optional[float] = None
    degisim_1a: Optional[float] = None
    degisim_3a: Optional[float] = None
    degisim_ytd: Optional[float] = None
    degisim_1y: Optional[float] = None
    not_bilgisi: str = ""
    kaynak: str = "Yahoo Finance"

    @property
    def yon_1g(self) -> str:
        return classify_trend(self.degisim_1g, 0.10)

    @property
    def yon_1h(self) -> str:
        return classify_trend(self.degisim_1h, 0.25)

    @property
    def yon_1a(self) -> str:
        return classify_trend(self.degisim_1a, 0.50)

    @property
    def yon_3a(self) -> str:
        return classify_trend(self.degisim_3a, 0.75)

    @property
    def yon_ytd(self) -> str:
        return classify_trend(self.degisim_ytd, 0.75)

    @property
    def yon_1y(self) -> str:
        return classify_trend(self.degisim_1y, 1.00)


@dataclass
class BistUsdTechnicalAnalysis:
    """
    BIST 100 Dolar (USD) Bazlı Performans ve Hibrit Teknik Analiz Modeli
    (Taban/Tavan Uzaklıkları, Swing High/Low Pivot, Fibonacci, MA200 ve RSI14).
    """
    guncel_usd: Optional[float] = None
    guncel_tl: Optional[float] = None
    usdtry_kuru: Optional[float] = None

    # Dolar bazlı dönemsel performanslar (%)
    degisim_1g_usd: Optional[float] = None
    degisim_1h_usd: Optional[float] = None
    degisim_1a_usd: Optional[float] = None
    degisim_3a_usd: Optional[float] = None
    degisim_ytd_usd: Optional[float] = None
    degisim_1y_usd: Optional[float] = None

    # 1 Yıllık (52 Haftalık) Dolar Tavan (Zirve) ve Taban (Dip)
    tavan_52h_usd: Optional[float] = None
    tavan_52h_tarih: str = ""
    tavana_uzaklik_52h_yuzde: Optional[float] = None  # Örn: -17.4% (Zirveden düşüş)
    taban_52h_usd: Optional[float] = None
    taban_52h_tarih: str = ""
    tabana_uzaklik_52h_yuzde: Optional[float] = None  # Örn: +9.2% (Dipten yükseliş)
    kanal_konumu_52h_yuzde: Optional[float] = None    # 0% = Tam Dip, 100% = Tam Zirve

    # 3 Aylık (63 İş Günü) Dolar Tavan ve Taban
    tavan_3a_usd: Optional[float] = None
    tavana_uzaklik_3a_yuzde: Optional[float] = None
    taban_3a_usd: Optional[float] = None
    tabana_uzaklik_3a_yuzde: Optional[float] = None

    # Fractal / Pivot Swing High (Son Yerel Tavan/Direnç) & Swing Low (Son Yerel Taban/Destek)
    son_swing_tavan_usd: Optional[float] = None
    son_swing_tavan_tarih: str = ""
    swing_tavana_uzaklik_yuzde: Optional[float] = None
    son_swing_taban_usd: Optional[float] = None
    son_swing_taban_tarih: str = ""
    swing_tabana_uzaklik_yuzde: Optional[float] = None

    # Fibonacci Düzeltme Seviyeleri (52H Taban -> 52H Tavan dalgasına göre)
    fib_236_usd: Optional[float] = None
    fib_382_usd: Optional[float] = None
    fib_500_usd: Optional[float] = None
    fib_618_usd: Optional[float] = None

    # Hareketli Ortalama ve Momentum
    ma50_usd: Optional[float] = None
    ma200_usd: Optional[float] = None
    rsi14_usd: Optional[float] = None
    teknik_ozet_yorum: str = ""


@dataclass
class GoldSilverSummary:
    """Altın & Gümüş TL Günlük Fiyatları ve Altın/Gümüş Rasyosu (XAU/XAG)."""
    gram_altin_tl: Optional[float] = None
    gram_altin_degisim_1g: Optional[float] = None
    gram_gumus_tl: Optional[float] = None
    gram_gumus_degisim_1g: Optional[float] = None
    altin_gumus_rasyosu: Optional[float] = None
    rasyo_degisim_1g: Optional[float] = None
    rasyo_degisim_1h: Optional[float] = None
    rasyo_degisim_1a: Optional[float] = None
    rasyo_degisim_ytd: Optional[float] = None
    rasyo_degisim_1y: Optional[float] = None
    rasyo_yorum: str = ""


@dataclass
class FearGreedItem:
    """S&P 500, Altın ve Kripto için Korku ve Açgözlülük Endeksi modeli."""
    piyasa: str          # "S&P 500 (ABD Borsası)", "Altın (Gold)", "Kripto Piyasası"
    skor: int            # 0 - 100 arası
    durum_tr: str        # "Aşırı Korku", "Korku", "Nötr", "Açgözlülük", "Aşırı Açgözlülük"
    onceki_gun: Optional[int] = None
    onceki_hafta: Optional[int] = None
    onceki_ay: Optional[int] = None
    aciklama: str = ""


@dataclass
class CryptoGlobalSummary:
    """Kripto Toplam Piyasa Değeri (Total Market Cap) ve Bitcoin Dominance (BTC.D)."""
    total_mcap_trilyon_usd: Optional[float] = None
    total_mcap_degisim_1g: Optional[float] = None
    total_mcap_degisim_1h: Optional[float] = None
    total_mcap_degisim_1a: Optional[float] = None
    total_mcap_degisim_ytd: Optional[float] = None
    total_mcap_degisim_1y: Optional[float] = None
    btc_dominance_yuzde: Optional[float] = None
    eth_dominance_yuzde: Optional[float] = None


@dataclass
class TefasTopFund:
    """TEFAS Dönemsel En Çok Kazandıran Fon Modeli."""
    donem_etiketi: str   # "Son 1 Gün", "Son 1 Hafta", "Son 1 Ay", "Yılbaşından İtibaren (YTD)", "Son 1 Yıl"
    sira: int
    kod: str
    ad: str
    kapsam_turu: str     # Örn: "Hisse Senedi Şemsiye Fonu", "Kıymetli Madenler Şemsiye Fonu", "Değişken Şemsiye Fonu"
    ilgili_donem_getiri_yuzde: float
    getiri_1g: Optional[float] = None
    getiri_1h: Optional[float] = None
    getiri_1a: Optional[float] = None
    getiri_ytd: Optional[float] = None
    getiri_1y: Optional[float] = None


@dataclass
class EconomicEvent:
    """Ekonomik takvim verisi (Bugün, Bu Hafta ve Gelecek Hafta)."""
    donem_grubu: str     # "bugun", "bu_hafta", "gelecek_hafta"
    tarih: str
    saat: str
    ulke: str            # "ABD", "Türkiye", "Euro Bölgesi"
    onem: str            # "Yüksek", "Orta"
    baslik: str
    gerceklesen: str = "-"
    beklenti: str = "-"
    onceki: str = "-"


@dataclass
class NewsHeadline:
    """Kısa haber başlığı (Otorite/Banka açıklamaları veya Konut/Araç istatistikleri)."""
    baslik: str
    kaynak: str
    kategori: str  # "otorite_banka", "konut", "arac"
    tarih_saat: str = ""
    link: str = ""
    etiketler: List[str] = field(default_factory=list)


@dataclass
class TTSSegment:
    """Sesli okuma (TTS) motorları için bölümlendirilmiş spiker metin parçası."""
    bolum_id: str
    bolum_basligi: str
    ham_metin: str
    tts_okunus_metni: str
    tahmini_sure_saniye: int


@dataclass
class DailyFinanceReport:
    """Gelişmiş Günlük Finans Raporu (V2) Ana Veri Yapısı."""
    tarih: str
    olusturulma_zamani: str

    # 1. BIST Endeksleri (TL Çoklu Dönem) & BIST 100 Dolar Teknik Analiz
    bist_endeksleri: List[MultiPeriodAsset] = field(default_factory=list)
    bist100_dolar_teknik: BistUsdTechnicalAnalysis = field(default_factory=BistUsdTechnicalAnalysis)

    # 2. S&P 500, Nasdaq ve Küresel Endeksler (Çoklu Dönem)
    abd_ve_kuresel_endeksler: List[MultiPeriodAsset] = field(default_factory=list)

    # 3. Altın & Gümüş (USD Çoklu Dönem + TL Günlük + Altın/Gümüş Oranı)
    altin_ve_gumus_usd: List[MultiPeriodAsset] = field(default_factory=list)
    altin_gumus_ozet: GoldSilverSummary = field(default_factory=GoldSilverSummary)

    # 4. Korku ve Açgözlülük Endeksleri (S&P 500, Altın, Kripto)
    korku_acgozluluk_endeksleri: List[FearGreedItem] = field(default_factory=list)

    # 5. TEFAS Fonları (Takip Listesi + Dönemsel En Çok Kazandıranlar: Gün, Hafta, Ay, YTD, 1 Yıl)
    tefas_donemsel_liderler: Dict[str, List[TefasTopFund]] = field(default_factory=dict)
    takip_edilen_fonlar: List[TefasTopFund] = field(default_factory=list)

    # 6. Kripto Varlıklar (BTC, ETH, XRP + Total Market Cap + BTC Dominance)
    kripto_varliklar: List[MultiPeriodAsset] = field(default_factory=list)
    kripto_piyasa_ozeti: CryptoGlobalSummary = field(default_factory=CryptoGlobalSummary)

    # 7. ABD & TR Tahvilleri, CDS, Euro, Dolar ve DXY
    tahvil_ve_cds: List[MultiPeriodAsset] = field(default_factory=list)
    doviz_ve_dxy: List[MultiPeriodAsset] = field(default_factory=list)

    # 8. Petrol ve Emtia Grupları (Brent, WTI, Doğalgaz, Bakır, Buğday, Kahve)
    petrol_ve_emtia: List[MultiPeriodAsset] = field(default_factory=list)

    # 9. Ekonomik Takvim (Bugün Açıklananlar, Bu Hafta ve Gelecek Hafta)
    ekonomik_takvim_bugun: List[EconomicEvent] = field(default_factory=list)
    ekonomik_takvim_bu_hafta: List[EconomicEvent] = field(default_factory=list)
    ekonomik_takvim_gelecek_hafta: List[EconomicEvent] = field(default_factory=list)

    # 10. Otorite/Banka Başlıkları & Konut/Araç İstatistikleri
    otorite_ve_banka_haberleri: List[NewsHeadline] = field(default_factory=list)
    konut_ve_arac_istatistikleri: List[NewsHeadline] = field(default_factory=list)

    # 11. Web Dashboard Grafikleri İçin Tarihsel Seri Verileri
    grafik_verileri: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
