-- ============================================================================
-- GÜNLÜK FİNANS RAPORU VE SESLİ BÜLTEN SİSTEMİ - SUPABASE VERİTABANI ŞEMASI
-- Bu SQL kodunu Supabase Dashboard -> SQL Editor ekranına yapıştırıp çalıştırın.
-- ============================================================================

-- 1. Günlük Ana Bülten ve Özet Metrikler Tablosu
CREATE TABLE IF NOT EXISTS public.daily_finance_reports (
    report_date DATE PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    bist100_tl NUMERIC,
    bist100_1g_pct NUMERIC,
    bist100_usd NUMERIC,
    bist100_usd_52w_high_dist_pct NUMERIC,
    bist100_usd_52w_low_dist_pct NUMERIC,
    sp500 NUMERIC,
    sp500_1g_pct NUMERIC,
    ons_altin_usd NUMERIC,
    gram_altin_tl NUMERIC,
    ons_gumus_usd NUMERIC,
    altin_gumus_rasyosu NUMERIC,
    usdtry NUMERIC,
    eurtry NUMERIC,
    eurusd NUMERIC,
    dxy NUMERIC,
    abd_10y_tahvil NUMERIC,
    tr_2y_tahvil NUMERIC,
    tr_10y_tahvil NUMERIC,
    tr_5y_cds NUMERIC,
    btc_usd NUMERIC,
    eth_usd NUMERIC,
    xrp_usd NUMERIC,
    crypto_total_mcap_trillion NUMERIC,
    btc_dominance_pct NUMERIC,
    fg_sp500 INTEGER,
    fg_altin INTEGER,
    fg_kripto INTEGER,
    markdown_content TEXT,
    speaker_text TEXT,
    tts_text TEXT,
    full_payload JSONB NOT NULL
);

-- 2. Varlık Bazlı Çoklu Dönem Performans Arşivi Tablosu
CREATE TABLE IF NOT EXISTS public.asset_daily_metrics (
    report_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    asset_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price NUMERIC,
    unit TEXT,
    chg_1d NUMERIC,
    chg_1w NUMERIC,
    chg_1m NUMERIC,
    chg_3m NUMERIC,
    chg_ytd NUMERIC,
    chg_1y NUMERIC,
    PRIMARY KEY (report_date, symbol)
);

-- 3. Her yerden okuma (Web Dashboard) için RLS (Row Level Security) Okuma Politikası
ALTER TABLE public.daily_finance_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.asset_daily_metrics ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Herkes günlük raporları okuyabilir" ON public.daily_finance_reports;
CREATE POLICY "Herkes günlük raporları okuyabilir"
    ON public.daily_finance_reports FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Herkes varlık metriklerini okuyabilir" ON public.asset_daily_metrics;
CREATE POLICY "Herkes varlık metriklerini okuyabilir"
    ON public.asset_daily_metrics FOR SELECT
    USING (true);

-- 4. Excel ve Ses Dosyaları İçin Storage Bucket Oluşturma
INSERT INTO storage.buckets (id, name, public)
VALUES ('finans-raporlari', 'finans-raporlari', true)
ON CONFLICT (id) DO NOTHING;
