from datetime import datetime, timedelta
import math
from src.models import (
    BistUsdTechnicalAnalysis,
    CryptoGlobalSummary,
    DailyFinanceReport,
    EconomicEvent,
    FearGreedItem,
    GoldSilverSummary,
    MultiPeriodAsset,
    NewsHeadline,
    TefasTopFund,
)


def _make_demo_curve(now: datetime, start_val: float, end_val: float, volatility: float, phase: float = 0.0):
    pts = []
    for i in range(60):
        dt = (now - timedelta(days=59 - i)).strftime("%Y-%m-%d")
        t = i / 59.0
        wave = math.sin(t * 9.0 + phase) * volatility + math.cos(t * 4.5 + phase) * (volatility * 0.6)
        val = start_val + (end_val - start_val) * t + wave * (1.0 - 0.3 * t)
        if i == 59:
            val = end_val
        pts.append({"d": dt, "v": round(val, 2)})
    return pts


def create_demo_report(now: datetime) -> DailyFinanceReport:
    """Tüm V2 çoklu dönem, teknik analiz, TEFAS liderleri ve takvim verilerini içeren zengin örnek rapor."""
    d_str = now.strftime("%Y-%m-%d")
    emtia_demo = {}
    for idx, (label, chg_end, p_start) in enumerate([
        ("Brent Petrol", -7.8, 81.2),
        ("Bakır", 6.4, 4.12),
        ("Buğday", 4.6, 547.0),
        ("Kahve", 6.2, 233.9),
    ]):
        c_pts = _make_demo_curve(now, 0.0, chg_end, 3.2, phase=idx * 1.1)
        for p in c_pts:
            p["raw"] = round(p_start * (1.0 + p["v"] / 100.0), 2)
        emtia_demo[label] = c_pts

    demo_charts = {
        "bist100_tl": _make_demo_curve(now, 10820.0, 9685.40, 210.0, 0.2),
        "bist100_usd": _make_demo_curve(now, 327.80, 282.54, 6.5, 0.5),
        "sp500": _make_demo_curve(now, 5430.0, 5842.50, 55.0, 1.0),
        "ons_altin": _make_demo_curve(now, 2398.0, 2738.50, 28.0, 1.5),
        "btc_usd": _make_demo_curve(now, 65600.0, 68450.0, 2100.0, 2.1),
        "btc_dominance": _make_demo_curve(now, 55.20, 57.45, 0.65, 0.8),
        "emtia_normalize_60g": emtia_demo,
    }
    return DailyFinanceReport(
        tarih=d_str,
        olusturulma_zamani=now.strftime("%Y-%m-%d %H:%M:%S") + " (Örnek/Demo Veri)",
        bist_endeksleri=[
            MultiPeriodAsset("XU100.IS", "BIST 100", "Borsa İstanbul yüz endeksi", "puan", "bist", 9685.40, 9549.80, 1.42, 3.85, -1.90, -10.45, 29.65, 24.80, "Ana Endeks", "Borsa İstanbul"),
            MultiPeriodAsset("XU030.IS", "BIST 30", "Borsa İstanbul otuz endeksi", "puan", "bist", 10720.15, 10546.10, 1.65, 4.10, -1.40, -9.80, 33.40, 28.10, "Büyük Ölçekli", "Borsa İstanbul"),
            MultiPeriodAsset("XBANK.IS", "BIST Bankacılık", "Borsa İstanbul bankacılık endeksi", "puan", "bist", 13450.00, 13163.00, 2.18, 5.60, 1.25, -8.20, 54.20, 61.50, "Bankacılık", "Borsa İstanbul"),
            MultiPeriodAsset("XUSIN.IS", "BIST Sınai", "Borsa İstanbul sınai endeksi", "puan", "bist", 12940.50, 12835.00, 0.82, 2.15, -3.40, -14.10, 11.80, 9.40, "Sanayi", "Borsa İstanbul"),
        ],
        bist100_dolar_teknik=BistUsdTechnicalAnalysis(
            guncel_usd=282.54,
            guncel_tl=9685.40,
            usdtry_kuru=34.28,
            degisim_1g_usd=1.30,
            degisim_1h_usd=3.52,
            degisim_1a_usd=-2.45,
            degisim_3a_usd=-13.80,
            degisim_ytd_usd=11.40,
            degisim_1y_usd=1.85,
            tavan_52h_usd=344.20,
            tavan_52h_tarih="2026-07-18",
            tavana_uzaklik_52h_yuzde=-17.91,
            taban_52h_usd=254.80,
            taban_52h_tarih="2025-12-26",
            tabana_uzaklik_52h_yuzde=10.89,
            kanal_konumu_52h_yuzde=31.0,
            tavan_3a_usd=327.80,
            tavana_uzaklik_3a_yuzde=-13.81,
            taban_3a_usd=261.40,
            tabana_uzaklik_3a_yuzde=8.09,
            son_swing_tavan_usd=298.60,
            son_swing_tavan_tarih="2026-09-24",
            swing_tavana_uzaklik_yuzde=-5.38,
            son_swing_taban_usd=261.40,
            son_swing_taban_tarih="2026-10-14",
            swing_tabana_uzaklik_yuzde=8.09,
            fib_236_usd=323.10,
            fib_382_usd=310.05,
            fib_500_usd=299.50,
            fib_618_usd=288.95,
            ma50_usd=289.40,
            ma200_usd=296.80,
            rsi14_usd=44.6,
            teknik_ozet_yorum=(
                "BIST 100 Dolar bazında 282,54$ seviyesinde olup 1 yıllık dolar kanalının alt (ucuz/destek) bölgesinde (%31,0) yer alıyor. "
                "52 haftalık zirvesinden (344,20$) %17,9 aşağıda, 52 haftalık dibinden (254,80$) ise %10,9 yukarıda bulunuyor. "
                "Son yerel Swing tabanı olan 261,40$ desteğinden %8,1 tepki veren endekste ilk kritik direnç Fibonacci %61,8 (288,95$) ve 200 günlük ortalama (296,80$) bölgesidir."
            ),
        ),
        abd_ve_kuresel_endeksler=[
            MultiPeriodAsset("^GSPC", "S&P 500", "Es end Pi beş yüz endeksi", "puan", "abd_endeks", 5842.50, 5814.60, 0.48, 0.85, 2.35, 7.60, 22.40, 38.20, "ABD Geniş Piyasa", "Yahoo Finance"),
            MultiPeriodAsset("^IXIC", "Nasdaq", "Nazdak teknoloji endeksi", "puan", "abd_endeks", 18590.20, 18449.90, 0.76, 1.40, 3.10, 8.90, 23.80, 42.10, "ABD Teknoloji", "Yahoo Finance"),
            MultiPeriodAsset("^DJI", "Dow Jones", "Dav Cons endeksi", "puan", "abd_endeks", 42374.30, 42512.00, -0.32, -0.95, 0.80, 5.40, 12.40, 27.60, "ABD Sanayi", "Yahoo Finance"),
            MultiPeriodAsset("^VIX", "VIX Volatilite Endeksi", "Viks korku endeksi", "puan", "abd_endeks", 18.45, 19.06, -3.20, 2.30, 19.80, 12.10, 48.20, -4.10, "Korku Endeksi", "Yahoo Finance"),
        ],
        altin_ve_gumus_usd=[
            MultiPeriodAsset("GC=F", "Ons Altın (USD)", "Ons altın", "USD", "altin_gumus_usd", 2738.50, 2715.40, 0.85, 1.72, 4.30, 14.20, 32.80, 38.60, "Kıymetli Maden", "Yahoo Finance"),
            MultiPeriodAsset("SI=F", "Ons Gümüş (USD)", "Ons gümüş", "USD", "altin_gumus_usd", 33.85, 33.46, 1.15, 6.40, 9.80, 16.90, 41.20, 46.80, "Kıymetli Maden", "Yahoo Finance"),
        ],
        altin_gumus_ozet=GoldSilverSummary(
            gram_altin_tl=3018.45,
            gram_altin_degisim_1g=0.97,
            gram_gumus_tl=37.31,
            gram_gumus_degisim_1g=1.27,
            altin_gumus_rasyosu=80.90,
            rasyo_degisim_1g=-0.30,
            rasyo_degisim_1h=-4.40,
            rasyo_degisim_1a=-5.01,
            rasyo_degisim_ytd=-5.95,
            rasyo_degisim_1y=-5.58,
            rasyo_yorum="Altın/Gümüş oranı 80,90 seviyesinde; son 1 ayda gümüşün altına kıyasla daha hızlı yükselmesiyle rasyo %5,01 geriledi.",
        ),
        korku_acgozluluk_endeksleri=[
            FearGreedItem(
                piyasa="S&P 500 (ABD Borsası)",
                skor=68,
                durum_tr="Açgözlülük",
                onceki_gun=66,
                onceki_hafta=71,
                onceki_ay=62,
                aciklama="S&P 500 zirveye yakın seyrederken yatırımcı iştahı 'Açgözlülük' (Greed) bölgesinde güçlü kalmaya devam ediyor.",
            ),
            FearGreedItem(
                piyasa="Altın (Ons Gold)",
                skor=76,
                durum_tr="Aşırı Açgözlülük",
                onceki_gun=74,
                onceki_hafta=72,
                onceki_ay=65,
                aciklama="Merkez bankası alımları ve jeopolitik güvenli liman talebiyle altında 'Aşırı Açgözlülük' (Extreme Greed) momentumu hakim.",
            ),
            FearGreedItem(
                piyasa="Kripto Piyasası (BTC & Genel)",
                skor=72,
                durum_tr="Açgözlülük",
                onceki_gun=70,
                onceki_hafta=64,
                onceki_ay=54,
                aciklama="Bitcoin'in 68 bin dolar üzerinde tutunması ve ETF girişleriyle kripto duyarlılığı 'Açgözlülük' bölgesinde.",
            ),
        ],
        tefas_donemsel_liderler={
            "gunluk": [
                TefasTopFund("Son 1 Gün", 1, "TI2", "İş Portföy BIST Teknoloji Ağırlıklı Sınırlamalı Endeks Hisse Senedi Fonu", "Teknoloji & Yerli Hisse Kapsamı", 3.42, 3.42, 6.10, 4.80, 48.20, 62.40),
                TefasTopFund("Son 1 Gün", 2, "TAU", "İş Portföy BIST Banka Endeksi Hisse Senedi Fonu", "Bankacılık & Finans Sektörü Hisse Kapsamı", 2.85, 2.85, 5.90, 2.10, 64.50, 78.10),
                TefasTopFund("Son 1 Gün", 3, "GUM", "Ak Portföy Gümüş Fon Sepeti Fonu", "Altın & Kıymetli Madenler Kapsamı", 2.40, 2.40, 7.80, 12.40, 52.10, 66.80),
                TefasTopFund("Son 1 Gün", 4, "YHZ", "Yapı Kredi Portföy BIST Banka Endeksi Hisse Senedi Fonu", "Bankacılık & Finans Sektörü Hisse Kapsamı", 2.32, 2.32, 5.75, 1.95, 63.80, 76.90),
            ],
            "haftalik": [
                TefasTopFund("Son 1 Hafta", 1, "GUM", "Ak Portföy Gümüş Fon Sepeti Fonu", "Altın & Kıymetli Madenler Kapsamı", 7.80, 2.40, 7.80, 12.40, 52.10, 66.80),
                TefasTopFund("Son 1 Hafta", 2, "GTZ", "Garanti Portföy Gümüş Fon Sepeti Fonu", "Altın & Kıymetli Madenler Kapsamı", 7.45, 2.15, 7.45, 11.90, 50.80, 64.90),
                TefasTopFund("Son 1 Hafta", 3, "TI2", "İş Portföy BIST Teknoloji Ağırlıklı Sınırlamalı Endeks Hisse Senedi Fonu", "Teknoloji & Yerli Hisse Kapsamı", 6.10, 3.42, 6.10, 4.80, 48.20, 62.40),
                TefasTopFund("Son 1 Hafta", 4, "TAU", "İş Portföy BIST Banka Endeksi Hisse Senedi Fonu", "Bankacılık & Finans Sektörü Hisse Kapsamı", 5.90, 2.85, 5.90, 2.10, 64.50, 78.10),
            ],
            "aylik": [
                TefasTopFund("Son 1 Ay", 1, "GUM", "Ak Portföy Gümüş Fon Sepeti Fonu", "Altın & Kıymetli Madenler Kapsamı", 12.40, 2.40, 7.80, 12.40, 52.10, 66.80),
                TefasTopFund("Son 1 Ay", 2, "KZL", "Kuveyt Türk Portföy Altın Katılım Fonu", "Altın & Kıymetli Madenler Kapsamı", 8.90, 0.95, 3.10, 8.90, 49.40, 64.20),
                TefasTopFund("Son 1 Ay", 3, "AFT", "Ak Portföy Yeni Teknolojiler Yabancı Hisse Senedi Fonu", "Teknoloji & Yabancı Hisse Kapsamı", 7.15, 0.94, 2.40, 7.15, 44.60, 58.90),
                TefasTopFund("Son 1 Ay", 4, "YAY", "Yapı Kredi Portföy Yabancı Teknoloji Sektörü Hisse Senedi Fonu", "Teknoloji & Yabancı Hisse Kapsamı", 6.95, 0.88, 2.25, 6.95, 45.10, 60.40),
            ],
            "ytd": [
                TefasTopFund("Yılbaşından İtibaren (YTD)", 1, "IIH", "İstanbul Portföy Üçüncü Hisse Senedi Fonu", "Yerli Hisse Senedi (BIST) Kapsamı", 68.40, 1.65, 3.90, 2.40, 68.40, 84.50),
                TefasTopFund("Yılbaşından İtibaren (YTD)", 2, "TAU", "İş Portföy BIST Banka Endeksi Hisse Senedi Fonu", "Bankacılık & Finans Sektörü Hisse Kapsamı", 64.50, 2.85, 5.90, 2.10, 64.50, 78.10),
                TefasTopFund("Yılbaşından İtibaren (YTD)", 3, "MAC", "Marmara Capital Portföy Hisse Senedi Fonu", "Yerli Hisse Senedi (BIST) Kapsamı", 56.20, 1.38, 3.20, 1.80, 56.20, 71.40),
                TefasTopFund("Yılbaşından İtibaren (YTD)", 4, "GUM", "Ak Portföy Gümüş Fon Sepeti Fonu", "Altın & Kıymetli Madenler Kapsamı", 52.10, 2.40, 7.80, 12.40, 52.10, 66.80),
            ],
            "yillik": [
                TefasTopFund("Son 1 Yıl", 1, "IIH", "İstanbul Portföy Üçüncü Hisse Senedi Fonu", "Yerli Hisse Senedi (BIST) Kapsamı", 84.50, 1.65, 3.90, 2.40, 68.40, 84.50),
                TefasTopFund("Son 1 Yıl", 2, "TAU", "İş Portföy BIST Banka Endeksi Hisse Senedi Fonu", "Bankacılık & Finans Sektörü Hisse Kapsamı", 78.10, 2.85, 5.90, 2.10, 64.50, 78.10),
                TefasTopFund("Son 1 Yıl", 3, "MAC", "Marmara Capital Portföy Hisse Senedi Fonu", "Yerli Hisse Senedi (BIST) Kapsamı", 71.40, 1.38, 3.20, 1.80, 56.20, 71.40),
                TefasTopFund("Son 1 Yıl", 4, "GUM", "Ak Portföy Gümüş Fon Sepeti Fonu", "Altın & Kıymetli Madenler Kapsamı", 66.80, 2.40, 7.80, 12.40, 52.10, 66.80),
            ],
        },
        takip_edilen_fonlar=[
            TefasTopFund("Takip Listesi", 1, "TI2", "İş Portföy BIST Teknoloji Ağırlıklı Sınırlamalı Endeks Hisse Senedi Fonu", "Teknoloji & Yerli Hisse Kapsamı", 3.42, 3.42, 6.10, 4.80, 48.20, 62.40),
            TefasTopFund("Takip Listesi", 2, "TTE", "İş Portföy BIST Teknoloji Endeksi Hisse Senedi Fonu", "Teknoloji & Yerli Hisse Kapsamı", 2.95, 2.95, 5.40, 3.90, 41.50, 54.80),
            TefasTopFund("Takip Listesi", 3, "MAC", "Marmara Capital Portföy Hisse Senedi Fonu", "Yerli Hisse Senedi (BIST) Kapsamı", 1.38, 1.38, 3.20, 1.80, 56.20, 71.40),
            TefasTopFund("Takip Listesi", 4, "IPB", "İstanbul Portföy Birinci Değişken Fon", "Değişken / Aktif Dağılım Kapsamı", 0.88, 0.88, 2.40, 3.50, 46.80, 61.20),
            TefasTopFund("Takip Listesi", 5, "AFT", "Ak Portföy Yeni Teknolojiler Yabancı Hisse Senedi Fonu", "Teknoloji & Yabancı Hisse Kapsamı", 0.94, 0.94, 2.40, 7.15, 44.60, 58.90),
            TefasTopFund("Takip Listesi", 6, "KZL", "Kuveyt Türk Portföy Altın Katılım Fonu", "Altın & Kıymetli Madenler Kapsamı", 0.95, 0.95, 3.10, 8.90, 49.40, 64.20),
            TefasTopFund("Takip Listesi", 7, "PPN", "Nurol Portföy Para Piyasası Fonu", "Para Piyasası & Kısa Vadeli Likidite Kapsamı", 0.14, 0.14, 0.98, 4.18, 44.10, 55.60),
        ],
        kripto_varliklar=[
            MultiPeriodAsset("BTC-USD", "Bitcoin (BTC)", "Bitkoin", "USD", "kripto", 68450.00, 67206.00, 1.85, 3.40, 8.90, 4.20, 61.80, 98.40, "Lider Kripto", "Yahoo Finance"),
            MultiPeriodAsset("ETH-USD", "Ethereum (ETH)", "Eteryum", "USD", "kripto", 2640.00, 2615.00, 0.95, 1.80, 2.10, -18.40, 15.60, 44.20, "Akıllı Kontrat", "Yahoo Finance"),
            MultiPeriodAsset("XRP-USD", "Ripple (XRP)", "Ripıl İks Ar Pi", "USD", "kripto", 0.5420, 0.5340, 1.50, -1.20, -6.40, -8.90, -11.80, -1.40, "Ödeme Ağı", "Yahoo Finance"),
        ],
        kripto_piyasa_ozeti=CryptoGlobalSummary(
            total_mcap_trilyon_usd=2.36,
            total_mcap_degisim_1g=1.62,
            total_mcap_degisim_1h=2.84,
            total_mcap_degisim_1a=6.52,
            total_mcap_degisim_ytd=45.60,
            total_mcap_degisim_1y=79.40,
            btc_dominance_yuzde=57.45,
            eth_dominance_yuzde=13.40,
        ),
        tahvil_ve_cds=[
            MultiPeriodAsset("^FVX", "ABD 5 Yıllık Tahvil", "Amerika beş yıllık tahvil faizi", "%", "tahvil_cds", 4.03, 4.02, 0.30, 3.80, 14.20, -2.10, 4.80, -16.20, "ABD Hazine", "Yahoo Finance"),
            MultiPeriodAsset("^TNX", "ABD 10 Yıllık Tahvil", "Amerika on yıllık tahvil faizi", "%", "tahvil_cds", 4.21, 4.19, 0.45, 3.20, 12.60, -0.80, 8.50, -13.40, "ABD Gösterge", "Yahoo Finance"),
            MultiPeriodAsset("^TYX", "ABD 30 Yıllık Tahvil", "Amerika otuz yıllık tahvil faizi", "%", "tahvil_cds", 4.50, 4.48, 0.40, 2.60, 9.80, 0.90, 11.60, -9.80, "ABD Uzun Vade", "Yahoo Finance"),
            MultiPeriodAsset("TR2Y", "Türkiye 2 Yıllık Tahvil", "Türkiye iki yıllık gösterge tahvil faizi", "%", "tahvil_cds", 42.65, 42.71, -0.15, -0.45, 1.20, 2.40, 7.50, 14.80, "TR Gösterge", "Tahvil Piyasası"),
            MultiPeriodAsset("TR10Y", "Türkiye 10 Yıllık Tahvil", "Türkiye on yıllık tahvil faizi", "%", "tahvil_cds", 29.80, 29.83, -0.10, -0.80, 3.10, 5.20, 11.40, 8.90, "TR Uzun Vade", "Tahvil Piyasası"),
            MultiPeriodAsset("TR_CDS_5Y", "Türkiye 5 Yıllık CDS", "Türkiye beş yıllık Si Di Es risk primi", "bp", "tahvil_cds", 266.50, 268.00, -0.56, -1.80, -3.40, 1.20, -5.80, -34.20, "Ülke Risk Primi", "CDS Piyasası"),
        ],
        doviz_ve_dxy=[
            MultiPeriodAsset("USDTRY=X", "Dolar / TL", "Dolar Türk Lirası kuru", "TL", "doviz", 34.28, 34.24, 0.12, 0.32, 0.56, 3.88, 16.05, 22.40, "Kur", "Yahoo Finance"),
            MultiPeriodAsset("EURTRY=X", "Euro / TL", "Euro Türk Lirası kuru", "TL", "doviz", 37.15, 37.06, 0.25, -0.18, -2.10, 3.40, 13.80, 24.90, "Kur", "Yahoo Finance"),
            MultiPeriodAsset("EURUSD=X", "EUR / USD Paritesi", "Euro Dolar paritesi", "USD", "doviz", 1.0835, 1.0820, 0.14, -0.45, -2.65, -0.40, -1.95, 2.10, "Majör Parite", "Yahoo Finance"),
            MultiPeriodAsset("DX-Y.NYB", "DXY Dolar Endeksi", "Küresel Dolar Endeksi Diksiy", "puan", "doviz", 104.25, 104.10, 0.14, 0.65, 3.40, -0.15, 2.85, -1.90, "Küresel Dolar", "Yahoo Finance"),
        ],
        petrol_ve_emtia=[
            MultiPeriodAsset("BZ=F", "Brent Petrol", "Brent petrol", "USD", "emtia", 74.90, 75.39, -0.65, 2.40, 1.80, -7.80, -2.80, -15.40, "Enerji", "Yahoo Finance"),
            MultiPeriodAsset("HG=F", "Bakır (Dr. Copper)", "Bakır", "USD", "emtia", 4.38, 4.35, 0.69, 0.45, -2.10, 6.40, 12.60, 21.80, "Sanayi Metali", "Yahoo Finance"),
            MultiPeriodAsset("ZW=F", "Buğday", "Buğday", "cent", "emtia", 572.50, 578.00, -0.95, -2.80, -1.40, 4.60, -8.90, -1.20, "Tarım Emtiası", "Yahoo Finance"),
            MultiPeriodAsset("KC=F", "Kahve", "Kahve", "cent", "emtia", 248.40, 251.20, -1.11, -3.10, -6.80, 6.20, 31.80, 49.50, "Tarım Emtiası", "Yahoo Finance"),
        ],
        ekonomik_takvim_bugun=[
            EconomicEvent("bugun", d_str, "10:00", "Türkiye (TCMB/TÜİK)", "Yüksek", "TCMB Piyasa Katılımcıları Anketi ve Enflasyon Beklentileri", "%43,11", "%43,50", "%43,14"),
            EconomicEvent("bugun", d_str, "14:00", "Türkiye (TCMB)", "Yüksek", "TCMB Para Politikası Kurulu (PPK) Faiz Kararı Özeti", "%50,00", "%50,00", "%50,00"),
            EconomicEvent("bugun", d_str, "15:30", "ABD (Fed/Makro)", "Yüksek", "Dayanıklı Mal Siparişleri (Aylık)", "-0.8%", "-1.0%", "0.0%"),
            EconomicEvent("bugun", d_str, "17:00", "ABD (Fed/Makro)", "Yüksek", "Michigan Tüketici Güven Endeksi ve Enflasyon Beklentisi", "70.5", "69.0", "68.9"),
        ],
        ekonomik_takvim_bu_hafta=[
            EconomicEvent("bu_hafta", "2026-10-26", "15:30", "ABD (Fed/Makro)", "Yüksek", "Haftalık İşsizlik Maaşı Başvuruları", "-", "240K", "227K"),
            EconomicEvent("bu_hafta", "2026-10-26", "16:45", "ABD (Fed/Makro)", "Yüksek", "Öncü İmalat ve Hizmetler PMI Verileri", "-", "47.5", "47.3"),
        ],
        ekonomik_takvim_gelecek_hafta=[
            EconomicEvent("gelecek_hafta", "2026-10-30", "15:30", "ABD (Fed/Makro)", "Yüksek", "ABD 3. Çeyrek Öncü GSYH Büyüme Oranı (Çeyreklik)", "-", "%3,0", "%3,0"),
            EconomicEvent("gelecek_hafta", "2026-10-31", "14:30", "Türkiye (TCMB)", "Yüksek", "TCMB Haftalık Döviz Rezervleri ve Yabancı Menkul Kıymet İstatistikleri", "-", "-", "-"),
            EconomicEvent("gelecek_hafta", "2026-10-31", "15:30", "ABD (Fed/Makro)", "Yüksek", "Fed'in Favori Enflasyon Göstergesi: Çekirdek PCE Fiyat Endeksi", "-", "%0,3", "%0,1"),
            EconomicEvent("gelecek_hafta", "2026-11-01", "15:30", "ABD (Fed/Makro)", "Yüksek", "ABD Tarım Dışı İstihdam (NFP) ve İşsizlik Oranı", "-", "115K / %4,1", "254K / %4,1"),
            EconomicEvent("gelecek_hafta", "2026-11-04", "10:00", "Türkiye (TÜİK)", "Yüksek", "TÜİK Ekim Ayı TÜFE ve ÜFE Enflasyon Verileri", "-", "%2,45", "%2,97"),
        ],
        otorite_ve_banka_haberleri=[
            NewsHeadline(
                "TCMB Başkanı Karahan: Dezenflasyon sürecinde hizmet enflasyonundaki katılığın zayıflamasını yakından izliyoruz",
                "Bloomberg HT",
                "otorite_banka",
                etiketler=["TCMB", "Karahan", "Enflasyon"],
            ),
            NewsHeadline(
                "Goldman Sachs ve Morgan Stanley, Türkiye için yıl sonu politika faizi ve enflasyon patikası tahminlerini güncelledi",
                "Ekonomim",
                "otorite_banka",
                etiketler=["Goldman Sachs", "Morgan Stanley", "Faiz"],
            ),
            NewsHeadline(
                "BofA (Bank of America) Raporu: Türk tahvillerine ve bankacılık hisselerine yabancı ilgisi devam ediyor",
                "Dünya Gazetesi",
                "otorite_banka",
                etiketler=["BofA", "Tahvil"],
            ),
            NewsHeadline(
                "Fed yetkililerinden faiz indirimi mesajı: İstihdam piyasası dengelenirken kademeli gevşeme sürecek",
                "CNBC-e",
                "otorite_banka",
                etiketler=["Fed", "Faiz"],
            ),
            NewsHeadline(
                "Hazine ve Maliye Bakanı Mehmet Şimşek: Cari açıktaki düşüş ve rezerv birikimi makro finansal istikrarı güçlendiriyor",
                "Anadolu Ajansı",
                "otorite_banka",
                etiketler=["Hazine", "Şimşek", "Rezerv"],
            ),
        ],
        konut_ve_arac_istatistikleri=[
            NewsHeadline(
                "TÜİK Konut Satış İstatistikleri: Türkiye genelinde konut satışları bir önceki yılın aynı ayına göre %37,3 artarak 140 bin 919 oldu",
                "TÜİK / Bloomberg HT",
                "konut",
                etiketler=["Konut İstatistikleri", "TÜİK"],
            ),
            NewsHeadline(
                "İpotekli konut satışları yıllık bazda %60,3 artış gösterirken toplam satışlar içindeki payı %11,2 olarak gerçekleşti",
                "TÜİK / Ekonomim",
                "konut",
                etiketler=["Konut İstatistikleri", "TÜİK"],
            ),
            NewsHeadline(
                "ODMD Verileri: Türkiye otomobil ve hafif ticari araç toplam pazarı Ocak-Eylül döneminde 849 bin 892 adet seviyesinde gerçekleşti",
                "ODMD / Otomotiv Sektörü",
                "arac",
                etiketler=["Otomotiv Pazarı", "ODMD"],
            ),
            NewsHeadline(
                "Otomobil satışlarında elektrikli ve hibrit araçların toplam pazar payı %25 sınırını aştı",
                "ODMD / Dünya",
                "arac",
                etiketler=["Otomotiv Pazarı", "ODMD"],
            ),
        ],
        grafik_verileri=demo_charts,
    )
