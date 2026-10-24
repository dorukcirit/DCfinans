import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from src.models import DailyFinanceReport, MultiPeriodAsset


class SupabaseSyncClient:
    """
    Günlük finans raporunu, çoklu dönem varlık performanslarını ve Excel (.xlsx) dosyasını
    Supabase PostgreSQL veritabanına ve Supabase Storage'a senkronize eder.
    """

    def __init__(self, supabase_cfg: Optional[Dict] = None):
        cfg = supabase_cfg or {}
        url_env = cfg.get("url_env", "SUPABASE_URL")
        key_env = cfg.get("key_env", "SUPABASE_SERVICE_ROLE_KEY")
        self.url = (os.environ.get(url_env) or os.environ.get("SUPABASE_URL") or "").rstrip("/")
        self.key = (
            os.environ.get(key_env)
            or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or os.environ.get("SUPABASE_KEY")
            or ""
        ).strip()
        self.bucket = cfg.get("bucket_adi", "finans-raporlari")

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.key)

    def _headers(self, content_type: str = "application/json") -> Dict[str, str]:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": content_type,
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }

    @staticmethod
    def _find_val(assets: List[MultiPeriodAsset], kod: str) -> Optional[float]:
        a = next((x for x in assets if x.kod == kod), None)
        return a.fiyat if a else None

    @staticmethod
    def _find_1g(assets: List[MultiPeriodAsset], kod: str) -> Optional[float]:
        a = next((x for x in assets if x.kod == kod), None)
        return a.degisim_1g if a else None

    def sync_daily_report(
        self,
        report: DailyFinanceReport,
        md_content: str,
        speaker_text: str,
        tts_text: str,
        full_json_payload: Dict[str, Any],
        excel_path: Optional[Path] = None,
    ) -> tuple[bool, str]:
        """
        Raporu Supabase `daily_finance_reports` ve `asset_daily_metrics` tablolarına yazar,
        ardından Excel dosyasını Supabase Storage'a yükler.
        """
        if not self.is_configured:
            return (
                False,
                "Supabase ortam değişkenleri (SUPABASE_URL ve SUPABASE_SERVICE_ROLE_KEY) tanımlı değil; yerel/GitHub modunda devam edildi.",
            )

        bt = report.bist100_dolar_teknik
        gs = report.altin_gumus_ozet
        cp = report.kripto_piyasa_ozeti

        fg_sp = next((x.skor for x in report.korku_acgozluluk_endeksleri if "S&P" in x.piyasa), None)
        fg_au = next((x.skor for x in report.korku_acgozluluk_endeksleri if "Altın" in x.piyasa), None)
        fg_cr = next((x.skor for x in report.korku_acgozluluk_endeksleri if "Kripto" in x.piyasa), None)

        row_main = {
            "report_date": report.tarih,
            "bist100_tl": self._find_val(report.bist_endeksleri, "XU100.IS"),
            "bist100_1g_pct": self._find_1g(report.bist_endeksleri, "XU100.IS"),
            "bist100_usd": bt.guncel_usd,
            "bist100_usd_52w_high_dist_pct": bt.tavana_uzaklik_52h_yuzde,
            "bist100_usd_52w_low_dist_pct": bt.tabana_uzaklik_52h_yuzde,
            "sp500": self._find_val(report.abd_ve_kuresel_endeksler, "^GSPC"),
            "sp500_1g_pct": self._find_1g(report.abd_ve_kuresel_endeksler, "^GSPC"),
            "ons_altin_usd": self._find_val(report.altin_ve_gumus_usd, "GC=F"),
            "gram_altin_tl": gs.gram_altin_tl,
            "ons_gumus_usd": self._find_val(report.altin_ve_gumus_usd, "SI=F"),
            "altin_gumus_rasyosu": gs.altin_gumus_rasyosu,
            "usdtry": self._find_val(report.doviz_ve_dxy, "USDTRY=X"),
            "eurtry": self._find_val(report.doviz_ve_dxy, "EURTRY=X"),
            "eurusd": self._find_val(report.doviz_ve_dxy, "EURUSD=X"),
            "dxy": self._find_val(report.doviz_ve_dxy, "DX-Y.NYB"),
            "abd_10y_tahvil": self._find_val(report.tahvil_ve_cds, "^TNX"),
            "tr_2y_tahvil": self._find_val(report.tahvil_ve_cds, "TR2Y"),
            "tr_10y_tahvil": self._find_val(report.tahvil_ve_cds, "TR10Y"),
            "tr_5y_cds": self._find_val(report.tahvil_ve_cds, "TR_CDS_5Y"),
            "btc_usd": self._find_val(report.kripto_varliklar, "BTC-USD"),
            "eth_usd": self._find_val(report.kripto_varliklar, "ETH-USD"),
            "xrp_usd": self._find_val(report.kripto_varliklar, "XRP-USD"),
            "crypto_total_mcap_trillion": cp.total_mcap_trilyon_usd,
            "btc_dominance_pct": cp.btc_dominance_yuzde,
            "fg_sp500": fg_sp,
            "fg_altin": fg_au,
            "fg_kripto": fg_cr,
            "markdown_content": md_content,
            "speaker_text": speaker_text,
            "tts_text": tts_text,
            "full_payload": full_json_payload,
        }

        messages: List[str] = []
        try:
            resp = requests.post(
                f"{self.url}/rest/v1/daily_finance_reports?on_conflict=report_date",
                headers=self._headers(),
                json=row_main,
                timeout=15,
            )
            if resp.status_code in (200, 201, 204):
                messages.append("daily_finance_reports tablosu güncellendi")
            else:
                return False, f"Supabase tablo hatası ({resp.status_code}): {resp.text[:200]}"

            # Varlık bazlı çoklu dönem metriklerini kaydet
            all_assets = (
                report.bist_endeksleri
                + report.abd_ve_kuresel_endeksler
                + report.altin_ve_gumus_usd
                + report.kripto_varliklar
                + report.doviz_ve_dxy
                + report.tahvil_ve_cds
                + report.petrol_ve_emtia
            )
            metric_rows = [
                {
                    "report_date": report.tarih,
                    "symbol": a.kod,
                    "asset_name": a.ad,
                    "category": a.kategori,
                    "price": a.fiyat,
                    "unit": a.birim,
                    "chg_1d": a.degisim_1g,
                    "chg_1w": a.degisim_1h,
                    "chg_1m": a.degisim_1a,
                    "chg_3m": a.degisim_3a,
                    "chg_ytd": a.degisim_ytd,
                    "chg_1y": a.degisim_1y,
                }
                for a in all_assets
            ]
            if metric_rows:
                requests.post(
                    f"{self.url}/rest/v1/asset_daily_metrics?on_conflict=report_date,symbol",
                    headers=self._headers(),
                    json=metric_rows,
                    timeout=15,
                )
                messages.append(f"{len(metric_rows)} varlık metriği kaydedildi")

            # Excel dosyasını Supabase Storage bucket'ına yükle
            if excel_path and excel_path.exists():
                storage_headers = {
                    "apikey": self.key,
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "x-upsert": "true",
                }
                up_resp = requests.post(
                    f"{self.url}/storage/v1/object/{self.bucket}/Finans_Veri_Tabani.xlsx",
                    headers=storage_headers,
                    data=excel_path.read_bytes(),
                    timeout=25,
                )
                if up_resp.status_code in (200, 201):
                    messages.append("Excel dosyası Supabase Storage'a yüklendi")

            return True, " | ".join(messages)
        except Exception as exc:
            return False, f"Supabase bağlantı hatası: {exc}"
