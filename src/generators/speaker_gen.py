import os
from typing import Dict, List, Optional, Tuple
import requests
from src.models import DailyFinanceReport, MultiPeriodAsset, TTSSegment, classify_trend
from src.generators.tts_normalizer import format_number_for_speech, normalize_text_for_tts


class HybridSpeakerGenerator:
    """
    Gelişmiş (V2) Hibrit Haber Spikeri Metin Üreticisi:
    Çoklu dönem performanslarını, BIST 100 Dolar bazlı taban/tavan teknik analizini,
    Altın/Gümüş rasyosunu, Fear & Greed endekslerini, TEFAS dönemsel şampiyonlarını
    ve 2 haftalık ekonomik takvimi doğal bir radyo/podcast bültenine dönüştürür.
    """

    def __init__(self, ai_config: Optional[Dict] = None):
        self.ai_config = ai_config or {}

    @staticmethod
    def _estimate_seconds(text: str) -> int:
        words = len(text.split())
        return max(3, int(round((words / 135.0) * 60)))

    @staticmethod
    def _multi_period_sentence(a: MultiPeriodAsset, include_long: bool = True) -> Optional[str]:
        if a.fiyat is None:
            return None
        f_s = format_number_for_speech(a.fiyat, 2)
        g1 = format_number_for_speech(abs(a.degisim_1g or 0), 2)
        yon1 = "artışla" if (a.degisim_1g or 0) > 0.1 else ("düşüşle" if (a.degisim_1g or 0) < -0.1 else "yatay seyirle")
        base = f"{a.okunus}, günü yüzde {g1} {yon1} {f_s} {a.birim} seviyesinde tamamladı."
        if include_long and a.degisim_1h is not None and a.degisim_ytd is not None and a.degisim_1y is not None:
            yon_1a = classify_trend(a.degisim_1a, 0.5).lower()
            yon_ytd = classify_trend(a.degisim_ytd, 0.75).lower()
            h_s = format_number_for_speech(abs(a.degisim_1h), 2)
            a_s = format_number_for_speech(abs(a.degisim_1a or 0), 2)
            ytd_s = format_number_for_speech(abs(a.degisim_ytd), 2)
            y1_s = format_number_for_speech(abs(a.degisim_1y), 2)
            base += (
                f" Haftalık bazda yüzde {h_s}, aylıkta yüzde {a_s} ({yon_1a}), "
                f"yılbaşından itibaren yüzde {ytd_s} ({yon_ytd}) ve son bir yılda yüzde {y1_s} değişim kaydetti."
            )
        return base

    def generate_template_segments(self, report: DailyFinanceReport) -> List[TTSSegment]:
        segments: List[TTSSegment] = []

        # 1. AÇILIŞ
        giris = (
            f"İyi günler. {report.tarih} tarihli Günlük Küresel ve Yerel Finans Bültenine hoş geldiniz. "
            f"Bugün Borsa İstanbul'un TL ve Dolar bazlı teknik görünümünü, Es end Pi 500, altın, gümüş, "
            f"TEFAS şampiyon fonları, kripto piyasasını ve iki haftalık ekonomik takvimi aktarıyoruz."
        )
        segments.append(
            TTSSegment("01_giris", "Açılış", giris, normalize_text_for_tts(giris), self._estimate_seconds(giris))
        )

        # 2. BIST 100 (TL VE DOLAR BAZLI TEKNİK ANALİZ)
        bist_c = ["Borsa İstanbul ile başlıyoruz."]
        for a in report.bist_endeksleri:
            s = self._multi_period_sentence(a, include_long=(a.kod == "XU100.IS"))
            if s:
                bist_c.append(s)

        bt = report.bist100_dolar_teknik
        if bt.guncel_usd is not None:
            usd_f = format_number_for_speech(bt.guncel_usd, 2)
            tavan_f = format_number_for_speech(bt.tavan_52h_usd or 0, 2)
            taban_f = format_number_for_speech(bt.taban_52h_usd or 0, 2)
            uz_tavan = format_number_for_speech(abs(bt.tavana_uzaklik_52h_yuzde or 0), 1)
            uz_taban = format_number_for_speech(abs(bt.tabana_uzaklik_52h_yuzde or 0), 1)
            bist_c.append(
                f"Dolar bazında Borsa İstanbul yüz endeksi {usd_f} dolar seviyesindedir. "
                f"Teknik analizde son bir yılın dolar zirvesi olan {tavan_f} dolardan yüzde {uz_tavan} aşağıda, "
                f"bir yıllık dolar tabanı olan {taban_f} dolardan ise yüzde {uz_taban} yukarıda işlem görüyor. "
                f"İki yüz günlük dolar ortalaması {format_number_for_speech(bt.ma200_usd or 0, 2)} dolar, "
                f"Ar Es Ay göstergesi ise {format_number_for_speech(bt.rsi14_usd or 50, 1)} seviyesindedir."
            )
        bist_ham = " ".join(bist_c)
        segments.append(
            TTSSegment(
                "02_bist_ve_teknik",
                "BIST 100 TL ve Dolar Bazlı Teknik Analiz",
                bist_ham,
                normalize_text_for_tts(bist_ham),
                self._estimate_seconds(bist_ham),
            )
        )

        # 3. S&P 500, ALTIN, GÜMÜŞ VE FEAR & GREED ENDEKSLERİ
        küresel_c = ["Küresel endeksler ve kıymetli madenler cephesine geçiyoruz."]
        for a in report.abd_ve_kuresel_endeksler[:2]:
            s = self._multi_period_sentence(a, include_long=(a.kod == "^GSPC"))
            if s:
                küresel_c.append(s)

        for a in report.altin_ve_gumus_usd:
            s = self._multi_period_sentence(a, include_long=True)
            if s:
                küresel_c.append(s)

        gs = report.altin_gumus_ozet
        if gs.gram_altin_tl:
            küresel_c.append(
                f"Türk Lirası bazında günlük fiyatlarda Gram Altın {format_number_for_speech(gs.gram_altin_tl, 2)} Türk Lirası, "
                f"Gram Gümüş ise {format_number_for_speech(gs.gram_gumus_tl or 0, 2)} Türk Lirası seviyesindedir. "
                f"Altın Gümüş oranı ise {format_number_for_speech(gs.altin_gumus_rasyosu or 0, 2)} düzeyindedir."
            )

        if report.korku_acgozluluk_endeksleri:
            fg_parts = [f"{fg.piyasa} için {fg.skor} puan ile {fg.durum_tr}" for fg in report.korku_acgozluluk_endeksleri]
            küresel_c.append("Korku ve Açgözlülük endeksleri; " + ", ".join(fg_parts) + " bölgesine işaret ediyor.")

        kuresel_ham = " ".join(küresel_c)
        segments.append(
            TTSSegment(
                "03_sp500_altin_duyarlilik",
                "S&P 500, Altın, Gümüş ve Korku/Açgözlülük Endeksleri",
                kuresel_ham,
                normalize_text_for_tts(kuresel_ham),
                self._estimate_seconds(kuresel_ham),
            )
        )

        # 4. TEFAS DÖNEMSEL ŞAMPİYON FONLAR
        tefas_c = ["TEFAS yatırım fonlarında dönemsel bazda en çok kazandıran fonlar şöyle:"]
        for p_key, p_label in [
            ("gunluk", "Son bir günde"),
            ("haftalik", "Son bir haftada"),
            ("aylik", "Son bir ayda"),
            ("ytd", "Yılbaşından itibaren"),
            ("yillik", "Son bir yılda"),
        ]:
            top_list = report.tefas_donemsel_liderler.get(p_key, [])
            if top_list:
                f = top_list[0]
                oran = format_number_for_speech(f.ilgili_donem_getiri_yuzde, 2)
                tefas_c.append(
                    f"{p_label} lider fon, {f.kapsam_turu} içinden yüzde {oran} getiri ile {f.ad} ({f.kod}) oldu."
                )
        tefas_ham = " ".join(tefas_c)
        segments.append(
            TTSSegment(
                "04_tefas_liderler",
                "TEFAS Dönemsel En Çok Kazandıran Fonlar",
                tefas_ham,
                normalize_text_for_tts(tefas_ham),
                self._estimate_seconds(tefas_ham),
            )
        )

        # 5. KRİPTO PİYASASI, TAHVİL, DÖVİZ VE EMTİA
        kripto_emtia_c = []
        cp = report.kripto_piyasa_ozeti
        if cp.total_mcap_trilyon_usd:
            kripto_emtia_c.append(
                f"Kripto para piyasasının toplam büyüklüğü {format_number_for_speech(cp.total_mcap_trilyon_usd, 2)} trilyon dolar, "
                f"Bitkoin dominansı ise yüzde {format_number_for_speech(cp.btc_dominance_yuzde or 0, 2)} seviyesinde."
            )
        for k in report.kripto_varliklar:
            s = self._multi_period_sentence(k, include_long=(k.kod == "BTC-USD"))
            if s:
                kripto_emtia_c.append(s)

        for d in report.doviz_ve_dxy:
            s = self._multi_period_sentence(d, include_long=False)
            if s:
                kripto_emtia_c.append(s)

        for t in report.tahvil_ve_cds:
            s = self._multi_period_sentence(t, include_long=False)
            if s:
                kripto_emtia_c.append(s)

        for e in report.petrol_ve_emtia[:4]:
            s = self._multi_period_sentence(e, include_long=False)
            if s:
                kripto_emtia_c.append(s)

        ke_ham = " ".join(kripto_emtia_c)
        segments.append(
            TTSSegment(
                "05_kripto_tahvil_emtia",
                "Kripto, Tahvil, Döviz ve Emtia Piyasaları",
                ke_ham,
                normalize_text_for_tts(ke_ham),
                self._estimate_seconds(ke_ham),
            )
        )

        # 6. EKONOMİK TAKVİM (BUGÜN, BU HAFTA VE GELECEK HAFTA)
        takvim_c = ["ABD ve Türkiye ekonomik takviminde öne çıkan başlıklar:"]
        for ev in report.ekonomik_takvim_bugun[:4]:
            takvim_c.append(f"Bugün {ev.ulke} tarafında {ev.baslik} takip edildi; açıklanan veri {ev.gerceklesen}, beklenti {ev.beklenti}.")
        if report.ekonomik_takvim_bu_hafta:
            bu_h_basliklar = ", ".join(f"{e.ulke} {e.baslik}" for e in report.ekonomik_takvim_bu_hafta[:3])
            takvim_c.append(f"Bu haftanın kalanında {bu_h_basliklar} verileri izlenecek.")
        if report.ekonomik_takvim_gelecek_hafta:
            gel_h_basliklar = ", ".join(f"{e.tarih} tarihinde {e.ulke} {e.baslik}" for e in report.ekonomik_takvim_gelecek_hafta[:4])
            takvim_c.append(f"Gelecek haftanın kritik gündeminde ise {gel_h_basliklar} yer alıyor.")

        takvim_ham = " ".join(takvim_c)
        segments.append(
            TTSSegment(
                "06_ekonomik_takvim",
                "Ekonomik Takvim (Bugün, Bu Hafta ve Gelecek Hafta)",
                takvim_ham,
                normalize_text_for_tts(takvim_ham),
                self._estimate_seconds(takvim_ham),
            )
        )

        # 7. OTORİTE/BANKA AÇIKLAMALARI VE KONUT/ARAÇ İSTATİSTİKLERİ
        haber_c = ["Finans otoriteleri, bankalar ve reel sektör istatistiklerinden son başlıklar:"]
        for h in report.otorite_ve_banka_haberleri[:5]:
            haber_c.append(f"{h.kaynak}: {h.baslik}.")
        for s in report.konut_ve_arac_istatistikleri[:4]:
            haber_c.append(f"{s.baslik}.")
        haber_c.append("Bültenimizin sonuna geldik. İyi ve kazançlı günler dileriz.")
        haber_ham = " ".join(haber_c)
        segments.append(
            TTSSegment(
                "07_haberler_ve_kapanis",
                "Otorite Açıklamaları, Konut/Araç İstatistikleri ve Kapanış",
                haber_ham,
                normalize_text_for_tts(haber_ham),
                self._estimate_seconds(haber_ham),
            )
        )

        return segments

    def try_generate_ai_bulletin(self, report: DailyFinanceReport, template_text: str) -> Optional[str]:
        if not self.ai_config.get("aktif", False):
            return None
        env_name = self.ai_config.get("api_key_env", "GEMINI_API_KEY")
        api_key = os.environ.get(env_name, "").strip()
        if not api_key:
            return None

        model = self.ai_config.get("model", "gemini-2.5-flash")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        prompt = (
            "Sen Bloomberg HT / CNBC-e ana haber spikerisin. Aşağıdaki günlük finans bülteni taslağını, "
            "sesli okumaya (TTS) %100 uygun, kısaltmaları açık okunan, akıcı bir radyo bülteni metnine dönüştür:\n\n"
            f"{template_text}"
        )
        try:
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=20)
            if resp.status_code == 200:
                candidates = resp.json().get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and parts[0].get("text"):
                        return parts[0]["text"].strip()
        except Exception:
            pass
        return None

    def build_speaker_outputs(self, report: DailyFinanceReport) -> Tuple[List[TTSSegment], str, str]:
        segments = self.generate_template_segments(report)
        raw_joined = "\n\n".join(f"[{seg.bolum_basligi.upper()}]\n{seg.ham_metin}" for seg in segments)
        ai_polished = self.try_generate_ai_bulletin(report, raw_joined)
        if ai_polished:
            full_human_text = ai_polished
            full_tts_text = normalize_text_for_tts(ai_polished)
        else:
            full_human_text = raw_joined
            full_tts_text = "\n\n".join(seg.tts_okunus_metni for seg in segments)
        return segments, full_human_text, full_tts_text
