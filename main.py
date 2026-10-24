import argparse
from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys


def load_dotenv_if_exists(base_dir: Path) -> None:
    """Yerel .env dosyası varsa ortam değişkenlerine yükler (ek kütüphane gerektirmez)."""
    env_path = base_dir / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v


from src.cloud.supabase_sync import SupabaseSyncClient
from src.collectors.calendar_collector import CalendarCollector
from src.collectors.market_collector import MarketCollector
from src.collectors.news_collector import NewsCollector
from src.collectors.tefas_collector import TefasCollector
from src.demo_data import create_demo_report
from src.generators.excel_gen import update_excel_workbook
from src.generators.markdown_gen import generate_markdown_report
from src.generators.speaker_gen import HybridSpeakerGenerator
from src.models import DailyFinanceReport
from src.tts.audio_engine import TTSAudioEngine


def load_config(config_path: Path) -> dict:
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def collect_live_report(cfg: dict, now: datetime) -> DailyFinanceReport:
    piyasa_cfg = cfg.get("piyasa_varliklari", {})
    fon_cfg = cfg.get("tefas_fonlari", [])
    haber_cfg = cfg.get("haber_filtreleri", {})
    rapor_cfg = cfg.get("rapor_ayarlari", {})

    market_col = MarketCollector(timeout=12)
    tefas_col = TefasCollector(timeout=15)
    cal_col = CalendarCollector(timeout=10)
    news_col = NewsCollector(timeout=10)

    print("[1/7] BIST (TL & Dolar Teknik Analiz), S&P 500, Altın, Gümüş, Tahvil, Döviz, Emtia ve Kripto 1 yıllık serileri çekiliyor...")
    bist_endeksleri = market_col.collect_multi_period_category(
        "bist", piyasa_cfg.get("bist_endeksleri", [])
    )
    bist100_dolar_teknik = market_col.compute_bist100_usd_technical()

    abd_endeksler = market_col.collect_multi_period_category(
        "abd_endeks", piyasa_cfg.get("abd_ve_kuresel_endeksler", [])
    )
    altin_gumus_usd = market_col.collect_multi_period_category(
        "altin_gumus_usd", piyasa_cfg.get("altin_ve_gumus_usd", [])
    )
    altin_gumus_ozet = market_col.compute_gold_silver_summary()

    doviz_ve_dxy = market_col.collect_multi_period_category(
        "doviz", piyasa_cfg.get("doviz_ve_dxy", [])
    )
    tahvil_ve_cds = market_col.collect_multi_period_category(
        "tahvil_cds", piyasa_cfg.get("tahvil_ve_cds", [])
    )
    petrol_ve_emtia = market_col.collect_multi_period_category(
        "emtia", piyasa_cfg.get("petrol_ve_emtia", [])
    )
    kripto_varliklar = market_col.collect_multi_period_category(
        "kripto", piyasa_cfg.get("kripto_varliklar", [])
    )

    print("[2/7] Kripto Toplam Piyasa Değeri (Total Market Cap) ve Bitcoin Dominance hesaplanıyor...")
    kripto_ozet = market_col.collect_crypto_global(kripto_varliklar)

    print("[3/7] S&P 500, Altın ve Kripto Korku & Açgözlülük (Fear & Greed) endeksleri hesaplanıyor...")
    fear_greed = market_col.collect_fear_and_greed_indices()

    print("[4/7] TEFAS fonları (Son Gün, Hafta, Ay, YTD ve 1 Yıl en çok kazandıranlar + kapsamları) çekiliyor...")
    top_n = rapor_cfg.get("tefas_lider_sayisi", 4)
    tefas_liderler, takip_fonlar = tefas_col.collect_top_and_watchlist_funds(fon_cfg, top_n=top_n)

    print("[5/7] ABD ve Türkiye Ekonomik Takvimi (Bugün, Bu Hafta ve Gelecek Hafta) çekiliyor...")
    cal_today, cal_this_w, cal_next_w = cal_col.collect_all_calendar_horizons(now)

    print("[6/7] Finans otoriteleri ve banka açıklamaları (başlıklar) taranıyor...")
    keywords = haber_cfg.get("otorite_ve_banka_anahtar_kelimeler", [])
    max_news = rapor_cfg.get("maksimum_haber_basligi", 10)
    otorite_haberleri = news_col.collect_authority_and_bank_headlines(keywords, max_headlines=max_news)

    print("[7/7] Türkiye konut (TÜİK) ve araç (ODMD) satış istatistikleri taranıyor...")
    konut_arac = news_col.collect_housing_and_auto_stats(max_per_topic=2)

    return DailyFinanceReport(
        tarih=now.strftime("%Y-%m-%d"),
        olusturulma_zamani=now.strftime("%Y-%m-%d %H:%M:%S"),
        bist_endeksleri=bist_endeksleri,
        bist100_dolar_teknik=bist100_dolar_teknik,
        abd_ve_kuresel_endeksler=abd_endeksler,
        altin_ve_gumus_usd=altin_gumus_usd,
        altin_gumus_ozet=altin_gumus_ozet,
        korku_acgozluluk_endeksleri=fear_greed,
        tefas_donemsel_liderler=tefas_liderler,
        takip_edilen_fonlar=takip_fonlar,
        kripto_varliklar=kripto_varliklar,
        kripto_piyasa_ozeti=kripto_ozet,
        tahvil_ve_cds=tahvil_ve_cds,
        doviz_ve_dxy=doviz_ve_dxy,
        petrol_ve_emtia=petrol_ve_emtia,
        ekonomik_takvim_bugun=cal_today,
        ekonomik_takvim_bu_hafta=cal_this_w,
        ekonomik_takvim_gelecek_hafta=cal_next_w,
        otorite_ve_banka_haberleri=otorite_haberleri,
        konut_ve_arac_istatistikleri=konut_arac,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Günlük Küresel ve Yerel Finans Bülteni (Excel, Supabase, Web Dashboard ve TTS)"
    )
    parser.add_argument("--config", type=str, default="config.json", help="Yapılandırma dosyası yolu")
    parser.add_argument("--demo", action="store_true", help="Örnek verilerle tüm çıktıları, Excel'i ve Web Dashboard'u üretir")
    parser.add_argument("--ai", action="store_true", help="Gemini API ile spiker metni cilalamayı aktif eder")
    parser.add_argument("--tts", action="store_true", help="Üretilen TTS metnini MP3 ses dosyasına dönüştürür")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    load_dotenv_if_exists(base_dir)
    config_path = base_dir / args.config
    if not config_path.exists():
        print(f"HATA: Yapılandırma dosyası bulunamadı: {config_path}", file=sys.stderr)
        return 1

    cfg = load_config(config_path)
    now = datetime.now()

    if args.demo:
        print("Bilgi: --demo modu seçildi, zengin örnek verilerle rapor, Excel ve Web Dashboard oluşturuluyor...")
        report = create_demo_report(now)
    else:
        report = collect_live_report(cfg, now)
        all_prices = [
            a.fiyat
            for a in (report.bist_endeksleri + report.abd_ve_kuresel_endeksler + report.kripto_varliklar)
            if a.fiyat is not None
        ]
        if not all_prices:
            print(
                "UYARI: Canlı piyasa verilerine erişilemedi (ağ kısıtlaması olabilir). "
                "Tabloların boş kalmaması için örnek verilerle devam etmek isterseniz 'python main.py --demo' çalıştırabilirsiniz."
            )

    ai_cfg = dict(cfg.get("ai_ayarlari", {}))
    if args.ai:
        ai_cfg["aktif"] = True

    speaker_gen = HybridSpeakerGenerator(ai_config=ai_cfg)
    segments, human_speaker_text, tts_ready_text = speaker_gen.build_speaker_outputs(report)

    rapor_cfg = cfg.get("rapor_ayarlari", {})
    bulten_adi = rapor_cfg.get("bulten_adi", "Günlük Küresel ve Yerel Finans Bülteni")
    md_content = generate_markdown_report(report, bulten_adi, human_speaker_text)

    # 1. Günlük Klasör Çıktıları (raporlar/YYYY-MM-DD/)
    out_root = base_dir / rapor_cfg.get("cikti_klasoru", "raporlar")
    day_dir = out_root / report.tarih
    day_dir.mkdir(parents=True, exist_ok=True)

    md_path = day_dir / f"{report.tarih}_finans_raporu.md"
    speaker_txt_path = day_dir / f"{report.tarih}_spiker_metni.txt"
    tts_txt_path = day_dir / f"{report.tarih}_tts_okunus.txt"
    json_path = day_dir / f"{report.tarih}_veri_ve_tts.json"
    daily_excel_path = day_dir / f"{report.tarih}_finans_tablosu.xlsx"
    master_excel_path = out_root / rapor_cfg.get("excel_dosya_adi", "Finans_Veri_Tabani.xlsx")

    md_path.write_text(md_content, encoding="utf-8")
    speaker_txt_path.write_text(human_speaker_text, encoding="utf-8")
    tts_txt_path.write_text(tts_ready_text, encoding="utf-8")

    toplam_sure = sum(s.tahmini_sure_saniye for s in segments)
    json_payload = {
        "meta": {
            "bulten_adi": bulten_adi,
            "tarih": report.tarih,
            "olusturulma_zamani": report.olusturulma_zamani,
            "tahmini_okuma_suresi_saniye": toplam_sure,
            "tahmini_okuma_suresi_dakika": round(toplam_sure / 60.0, 1),
        },
        "spiker_metni": human_speaker_text,
        "tts_bolumleri": [asdict(s) for s in segments],
        "tts_tam_metin": tts_ready_text,
        "ham_veriler": report.to_dict(),
    }
    json_str = json.dumps(json_payload, ensure_ascii=False, indent=2)
    json_path.write_text(json_str, encoding="utf-8")

    # 2. Excel Veri Tabanını ve Günlük Excel Dosyasını Güncelle
    update_excel_workbook(report, master_excel_path=master_excel_path, daily_excel_path=daily_excel_path)

    # 3. GitHub Pages / Her Yerden Erişim Web Dashboard Dosyalarını Güncelle (docs/)
    docs_dir = base_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    docs_json_path = docs_dir / "latest_report.json"
    docs_js_path = docs_dir / "latest_report_data.js"
    docs_excel_path = docs_dir / master_excel_path.name

    docs_json_path.write_text(json_str, encoding="utf-8")
    docs_js_path.write_text(f"window.LATEST_FINANCE_REPORT = {json_str};\n", encoding="utf-8")
    shutil.copy2(master_excel_path, docs_excel_path)

    # 4. Supabase Bulut Senkronizasyonu
    supa_cfg = cfg.get("supabase_ayarlari", {})
    supa_client = SupabaseSyncClient(supa_cfg)
    supa_ok, supa_msg = supa_client.sync_daily_report(
        report=report,
        md_content=md_content,
        speaker_text=human_speaker_text,
        tts_text=tts_ready_text,
        full_json_payload=json_payload,
        excel_path=master_excel_path,
    )

    print("\n======================================================================")
    print(f"GÜNLÜK FİNANS RAPORU, EXCEL VE WEB DASHBOARD HAZIR ({report.tarih})")
    print("======================================================================")
    print(f"1. Kümülatif Excel Tablosu : {master_excel_path}")
    print(f"2. Günlük Excel Tablosu    : {daily_excel_path}")
    print(f"3. Görsel Rapor (Markdown) : {md_path}")
    print(f"4. Haber Spikeri Metni     : {speaker_txt_path}")
    print(f"5. TTS Seslendirme Metni   : {tts_txt_path}")
    print(f"6. Web Dashboard (HTML)    : {docs_dir / 'index.html'}")
    print(f"7. Supabase Bulut Durumu   : {supa_msg}")
    print(f"   Tahmini Sesli Süre      : ~{toplam_sure} saniye (~{round(toplam_sure / 60.0, 1)} dk)")

    tts_cfg = dict(cfg.get("tts_ayarlari", {}))
    if args.tts or tts_cfg.get("aktif", False):
        mp3_path = day_dir / f"{report.tarih}_sesli_bulten.mp3"
        engine = TTSAudioEngine(tts_cfg)
        ok, msg = engine.synthesize_to_mp3(tts_txt_path, mp3_path)
        print(f"8. Sesli Okuma (TTS MP3)   : {msg}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
