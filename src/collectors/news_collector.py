import html
import re
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET
from typing import Dict, List, Set
import requests
from src.models import NewsHeadline


class NewsCollector:
    """
    1) Finans otoriteleri (TCMB, Fed, ECB, BDDK, SPK, Hazine) ve büyük bankaların
       (Goldman Sachs, BofA, JPMorgan, Morgan Stanley, Fitch, Moody's vb.) açıklamalarını
       yalnızca temiz başlıklar halinde toplar.
    2) Türkiye'deki konut satış istatistikleri (TÜİK) ve araç/otomotiv satış
       istatistiklerini (ODMD) takip eder.
    """

    def __init__(self, timeout: int = 10):
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
    def _clean_title_and_source(raw_title: str, default_source: str = "Finans Haber") -> tuple[str, str]:
        cleaned = html.unescape(raw_title or "").strip()
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        if " - " in cleaned:
            parts = cleaned.rsplit(" - ", 1)
            return parts[0].strip(), parts[1].strip()
        return cleaned, default_source

    def _fetch_rss_items(self, rss_url: str, default_source: str, max_items: int = 10) -> List[Dict[str, str]]:
        items_out: List[Dict[str, str]] = []
        try:
            resp = self.session.get(rss_url, timeout=self.timeout)
            if resp.status_code != 200:
                return []
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:max_items]:
                raw_title = item.findtext("title") or ""
                link = item.findtext("link") or ""
                pub_date = item.findtext("pubDate") or ""
                source_el = item.find("source")
                src_name = source_el.text.strip() if (source_el is not None and source_el.text) else default_source

                title, extracted_src = self._clean_title_and_source(raw_title, src_name)
                if title:
                    items_out.append(
                        {
                            "title": title,
                            "source": extracted_src,
                            "link": link.strip(),
                            "pubDate": pub_date.strip(),
                        }
                    )
        except Exception:
            pass
        return items_out

    def _google_news_rss_url(self, query: str) -> str:
        encoded = quote_plus(f"{query} when:7d")
        return f"https://news.google.com/rss/search?q={encoded}&hl=tr&gl=TR&ceid=TR:tr"

    def collect_authority_and_bank_headlines(
        self, keywords: List[str], max_headlines: int = 10
    ) -> List[NewsHeadline]:
        """
        Merkez bankaları, finans otoriteleri ve yatırım bankalarının açıklamalarını başlık olarak toplar.
        """
        queries = [
            'TCMB OR "Merkez Bankası" OR PPK OR Karahan OR "Mehmet Şimşek" faiz enflasyon',
            '"Goldman Sachs" OR JPMorgan OR BofA OR "Morgan Stanley" OR HSBC OR Fitch OR Moody\'s Türkiye',
            'Fed OR Powell OR ECB OR Lagarde faiz kararı enflasyon',
        ]
        direct_feeds = [
            ("https://www.bloomberght.com/rss", "Bloomberg HT"),
            ("https://www.ekonomim.com/rss", "Ekonomim"),
        ]

        raw_candidates: List[Dict[str, str]] = []
        for q in queries:
            raw_candidates.extend(self._fetch_rss_items(self._google_news_rss_url(q), "Google Haberler", max_items=6))

        for feed_url, src_name in direct_feeds:
            raw_candidates.extend(self._fetch_rss_items(feed_url, src_name, max_items=15))

        seen_Fingerprints: Set[str] = set()
        headlines: List[NewsHeadline] = []

        for cand in raw_candidates:
            title = cand["title"]
            # Başlığın ilk 35 karakteriyle mükerrer kontrolü
            fp = re.sub(r"\W+", "", title.lower())[:35]
            if not fp or fp in seen_Fingerprints:
                continue

            matched_tags = [
                kw for kw in keywords if kw.lower() in title.lower()
            ]
            if not matched_tags:
                continue

            seen_Fingerprints.add(fp)
            headlines.append(
                NewsHeadline(
                    baslik=title,
                    kaynak=cand["source"],
                    kategori="otorite_banka",
                    tarih_saat=cand.get("pubDate", ""),
                    link=cand.get("link", ""),
                    etiketler=matched_tags[:3],
                )
            )
            if len(headlines) >= max_headlines:
                break

        return headlines

    def collect_housing_and_auto_stats(self, max_per_topic: int = 2) -> List[NewsHeadline]:
        """
        Türkiye'deki konut satış istatistikleri (TÜİK) ve araç/otomotiv satış
        istatistiklerini (ODMD) başlık olarak çeker.
        """
        results: List[NewsHeadline] = []
        seen: Set[str] = set()

        # 1. Konut Satış İstatistikleri (son 30 gün, çünkü TÜİK ayda bir açıklar)
        housing_q = quote_plus('("TÜİK" AND "konut satış") OR "konut satış istatistikleri" OR "konut fiyat endeksi" when:30d')
        housing_url = f"https://news.google.com/rss/search?q={housing_q}&hl=tr&gl=TR&ceid=TR:tr"
        housing_items = self._fetch_rss_items(housing_url, "TÜİK / Konut Sektörü", max_items=6)

        count_h = 0
        for item in housing_items:
            title = item["title"]
            fp = re.sub(r"\W+", "", title.lower())[:35]
            if fp in seen:
                continue
            if any(w in title.lower() for w in ("konut", "ev satış", "ipotek", "tüik")):
                seen.add(fp)
                results.append(
                    NewsHeadline(
                        baslik=title,
                        kaynak=item["source"],
                        kategori="konut",
                        tarih_saat=item.get("pubDate", ""),
                        link=item.get("link", ""),
                        etiketler=["Konut İstatistikleri", "TÜİK"],
                    )
                )
                count_h += 1
                if count_h >= max_per_topic:
                    break

        # 2. Otomotiv / Araç Satış İstatistikleri (ODMD - son 30 gün)
        auto_q = quote_plus('("ODMD" AND ("otomobil" OR "satış")) OR "otomobil ve hafif ticari araç" OR "araç satışları" when:30d')
        auto_url = f"https://news.google.com/rss/search?q={auto_q}&hl=tr&gl=TR&ceid=TR:tr"
        auto_items = self._fetch_rss_items(auto_url, "ODMD / Otomotiv Sektörü", max_items=6)

        count_a = 0
        for item in auto_items:
            title = item["title"]
            fp = re.sub(r"\W+", "", title.lower())[:35]
            if fp in seen:
                continue
            if any(w in title.lower() for w in ("otomobil", "araç", "otomotiv", "odmd", "hafif ticari")):
                seen.add(fp)
                results.append(
                    NewsHeadline(
                        baslik=title,
                        kaynak=item["source"],
                        kategori="arac",
                        tarih_saat=item.get("pubDate", ""),
                        link=item.get("link", ""),
                        etiketler=["Otomotiv Pazarı", "ODMD"],
                    )
                )
                count_a += 1
                if count_a >= max_per_topic:
                    break

        return results
