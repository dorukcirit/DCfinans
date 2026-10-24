# 📊 Günlük Küresel ve Yerel Finans Bülteni (V2 — Excel, Supabase, GitHub Pages & TTS)

Her gün yurt içi ve küresel finansal verileri çoklu zaman dilimlerinde (`Günlük`, `1 Hafta`, `1 Ay`, `3 Ay`, `YTD`, `1 Yıl`) çeken, **BIST 100 Dolar bazlı taban/tavan teknik analizini** hesaplayan, **TEFAS dönemsel şampiyon fonlarını**, **S&P 500 / Altın / Kripto Fear & Greed endekslerini** ve **2 haftalık ABD/TR ekonomik takvimini** derleyerek **Excel (`.xlsx`)**, **Supabase**, **Web Dashboard** ve **Sesli Okuma (TTS)** formatlarında sunan sistem.

---

## 🌟 Neler Üretilir?

1. **Çok Sayfalı & Kümülatif Excel Veritabanı (`raporlar/Finans_Veri_Tabani.xlsx` & `docs/Finans_Veri_Tabani.xlsx`)**
   - `Gunluk_Arsiv_Log`: Her gün en alta yeni satır eklenen tarihsel veri günlüğü
   - `Coklu_Donem_Performans`: 1G, 1H, 1A, 3A, YTD, 1Y yüzdeleri ve renkli `Artış` / `Azalış` / `Yatay` etiketleri
   - `BIST100_Dolar_Teknik`: Dolar bazlı BIST 100 52H/3A Tavan-Taban, Swing Pivot, Fibonacci, MA50/MA200 ve RSI(14)
   - `TEFAS_En_Cok_Kazandiranlar`: Son 1 Gün, 1 Hafta, 1 Ay, YTD ve 1 Yıl en çok kazandıran fonlar ve kapsamları
   - `Ekonomik_Takvim_2Hafta`: ABD ve Türkiye için Bugün, Bu Hafta ve Gelecek Hafta verileri
   - `Duyarlilik_ve_Haberler`: S&P 500, Altın, Kripto Fear & Greed + Otorite/Banka + TÜİK Konut & ODMD Araç İstatistikleri
2. **Her Yerden Erişilebilir Web Dashboard (`docs/index.html`)**
   - Telefon ve bilgisayardan açılabilir, tek tıkla **🎙️ Sesli Bülten Okuma (TTS)** ve **📥 Excel İndirme** içerir.
3. **Supabase Bulut Senkronizasyonu (`supabase_schema.sql` & `src/cloud/supabase_sync.py`)**
4. **GitHub Actions Günlük Otomasyon (`.github/workflows/daily_finance_report.yml`)**

---

## 🚀 Çalıştırma Komutları

```powershell
# Canlı verilerle çalıştırma (Excel, Markdown, TTS ve Web Dashboard güncellenir)
python main.py

# Örnek/Demo verilerle tüm tabloları, Excel'i ve Web Dashboard'u test etme
python main.py --demo

# Ücretsiz Türkçe nöral ses ile MP3 üretme (pip install edge-tts sonrası)
python main.py --tts
```
