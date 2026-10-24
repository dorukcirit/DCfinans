from typing import List
from src.models import (
    DailyFinanceReport,
    EconomicEvent,
    MultiPeriodAsset,
    TefasTopFund,
    classify_trend,
    trend_icon,
)


def _fmt_num(val: float | None, birim: str = "") -> str:
    if val is None:
        return "Veri Yok"
    if birim == "%":
        s = f"%{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return s
    s = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} {birim}".strip()


def _fmt_pct_with_trend(val: float | None, threshold: float = 0.20) -> str:
    if val is None:
        return "-"
    sign = "+" if val > 0 else ""
    pct_str = f"{sign}{val:.2f}%".replace(".", ",")
    yon = classify_trend(val, threshold)
    ikon = "🟢" if yon == "Artış" else ("🔴" if yon == "Azalış" else "⚪")
    return f"{ikon} **{pct_str}** *({yon})*"


def _fmt_pct_short(val: float | None) -> str:
    if val is None:
        return "-"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%".replace(".", ",")


def _render_multi_period_table(assets: List[MultiPeriodAsset]) -> str:
    lines = [
        "| Varlık / Endeks | Kapanış / Son | Günlük (1G) | 1 Hafta (1H) | 1 Ay (1A) | 3 Ay (3A) | Yılbaşı (YTD) | 1 Yıl (1Y) |",
        "|:---|---:|:---|:---|:---|:---|:---|:---|",
    ]
    for a in assets:
        lines.append(
            f"| **{a.ad}** (`{a.kod}`) | **{_fmt_num(a.fiyat, a.birim)}** | "
            f"{_fmt_pct_with_trend(a.degisim_1g, 0.10)} | "
            f"{_fmt_pct_with_trend(a.degisim_1h, 0.25)} | "
            f"{_fmt_pct_with_trend(a.degisim_1a, 0.50)} | "
            f"{_fmt_pct_with_trend(a.degisim_3a, 0.75)} | "
            f"{_fmt_pct_with_trend(a.degisim_ytd, 0.75)} | "
            f"{_fmt_pct_with_trend(a.degisim_1y, 1.00)} |"
        )
    return "\n".join(lines)


def _render_calendar_table(events: List[EconomicEvent]) -> str:
    if not events:
        return "_Bu dönem için listelenen yüksek/orta önemde veri bulunmuyor._"
    lines = [
        "| Tarih | Saat | Ülke / Kurum | Önem | Veri / Karar Başlığı | Açıklanan | Beklenti | Önceki |",
        "|:---|:---:|:---|:---:|:---|---:|---:|---:|",
    ]
    for ev in events:
        onem_s = "🔥 Yüksek" if ev.onem == "Yüksek" else "🔸 Orta"
        lines.append(
            f"| `{ev.tarih}` | `{ev.saat}` | **{ev.ulke}** | {onem_s} | {ev.baslik} | "
            f"**{ev.gerceklesen}** | {ev.beklenti} | {ev.onceki} |"
        )
    return "\n".join(lines)


def _render_tefas_table(funds: List[TefasTopFund]) -> str:
    if not funds:
        return "_Veri bulunamadı._"
    lines = [
        "| Sıra | Kod | Fon Adı | Kapsamı / Şemsiye Türü | Günlük | 1 Hafta | 1 Ay | YTD (Yılbaşı) | 1 Yıl |",
        "|:---:|:---:|:---|:---|---:|---:|---:|---:|---:|",
    ]
    for f in funds:
        lines.append(
            f"| {f.sira} | **{f.kod}** | {f.ad} | *{f.kapsam_turu}* | "
            f"**{_fmt_pct_short(f.getiri_1g)}** | **{_fmt_pct_short(f.getiri_1h)}** | "
            f"**{_fmt_pct_short(f.getiri_1a)}** | **{_fmt_pct_short(f.getiri_ytd)}** | "
            f"**{_fmt_pct_short(f.getiri_1y)}** |"
        )
    return "\n".join(lines)


def generate_markdown_report(
    report: DailyFinanceReport,
    bulten_adi: str,
    speaker_text: str,
) -> str:
    """Tüm çoklu dönem performansları, teknik analiz, TEFAS liderleri ve takvimleri içeren Markdown üretir."""
    md: List[str] = []

    md.append(f"# 📊 {bulten_adi} — {report.tarih}")
    md.append(f"> **Oluşturulma Zamanı:** `{report.olusturulma_zamani}`  ")
    md.append(
        "> **Kapsam:** BIST (TL & USD Teknik Analiz) • S&P 500 & Küresel Endeksler • Altın, Gümüş & Rasyo • "
        "Fear & Greed (S&P 500, Altın, Kripto) • TEFAS Dönemsel Şampiyonlar • Kripto & BTC Dominance • "
        "Tahvil, CDS & Döviz • Petrol & Emtia • 2 Haftalık Ekonomik Takvim • Otorite ve Sektör Haberleri\n"
    )

    # 1. BIST Endeksleri (TL) & Dolar Bazlı BIST 100 Performans + Teknik Analiz
    md.append("## 1. 🇹🇷 BIST 100 ve Borsa İstanbul Endeksleri (TL ve Dolar Bazlı Analiz)")
    md.append("### 1.1. TL Bazlı BIST Endeksleri (Günlük, 1H, 1A, 3A, YTD ve 1Y)")
    md.append(_render_multi_period_table(report.bist_endeksleri))
    md.append("")

    bt = report.bist100_dolar_teknik
    md.append("### 1.2. 💵 Dolar (USD) Bazlı BIST 100 Performansı (`XU100 / USDTRY`)")
    md.append(
        "| Gösterge | Güncel USD | Günlük (1G) | 1 Hafta (1H) | 1 Ay (1A) | 3 Ay (3A) | Yılbaşı (YTD) | 1 Yıl (1Y) |"
    )
    md.append("|:---|---:|:---|:---|:---|:---|:---|:---|")
    md.append(
        f"| **BIST 100 (USD Bazlı)** | **{_fmt_num(bt.guncel_usd, 'USD')}** | "
        f"{_fmt_pct_with_trend(bt.degisim_1g_usd, 0.10)} | "
        f"{_fmt_pct_with_trend(bt.degisim_1h_usd, 0.25)} | "
        f"{_fmt_pct_with_trend(bt.degisim_1a_usd, 0.50)} | "
        f"{_fmt_pct_with_trend(bt.degisim_3a_usd, 0.75)} | "
        f"{_fmt_pct_with_trend(bt.degisim_ytd_usd, 0.75)} | "
        f"{_fmt_pct_with_trend(bt.degisim_1y_usd, 1.00)} |"
    )
    md.append("")

    md.append("### 1.3. 📐 BIST 100 Dolar Bazlı Taban (Dip) ve Tavan (Zirve) Teknik Analizi")
    md.append(
        "| Teknik Analiz Yöntemi | Referans Seviye (USD) | Tarih / Detay | Güncel Fiyata Uzaklık / Durum |"
    )
    md.append("|:---|---:|:---|:---|")
    md.append(
        f"| **52 Haftalık (1 Yıl) Dolar Tavanı (Zirve)** | **{_fmt_num(bt.tavan_52h_usd, 'USD')}** | `{bt.tavan_52h_tarih}` | "
        f"🔴 Zirveden **{_fmt_pct_short(bt.tavana_uzaklik_52h_yuzde)}** aşağıda |"
    )
    md.append(
        f"| **52 Haftalık (1 Yıl) Dolar Tabanı (Dip)** | **{_fmt_num(bt.taban_52h_usd, 'USD')}** | `{bt.taban_52h_tarih}` | "
        f"🟢 Dipten **{_fmt_pct_short(bt.tabana_uzaklik_52h_yuzde)}** yukarıda (Kanal Konumu: **%{bt.kanal_konumu_52h_yuzde}**) |"
    )
    md.append(
        f"| **Son 3 Aylık Dolar Tavanı / Tabanı** | **{_fmt_num(bt.tavan_3a_usd, '$')} / {_fmt_num(bt.taban_3a_usd, '$')}** | 63 İş Günü | "
        f"Tavana: **{_fmt_pct_short(bt.tavana_uzaklik_3a_yuzde)}** / Tabana: **{_fmt_pct_short(bt.tabana_uzaklik_3a_yuzde)}** |"
    )
    md.append(
        f"| **Son Yerel Swing Tavan (Pivot Direnç)** | **{_fmt_num(bt.son_swing_tavan_usd, 'USD')}** | `{bt.son_swing_tavan_tarih}` | "
        f"Son yerel tepeden **{_fmt_pct_short(bt.swing_tavana_uzaklik_yuzde)}** uzaklıkta |"
    )
    md.append(
        f"| **Son Yerel Swing Taban (Pivot Destek)** | **{_fmt_num(bt.son_swing_taban_usd, 'USD')}** | `{bt.son_swing_taban_tarih}` | "
        f"Son yerel dipten **{_fmt_pct_short(bt.swing_tabana_uzaklik_yuzde)}** yukarıda |"
    )
    md.append(
        f"| **Fibonacci Düzeltme Seviyeleri (1Y)** | `%61.8:` **{_fmt_num(bt.fib_618_usd, '$')}** | `%50:` **{_fmt_num(bt.fib_500_usd, '$')}** | "
        f"`%38.2:` **{_fmt_num(bt.fib_382_usd, '$')}** • `%23.6:` **{_fmt_num(bt.fib_236_usd, '$')}** |"
    )
    md.append(
        f"| **Hareketli Ortalamalar & RSI (USD)** | `MA50:` **{_fmt_num(bt.ma50_usd, '$')}** | `MA200:` **{_fmt_num(bt.ma200_usd, '$')}** | "
        f"`RSI(14):` **{bt.rsi14_usd}** |"
    )
    if bt.teknik_ozet_yorum:
        md.append(f"\n> **💡 Teknik Analiz Özeti:** {bt.teknik_ozet_yorum}\n")

    # 2. S&P 500 ve Küresel Endeksler
    md.append("## 2. 🌎 S&P 500 ve ABD / Küresel Endeksler (Çoklu Dönem)")
    md.append(_render_multi_period_table(report.abd_ve_kuresel_endeksler))
    md.append("")

    # 3. Altın, Gümüş ve Altın/Gümüş Oranı
    md.append("## 3. 🪙 Altın, Gümüş (Döviz Çoklu Dönem + Günlük TL) ve Altın/Gümüş Oranı")
    md.append("### 3.1. Döviz (USD / Ons) Bazlı Altın ve Gümüş Performansı")
    md.append(_render_multi_period_table(report.altin_ve_gumus_usd))
    md.append("")

    gs = report.altin_gumus_ozet
    md.append("### 3.2. TL Bazlı Günlük Değerler ve Altın / Gümüş Rasyosu (`XAU/XAG`)")
    md.append(
        "| Gösterge | Güncel Değer | Günlük (1G) | 1 Hafta (1H) | 1 Ay (1A) | Yılbaşı (YTD) | 1 Yıl (1Y) | Not |"
    )
    md.append("|:---|---:|:---|:---|:---|:---|:---|:---|")
    md.append(
        f"| **Gram Altın (TL - Sadece Günlük)** | **{_fmt_num(gs.gram_altin_tl, 'TL')}** | "
        f"{_fmt_pct_with_trend(gs.gram_altin_degisim_1g, 0.10)} | - | - | - | - | Ons × USD/TRY |"
    )
    md.append(
        f"| **Gram Gümüş (TL - Sadece Günlük)** | **{_fmt_num(gs.gram_gumus_tl, 'TL')}** | "
        f"{_fmt_pct_with_trend(gs.gram_gumus_degisim_1g, 0.10)} | - | - | - | - | Ons × USD/TRY |"
    )
    md.append(
        f"| **Altın / Gümüş Oranı (XAU/XAG)** | **{_fmt_num(gs.altin_gumus_rasyosu, 'kat')}** | "
        f"{_fmt_pct_with_trend(gs.rasyo_degisim_1g, 0.10)} | "
        f"{_fmt_pct_with_trend(gs.rasyo_degisim_1h, 0.25)} | "
        f"{_fmt_pct_with_trend(gs.rasyo_degisim_1a, 0.50)} | "
        f"{_fmt_pct_with_trend(gs.rasyo_degisim_ytd, 0.75)} | "
        f"{_fmt_pct_with_trend(gs.rasyo_degisim_1y, 1.00)} | 1 Ons Altın = {gs.altin_gumus_rasyosu} Ons Gümüş |"
    )
    if gs.rasyo_yorum:
        md.append(f"\n> **💡 Rasyo Notu:** {gs.rasyo_yorum}\n")

    # 4. Korku ve Açgözlülük Endeksleri (S&P 500, Altın, Kripto)
    md.append("## 4. 🧭 Korku ve Açgözlülük Endeksleri (S&P 500 • Altın • Kripto)")
    md.append("| Piyasa | Güncel Skor (0-100) | Duyarlılık Bölgesi | Önceki Gün | Geçen Hafta | Geçen Ay | Açıklama |")
    md.append("|:---|:---:|:---|:---:|:---:|:---:|:---|")
    for fg in report.korku_acgozluluk_endeksleri:
        md.append(
            f"| **{fg.piyasa}** | **{fg.skor} / 100** | **{fg.durum_tr}** | "
            f"{fg.onceki_gun or '-'} | {fg.onceki_hafta or '-'} | {fg.onceki_ay or '-'} | {fg.aciklama} |"
        )
    md.append("")

    # 5. TEFAS Fonlarında Dönemsel En Çok Kazandıranlar
    md.append("## 5. 🏆 TEFAS Fonları: Dönemsel En Çok Kazandıranlar ve Kapsamları")
    period_titles = [
        ("gunluk", "5.1. Son 1 Günde En Çok Kazandıran TEFAS Fonları"),
        ("haftalik", "5.2. Son 1 Haftada En Çok Kazandıran TEFAS Fonları"),
        ("aylik", "5.3. Son 1 Ayda En Çok Kazandıran TEFAS Fonları"),
        ("ytd", "5.4. Yılbaşından İtibaren (YTD) En Çok Kazandıran TEFAS Fonları"),
        ("yillik", "5.5. Son 1 Yılda En Çok Kazandıran TEFAS Fonları"),
    ]
    for p_key, p_title in period_titles:
        md.append(f"### {p_title}")
        md.append(_render_tefas_table(report.tefas_donemsel_liderler.get(p_key, [])))
        md.append("")

    if report.takip_edilen_fonlar:
        md.append("### 5.6. Özel Takip Listenizdeki TEFAS Fonları")
        md.append(_render_tefas_table(report.takip_edilen_fonlar))
        md.append("")

    # 6. Kripto Piyasası (BTC, ETH, XRP, Total Market Cap, BTC Dominance)
    md.append("## 6. ₿ Kripto Varlıklar (`BTC`, `ETH`, `XRP`), Toplam Piyasa Değeri ve BTC Dominance")
    cp = report.kripto_piyasa_ozeti
    md.append(
        f"- **Küresel Kripto Toplam Piyasa Değeri (Total Market Cap):** **${cp.total_mcap_trilyon_usd or '-'} Trilyon USD** "
        f"(Günlük: **{_fmt_pct_short(cp.total_mcap_degisim_1g)}** • Haftalık: **{_fmt_pct_short(cp.total_mcap_degisim_1h)}** • "
        f"Aylık: **{_fmt_pct_short(cp.total_mcap_degisim_1a)}** • YTD: **{_fmt_pct_short(cp.total_mcap_degisim_ytd)}** • "
        f"1 Yıllık: **{_fmt_pct_short(cp.total_mcap_degisim_1y)}**)"
    )
    md.append(
        f"- **Bitcoin Dominance (`BTC.D`):** **%{cp.btc_dominance_yuzde or '-'}** "
        f"(Ethereum Payı: **%{cp.eth_dominance_yuzde or '-'}**)\n"
    )
    md.append(_render_multi_period_table(report.kripto_varliklar))
    md.append("")

    # 7. ABD & TR Tahvilleri, CDS, Dolar, Euro ve DXY
    md.append("## 7. 🏛️ ABD & Türkiye Tahvilleri, CDS Risk Primi, Euro ve Dolar Fiyatları")
    md.append("### 7.1. Döviz Kurları, EUR/USD Paritesi ve Küresel Dolar Endeksi (`DXY`)")
    md.append(_render_multi_period_table(report.doviz_ve_dxy))
    md.append("")
    md.append("### 7.2. ABD Hazine Tahvilleri, Türkiye Gösterge Tahvilleri ve 5Y CDS")
    md.append(_render_multi_period_table(report.tahvil_ve_cds))
    md.append("")

    # 8. Petrol ve Emtia Grupları
    md.append("## 8. 🛢️ Petrol ve Küresel Emtia Grupları (Enerji • Sanayi Metalleri • Tarım)")
    md.append(_render_multi_period_table(report.petrol_ve_emtia))
    md.append("")

    # 9. Ekonomik Takvim (Bugün, Bu Hafta ve Gelecek Hafta)
    md.append("## 9. 🗓️ Ekonomik Takvim (ABD ve Türkiye — Bugün, Bu Hafta ve Gelecek Hafta)")
    md.append("### 9.1. 📌 Bugün Açıklanan / Takip Edilen Önemli Veriler")
    md.append(_render_calendar_table(report.ekonomik_takvim_bugun))
    md.append("")
    md.append("### 9.2. 📅 Bu Haftanın Kalanında Açıklanacak Önemli Veriler")
    md.append(_render_calendar_table(report.ekonomik_takvim_bu_hafta))
    md.append("")
    md.append("### 9.3. 🔭 Gelecek Hafta Açıklanacak Kritik Veriler (Ön Haber)")
    md.append(_render_calendar_table(report.ekonomik_takvim_gelecek_hafta))
    md.append("")

    # 10. Otorite/Banka Açıklamaları ve Konut/Araç İstatistikleri
    md.append("## 10. 🏦 Finans Otoriteleri ve Bankaların Açıklamaları (Başlıklar)")
    for idx, h in enumerate(report.otorite_ve_banka_haberleri, start=1):
        etiket_s = " ".join(f"`#{t}`" for t in h.etiketler) if h.etiketler else ""
        md.append(f"{idx}. **{h.baslik}** — *({h.kaynak})* {etiket_s}")
    md.append("")

    md.append("## 11. 🏠🚗 Türkiye Konut (TÜİK) ve Araç (ODMD) Satış İstatistikleri")
    for h in report.konut_ve_arac_istatistikleri:
        ikon = "🏠 **Konut:**" if h.kategori == "konut" else "🚗 **Otomotiv:**"
        md.append(f"- {ikon} {h.baslik} — *({h.kaynak})*")
    md.append("")

    md.append("---")
    md.append("## 🎙️ Haber Spikeri Metni (Sesli Okuma / TTS Önizlemesi)")
    md.append("```text")
    md.append(speaker_text)
    md.append("```")

    return "\n".join(md)
