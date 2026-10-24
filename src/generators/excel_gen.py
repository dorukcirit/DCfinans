from pathlib import Path
from typing import List, Optional
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from src.models import DailyFinanceReport, MultiPeriodAsset, classify_trend


HEADER_FILL = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
SUBHEADER_FILL = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
SUBHEADER_FONT = Font(name="Calibri", size=10, bold=True, color="F8FAFC")

GREEN_FILL = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
GREEN_FONT = Font(name="Calibri", size=10, bold=True, color="166534")
RED_FILL = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
RED_FONT = Font(name="Calibri", size=10, bold=True, color="991B1B")
NEUTRAL_FILL = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
NEUTRAL_FONT = Font(name="Calibri", size=10, bold=False, color="475569")

THIN_BORDER = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)


def _style_header_row(ws, row_idx: int, col_count: int):
    for col in range(1, col_count + 1):
        cell = ws.cell(row=row_idx, column=col)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
    ws.row_dimensions[row_idx].height = 24


def _apply_pct_style(cell, pct_val: Optional[float], threshold: float = 0.20):
    cell.border = THIN_BORDER
    cell.alignment = Alignment(horizontal="right", vertical="center")
    if pct_val is None:
        cell.value = "-"
        cell.fill = NEUTRAL_FILL
        cell.font = NEUTRAL_FONT
        return
    yon = classify_trend(pct_val, threshold)
    sign = "+" if pct_val > 0 else ""
    cell.value = f"{sign}{pct_val:.2f}% ({yon})"
    if yon == "Artış":
        cell.fill = GREEN_FILL
        cell.font = GREEN_FONT
    elif yon == "Azalış":
        cell.fill = RED_FILL
        cell.font = RED_FONT
    else:
        cell.fill = NEUTRAL_FILL
        cell.font = NEUTRAL_FONT


def _auto_fit_columns(ws, max_width: int = 48):
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), max_width)


def _find_asset(assets: List[MultiPeriodAsset], kod: str) -> Optional[MultiPeriodAsset]:
    return next((a for a in assets if a.kod == kod), None)


def update_excel_workbook(report: DailyFinanceReport, master_excel_path: Path, daily_excel_path: Optional[Path] = None):
    """
    Her gün kümülatif Excel dosyasındaki 'Gunluk_Arsiv_Log' sayfasına o günün satırını ekler/günceller
    ve diğer tüm detaylı analiz sayfalarını (Çoklu Dönem, BIST Dolar Teknik, TEFAS Liderler,
    Ekonomik Takvim, Haberler & Fear-Greed) güncel verilerle yeniler.
    """
    if master_excel_path.exists():
        try:
            wb = openpyxl.load_workbook(master_excel_path)
        except Exception:
            wb = openpyxl.Workbook()
    else:
        wb = openpyxl.Workbook()

    # Varsayılan boş 'Sheet' varsa adını Gunluk_Arsiv_Log yap
    if "Sheet" in wb.sheetnames and "Gunluk_Arsiv_Log" not in wb.sheetnames:
        wb["Sheet"].title = "Gunluk_Arsiv_Log"

    # -------------------------------------------------------------------------
    # SAYFA 1: GUNLUK_ARSIV_LOG (Her gün 1 satır eklenen kümülatif tarihsel tablo)
    # -------------------------------------------------------------------------
    if "Gunluk_Arsiv_Log" not in wb.sheetnames:
        ws_log = wb.create_sheet("Gunluk_Arsiv_Log", 0)
    else:
        ws_log = wb["Gunluk_Arsiv_Log"]

    log_headers = [
        "Tarih",
        "BIST 100 (TL)",
        "BIST 100 Günlük %",
        "BIST 100 (USD)",
        "BIST USD 52H Zirveye Uzaklık %",
        "BIST USD 52H Dipten Uzaklık %",
        "BIST USD MA200",
        "BIST USD RSI(14)",
        "S&P 500",
        "S&P 500 Günlük %",
        "Ons Altın ($)",
        "Gram Altın (TL)",
        "Ons Gümüş ($)",
        "Gram Gümüş (TL)",
        "Altın/Gümüş Oranı",
        "Dolar/TL",
        "Euro/TL",
        "EUR/USD",
        "DXY Endeksi",
        "ABD 10Y Tahvil %",
        "TR 2Y Tahvil %",
        "TR 10Y Tahvil %",
        "TR 5Y CDS",
        "Bitcoin ($)",
        "Ethereum ($)",
        "XRP ($)",
        "Kripto Total MCap (T$)",
        "BTC Dominance %",
        "Brent Petrol ($)",
        "Bakır ($)",
        "F&G S&P 500",
        "F&G Altın",
        "F&G Kripto",
        "TEFAS Günlük Şampiyon",
        "TEFAS Yıllık Şampiyon",
    ]

    if ws_log.max_row == 1 and ws_log.cell(1, 1).value is None:
        for c_idx, h_text in enumerate(log_headers, start=1):
            ws_log.cell(1, c_idx, h_text)
        _style_header_row(ws_log, 1, len(log_headers))

    # Aynı tarihli satır varsa üzerine yaz, yoksa yeni satır ekle
    target_row = ws_log.max_row + 1
    for r_idx in range(2, ws_log.max_row + 1):
        if str(ws_log.cell(r_idx, 1).value) == report.tarih:
            target_row = r_idx
            break

    bist100 = _find_asset(report.bist_endeksleri, "XU100.IS")
    sp500 = _find_asset(report.abd_ve_kuresel_endeksler, "^GSPC")
    gold_u = _find_asset(report.altin_ve_gumus_usd, "GC=F")
    silv_u = _find_asset(report.altin_ve_gumus_usd, "SI=F")
    usdtry = _find_asset(report.doviz_ve_dxy, "USDTRY=X")
    eurtry = _find_asset(report.doviz_ve_dxy, "EURTRY=X")
    eurusd = _find_asset(report.doviz_ve_dxy, "EURUSD=X")
    dxy = _find_asset(report.doviz_ve_dxy, "DX-Y.NYB")
    us10y = _find_asset(report.tahvil_ve_cds, "^TNX")
    tr2y = _find_asset(report.tahvil_ve_cds, "TR2Y")
    tr10y = _find_asset(report.tahvil_ve_cds, "TR10Y")
    trcds = _find_asset(report.tahvil_ve_cds, "TR_CDS_5Y")
    btc = _find_asset(report.kripto_varliklar, "BTC-USD")
    eth = _find_asset(report.kripto_varliklar, "ETH-USD")
    xrp = _find_asset(report.kripto_varliklar, "XRP-USD")
    brent = _find_asset(report.petrol_ve_emtia, "BZ=F")
    copper = _find_asset(report.petrol_ve_emtia, "HG=F")

    bt = report.bist100_dolar_teknik
    gs = report.altin_gumus_ozet
    cp = report.kripto_piyasa_ozeti

    fg_sp = next((x.skor for x in report.korku_acgozluluk_endeksleri if "S&P" in x.piyasa), None)
    fg_au = next((x.skor for x in report.korku_acgozluluk_endeksleri if "Altın" in x.piyasa), None)
    fg_cr = next((x.skor for x in report.korku_acgozluluk_endeksleri if "Kripto" in x.piyasa), None)

    tefas_1g_top = report.tefas_donemsel_liderler.get("gunluk", [])
    tefas_1y_top = report.tefas_donemsel_liderler.get("yillik", [])
    t1g_str = f"{tefas_1g_top[0].kod} (%{tefas_1g_top[0].ilgili_donem_getiri_yuzde})" if tefas_1g_top else "-"
    t1y_str = f"{tefas_1y_top[0].kod} (%{tefas_1y_top[0].ilgili_donem_getiri_yuzde})" if tefas_1y_top else "-"

    row_values = [
        report.tarih,
        bist100.fiyat if bist100 else None,
        bist100.degisim_1g if bist100 else None,
        bt.guncel_usd,
        bt.tavana_uzaklik_52h_yuzde,
        bt.tabana_uzaklik_52h_yuzde,
        bt.ma200_usd,
        bt.rsi14_usd,
        sp500.fiyat if sp500 else None,
        sp500.degisim_1g if sp500 else None,
        gold_u.fiyat if gold_u else None,
        gs.gram_altin_tl,
        silv_u.fiyat if silv_u else None,
        gs.gram_gumus_tl,
        gs.altin_gumus_rasyosu,
        usdtry.fiyat if usdtry else None,
        eurtry.fiyat if eurtry else None,
        eurusd.fiyat if eurusd else None,
        dxy.fiyat if dxy else None,
        us10y.fiyat if us10y else None,
        tr2y.fiyat if tr2y else None,
        tr10y.fiyat if tr10y else None,
        trcds.fiyat if trcds else None,
        btc.fiyat if btc else None,
        eth.fiyat if eth else None,
        xrp.fiyat if xrp else None,
        cp.total_mcap_trilyon_usd,
        cp.btc_dominance_yuzde,
        brent.fiyat if brent else None,
        copper.fiyat if copper else None,
        fg_sp,
        fg_au,
        fg_cr,
        t1g_str,
        t1y_str,
    ]

    for c_idx, val in enumerate(row_values, start=1):
        c = ws_log.cell(target_row, c_idx, val)
        c.border = THIN_BORDER
    _auto_fit_columns(ws_log)

    # Yardımcı fonksiyon: Sayfayı sıfırlayıp yeniden oluşturma
    def _recreate_sheet(title: str):
        if title in wb.sheetnames:
            del wb[title]
        return wb.create_sheet(title)

    # -------------------------------------------------------------------------
    # SAYFA 2: COKLU_DONEM_PERFORMANS (Tüm Varlıklar 1G, 1H, 1A, 3A, YTD, 1Y)
    # -------------------------------------------------------------------------
    ws_perf = _recreate_sheet("Coklu_Donem_Performans")
    perf_headers = [
        "Grup",
        "Kod",
        "Varlık / Endeks Adı",
        "Son Değer",
        "Birim",
        "Günlük (1G)",
        "1 Hafta (1H)",
        "1 Ay (1A)",
        "3 Ay (3A)",
        "Yılbaşı (YTD)",
        "1 Yıl (1Y)",
        "Kaynak / Not",
    ]
    for idx, h in enumerate(perf_headers, start=1):
        ws_perf.cell(1, idx, h)
    _style_header_row(ws_perf, 1, len(perf_headers))

    all_groups = [
        ("BIST Endeksleri (TL)", report.bist_endeksleri),
        ("ABD & Küresel Endeksler", report.abd_ve_kuresel_endeksler),
        ("Altın & Gümüş (USD)", report.altin_ve_gumus_usd),
        ("Kripto Varlıklar", report.kripto_varliklar),
        ("Döviz & DXY", report.doviz_ve_dxy),
        ("Tahvil & CDS", report.tahvil_ve_cds),
        ("Petrol & Emtia", report.petrol_ve_emtia),
    ]
    r_curr = 2
    for grp_name, assets in all_groups:
        for a in assets:
            ws_perf.cell(r_curr, 1, grp_name).border = THIN_BORDER
            ws_perf.cell(r_curr, 2, a.kod).border = THIN_BORDER
            c_name = ws_perf.cell(r_curr, 3, a.ad)
            c_name.font = Font(bold=True)
            c_name.border = THIN_BORDER
            c_price = ws_perf.cell(r_curr, 4, a.fiyat)
            c_price.border = THIN_BORDER
            ws_perf.cell(r_curr, 5, a.birim).border = THIN_BORDER

            _apply_pct_style(ws_perf.cell(r_curr, 6), a.degisim_1g, 0.10)
            _apply_pct_style(ws_perf.cell(r_curr, 7), a.degisim_1h, 0.25)
            _apply_pct_style(ws_perf.cell(r_curr, 8), a.degisim_1a, 0.50)
            _apply_pct_style(ws_perf.cell(r_curr, 9), a.degisim_3a, 0.75)
            _apply_pct_style(ws_perf.cell(r_curr, 10), a.degisim_ytd, 0.75)
            _apply_pct_style(ws_perf.cell(r_curr, 11), a.degisim_1y, 1.00)

            ws_perf.cell(r_curr, 12, a.not_bilgisi or a.kaynak).border = THIN_BORDER
            r_curr += 1

    # Gram Altın, Gram Gümüş (Sadece Günlük TL) ve Altın/Gümüş Oranı satırlarını da ekle
    ws_perf.cell(r_curr, 1, "Altın & Gümüş (TL / Rasyo)").border = THIN_BORDER
    ws_perf.cell(r_curr, 2, "GRAM_ALTIN_TL").border = THIN_BORDER
    ws_perf.cell(r_curr, 3, "Gram Altın (Sadece Günlük TL)").font = Font(bold=True)
    ws_perf.cell(r_curr, 4, gs.gram_altin_tl).border = THIN_BORDER
    ws_perf.cell(r_curr, 5, "TL").border = THIN_BORDER
    _apply_pct_style(ws_perf.cell(r_curr, 6), gs.gram_altin_degisim_1g, 0.10)
    for col_empty in range(7, 12):
        ws_perf.cell(r_curr, col_empty, "Sadece Günlük TL").border = THIN_BORDER
    ws_perf.cell(r_curr, 12, "Ons × USD/TRY").border = THIN_BORDER
    r_curr += 1

    ws_perf.cell(r_curr, 1, "Altın & Gümüş (TL / Rasyo)").border = THIN_BORDER
    ws_perf.cell(r_curr, 2, "XAU_XAG").border = THIN_BORDER
    ws_perf.cell(r_curr, 3, "Altın / Gümüş Oranı (Rasyo)").font = Font(bold=True)
    ws_perf.cell(r_curr, 4, gs.altin_gumus_rasyosu).border = THIN_BORDER
    ws_perf.cell(r_curr, 5, "Kat").border = THIN_BORDER
    _apply_pct_style(ws_perf.cell(r_curr, 6), gs.rasyo_degisim_1g, 0.10)
    _apply_pct_style(ws_perf.cell(r_curr, 7), gs.rasyo_degisim_1h, 0.25)
    _apply_pct_style(ws_perf.cell(r_curr, 8), gs.rasyo_degisim_1a, 0.50)
    ws_perf.cell(r_curr, 9, "-").border = THIN_BORDER
    _apply_pct_style(ws_perf.cell(r_curr, 10), gs.rasyo_degisim_ytd, 0.75)
    _apply_pct_style(ws_perf.cell(r_curr, 11), gs.rasyo_degisim_1y, 1.00)
    ws_perf.cell(r_curr, 12, gs.rasyo_yorum).border = THIN_BORDER

    _auto_fit_columns(ws_perf)

    # -------------------------------------------------------------------------
    # SAYFA 3: BIST100_DOLAR_TEKNIK (Dolar Bazlı Performans + Taban/Tavan Analizi)
    # -------------------------------------------------------------------------
    ws_bist = _recreate_sheet("BIST100_Dolar_Teknik")
    b_headers = ["Analiz Kategorisi", "Gösterge / Seviye Adı", "Değer (USD / %)", "Referans Tarih / Detay", "Yorum / Durum"]
    for idx, h in enumerate(b_headers, start=1):
        ws_bist.cell(1, idx, h)
    _style_header_row(ws_bist, 1, len(b_headers))

    bist_rows = [
        ("Fiyat & Kur", "BIST 100 Güncel (USD Bazlı)", bt.guncel_usd, f"TL: {bt.guncel_tl} / Kur: {bt.usdtry_kuru}", "XU100 / USDTRY"),
        ("Dolar Performansı", "Günlük Değişim (USD)", f"%{bt.degisim_1g_usd}", "1 İş Günü", classify_trend(bt.degisim_1g_usd, 0.1)),
        ("Dolar Performansı", "Son 1 Hafta Değişim (USD)", f"%{bt.degisim_1h_usd}", "5 İş Günü", classify_trend(bt.degisim_1h_usd, 0.25)),
        ("Dolar Performansı", "Son 1 Ay Değişim (USD)", f"%{bt.degisim_1a_usd}", "21 İş Günü", classify_trend(bt.degisim_1a_usd, 0.50)),
        ("Dolar Performansı", "Son 3 Ay Değişim (USD)", f"%{bt.degisim_3a_usd}", "63 İş Günü", classify_trend(bt.degisim_3a_usd, 0.75)),
        ("Dolar Performansı", "Yılbaşından İtibaren YTD (USD)", f"%{bt.degisim_ytd_usd}", "YTD", classify_trend(bt.degisim_ytd_usd, 0.75)),
        ("Dolar Performansı", "Son 1 Yıl Değişim (USD)", f"%{bt.degisim_1y_usd}", "252 İş Günü", classify_trend(bt.degisim_1y_usd, 1.00)),
        ("52 Haftalık Tavan/Taban", "52 Haftalık (1 Yıl) Dolar Tavanı (Zirve)", bt.tavan_52h_usd, bt.tavan_52h_tarih, f"Zirveden %{bt.tavana_uzaklik_52h_yuzde} aşağıda"),
        ("52 Haftalık Tavan/Taban", "52 Haftalık (1 Yıl) Dolar Tabanı (Dip)", bt.taban_52h_usd, bt.taban_52h_tarih, f"Dipten +%{bt.tabana_uzaklik_52h_yuzde} yukarıda"),
        ("52 Haftalık Tavan/Taban", "1 Yıllık Dolar Kanal Konumu (%0 Dip - %100 Zirve)", f"%{bt.kanal_konumu_52h_yuzde}", "Donchian Kanalı", "Alt/Orta/Üst Bant Konumu"),
        ("3 Aylık Tavan/Taban", "Son 3 Ayın En Yüksek Dolar Tavanı", bt.tavan_3a_usd, "63 İş Günü", f"Tavana uzaklık: %{bt.tavana_uzaklik_3a_yuzde}"),
        ("3 Aylık Tavan/Taban", "Son 3 Ayın En Düşük Dolar Tabanı", bt.taban_3a_usd, "63 İş Günü", f"Tabandan uzaklık: +%{bt.tabana_uzaklik_3a_yuzde}"),
        ("Pivot / Swing Noktaları", "Son Yerel Swing Tavan (Pivot Direnç)", bt.son_swing_tavan_usd, bt.son_swing_tavan_tarih, f"Uzaklık: %{bt.swing_tavana_uzaklik_yuzde}"),
        ("Pivot / Swing Noktaları", "Son Yerel Swing Taban (Pivot Destek)", bt.son_swing_taban_usd, bt.son_swing_taban_tarih, f"Uzaklık: +%{bt.swing_tabana_uzaklik_yuzde}"),
        ("Fibonacci Seviyeleri", "Fibonacci %61.8 Düzeltme Destek/Direnci", bt.fib_618_usd, "1Y Dalga", "Altın Oran Seviyesi"),
        ("Fibonacci Seviyeleri", "Fibonacci %50.0 Denge Seviyesi", bt.fib_500_usd, "1Y Dalga", "Yarı Düzeltme Seviyesi"),
        ("Fibonacci Seviyeleri", "Fibonacci %38.2 Direnç Seviyesi", bt.fib_382_usd, "1Y Dalga", "Üst Düzeltme Seviyesi"),
        ("Ortalamalar & Momentum", "50 Günlük Dolar Hareketli Ortalama (MA50)", bt.ma50_usd, "Kısa-Orta Vade", "USD Bazlı MA50"),
        ("Ortalamalar & Momentum", "200 Günlük Dolar Hareketli Ortalama (MA200)", bt.ma200_usd, "Uzun Vade Ana Trend", "USD Bazlı MA200"),
        ("Ortalamalar & Momentum", "14 Günlük Göreceli Güç Endeksi (RSI 14)", bt.rsi14_usd, "30 Aşırı Satım / 70 Aşırı Alım", bt.teknik_ozet_yorum),
    ]
    for r_i, row_data in enumerate(bist_rows, start=2):
        for c_i, val in enumerate(row_data, start=1):
            cell = ws_bist.cell(r_i, c_i, val)
            cell.border = THIN_BORDER
            if c_i == 2:
                cell.font = Font(bold=True)
    _auto_fit_columns(ws_bist, max_width=65)

    # -------------------------------------------------------------------------
    # SAYFA 4: TEFAS_EN_COK_KAZANDIRANLAR
    # -------------------------------------------------------------------------
    ws_tefas = _recreate_sheet("TEFAS_En_Cok_Kazandiranlar")
    t_headers = [
        "Dönem Kategorisi",
        "Sıra",
        "Fon Kodu",
        "Fon Adı",
        "Kapsamı / Şemsiye Fon Türü",
        "Günlük %",
        "1 Hafta %",
        "1 Ay %",
        "Yılbaşı (YTD) %",
        "1 Yıl %",
    ]
    for idx, h in enumerate(t_headers, start=1):
        ws_tefas.cell(1, idx, h)
    _style_header_row(ws_tefas, 1, len(t_headers))

    r_t = 2
    for p_key in ("gunluk", "haftalik", "aylik", "ytd", "yillik"):
        for f in report.tefas_donemsel_liderler.get(p_key, []):
            ws_tefas.cell(r_t, 1, f.donem_etiketi).border = THIN_BORDER
            ws_tefas.cell(r_t, 2, f.sira).border = THIN_BORDER
            c_kod = ws_tefas.cell(r_t, 3, f.kod)
            c_kod.font = Font(bold=True)
            c_kod.border = THIN_BORDER
            ws_tefas.cell(r_t, 4, f.ad).border = THIN_BORDER
            ws_tefas.cell(r_t, 5, f.kapsam_turu).border = THIN_BORDER
            _apply_pct_style(ws_tefas.cell(r_t, 6), f.getiri_1g, 0.1)
            _apply_pct_style(ws_tefas.cell(r_t, 7), f.getiri_1h, 0.25)
            _apply_pct_style(ws_tefas.cell(r_t, 8), f.getiri_1a, 0.50)
            _apply_pct_style(ws_tefas.cell(r_t, 9), f.getiri_ytd, 0.75)
            _apply_pct_style(ws_tefas.cell(r_t, 10), f.getiri_1y, 1.00)
            r_t += 1

    for f in report.takip_edilen_fonlar:
        ws_tefas.cell(r_t, 1, "Takip Listesi").border = THIN_BORDER
        ws_tefas.cell(r_t, 2, f.sira).border = THIN_BORDER
        ws_tefas.cell(r_t, 3, f.kod).border = THIN_BORDER
        ws_tefas.cell(r_t, 4, f.ad).border = THIN_BORDER
        ws_tefas.cell(r_t, 5, f.kapsam_turu).border = THIN_BORDER
        _apply_pct_style(ws_tefas.cell(r_t, 6), f.getiri_1g, 0.1)
        _apply_pct_style(ws_tefas.cell(r_t, 7), f.getiri_1h, 0.25)
        _apply_pct_style(ws_tefas.cell(r_t, 8), f.getiri_1a, 0.50)
        _apply_pct_style(ws_tefas.cell(r_t, 9), f.getiri_ytd, 0.75)
        _apply_pct_style(ws_tefas.cell(r_t, 10), f.getiri_1y, 1.00)
        r_t += 1

    _auto_fit_columns(ws_tefas, max_width=55)

    # -------------------------------------------------------------------------
    # SAYFA 5: EKONOMIK_TAKVIM_2HAFTA (Bugün, Bu Hafta, Gelecek Hafta)
    # -------------------------------------------------------------------------
    ws_cal = _recreate_sheet("Ekonomik_Takvim_2Hafta")
    c_headers = ["Dönem", "Tarih", "Saat", "Ülke / Kurum", "Önem", "Veri / Olay Başlığı", "Açıklanan", "Beklenti", "Önceki"]
    for idx, h in enumerate(c_headers, start=1):
        ws_cal.cell(1, idx, h)
    _style_header_row(ws_cal, 1, len(c_headers))

    r_c = 2
    for label, ev_list in [
        ("Bugün Açıklananlar", report.ekonomik_takvim_bugun),
        ("Bu Hafta Açıklanacaklar", report.ekonomik_takvim_bu_hafta),
        ("Gelecek Hafta Açıklanacaklar", report.ekonomik_takvim_gelecek_hafta),
    ]:
        for ev in ev_list:
            vals = [label, ev.tarih, ev.saat, ev.ulke, ev.onem, ev.baslik, ev.gerceklesen, ev.beklenti, ev.onceki]
            for c_i, v in enumerate(vals, start=1):
                cell = ws_cal.cell(r_c, c_i, v)
                cell.border = THIN_BORDER
            r_c += 1
    _auto_fit_columns(ws_cal, max_width=60)

    # -------------------------------------------------------------------------
    # SAYFA 6: DUYARLILIK_VE_HABERLER (Fear & Greed + Otorite/Banka + Konut/Araç)
    # -------------------------------------------------------------------------
    ws_news = _recreate_sheet("Duyarlilik_ve_Haberler")
    n_headers = ["Kategori", "Kaynak / Piyasa", "Başlık / Duyarlılık Detayı", "Skor / Etiketler"]
    for idx, h in enumerate(n_headers, start=1):
        ws_news.cell(1, idx, h)
    _style_header_row(ws_news, 1, len(n_headers))

    r_n = 2
    for fg in report.korku_acgozluluk_endeksleri:
        ws_news.cell(r_n, 1, "Fear & Greed Endeksi").border = THIN_BORDER
        ws_news.cell(r_n, 2, fg.piyasa).border = THIN_BORDER
        ws_news.cell(r_n, 3, fg.aciklama).border = THIN_BORDER
        ws_news.cell(r_n, 4, f"{fg.skor}/100 ({fg.durum_tr})").border = THIN_BORDER
        r_n += 1

    for h in report.otorite_ve_banka_haberleri:
        ws_news.cell(r_n, 1, "Otorite / Banka Açıklaması").border = THIN_BORDER
        ws_news.cell(r_n, 2, h.kaynak).border = THIN_BORDER
        ws_news.cell(r_n, 3, h.baslik).border = THIN_BORDER
        ws_news.cell(r_n, 4, ", ".join(h.etiketler)).border = THIN_BORDER
        r_n += 1

    for s in report.konut_ve_arac_istatistikleri:
        kat_label = "TÜİK Konut İstatistikleri" if s.kategori == "konut" else "ODMD Araç İstatistikleri"
        ws_news.cell(r_n, 1, kat_label).border = THIN_BORDER
        ws_news.cell(r_n, 2, s.kaynak).border = THIN_BORDER
        ws_news.cell(r_n, 3, s.baslik).border = THIN_BORDER
        ws_news.cell(r_n, 4, ", ".join(s.etiketler)).border = THIN_BORDER
        r_n += 1

    _auto_fit_columns(ws_news, max_width=75)

    master_excel_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(master_excel_path)

    if daily_excel_path is not None:
        daily_excel_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(daily_excel_path)
