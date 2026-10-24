import re
from typing import List, Tuple


# TTS Motorlarının Türkçe Doğal Okuması İçin Kısaltma ve Sembol Sözlüğü
TTS_ABBREVIATION_MAP: List[Tuple[str, str]] = [
    (r"\bS&P\s*500\b", "Es end Pi 500"),
    (r"\bS&P\b", "Es end Pi"),
    (r"\bBIST\s*100\b", "Borsa İstanbul 100"),
    (r"\bBIST\s*30\b", "Borsa İstanbul 30"),
    (r"\bBIST\b", "Borsa İstanbul"),
    (r"\bUSD/TRY\b", "Dolar Türk Lirası"),
    (r"\bEUR/TRY\b", "Euro Türk Lirası"),
    (r"\bDolar\s*/\s*TL\b", "Dolar Türk Lirası"),
    (r"\bEuro\s*/\s*TL\b", "Euro Türk Lirası"),
    (r"\bTCMB\b", "Türkiye Cumhuriyet Merkez Bankası"),
    (r"\bPPK\b", "Para Politikası Kurulu"),
    (r"\bTÜİK\b", "TÜİK"),
    (r"\bODMD\b", "Otomotiv Distribütörleri ve Mobilite Derneği"),
    (r"\bBDDK\b", "Bankacılık Düzenleme ve Denetleme Kurumu"),
    (r"\bSPK\b", "Sermaye Piyasası Kurulu"),
    (r"\bECB\b", "Avrupa Merkez Bankası"),
    (r"\bFed\b", "Amerikan Merkez Bankası Fed"),
    (r"\bBofA\b", "Bank of America"),
    (r"\bGSYH\b", "Gayri Safi Yurt İçi Hasıla"),
    (r"\bTÜFE\b", "Tüketici Fiyat Endeksi"),
    (r"\bÜFE\b", "Üretici Fiyat Endeksi"),
    (r"\bNFP\b", "Tarım Dışı İstihdam"),
    (r"\bPMI\b", "Pi Em Ay"),
    (r"\bVIX\b", "Viks"),
    (r"\bBTC\b", "Bitkoin"),
    (r"\bETH\b", "Eteryum"),
    (r"\bUSD\b", "Dolar"),
    (r"\bTL\b", "Türk Lirası"),
]


def format_number_for_speech(value: float, decimals: int = 2) -> str:
    """
    Sayıları Türkçe TTS motorlarının en doğal okuyacağı formata çevirir.
    Örn: 34.25 -> '34 virgül 25', 9850.0 -> '9850'
    """
    if value is None:
        return "veri yok"
    abs_val = abs(value)
    if decimals == 0 or abs_val >= 10000:
        return f"{int(round(abs_val))}"
    formatted = f"{abs_val:.{decimals}f}"
    tam, ondalik = formatted.split(".")
    if int(ondalik) == 0:
        return tam
    return f"{tam} virgül {ondalik}"


def normalize_text_for_tts(text: str) -> str:
    """
    Haber metnini veya başlığı sesli okuma (TTS) motorları için temizler ve normalize eder.
    Emojileri, Markdown işaretlerini kaldırır; kısaltmaları ve yüzdeleri okunuşuna çevirir.
    """
    if not text:
        return ""

    out = text

    # Markdown kalın/italik/başlık karakterlerini temizle
    out = re.sub(r"[*_`#~>|]", "", out)

    # Emojileri temizle
    out = re.sub(r"[\U00010000-\U0010ffff\u2600-\u27bf]", "", out)

    # Mükerrer parantez içi kısaltmaları önle (örn: "BofA (Bank of America)" -> "Bank of America")
    out = re.sub(r"\bBofA\s*\(\s*Bank of America\s*\)", "Bank of America", out, flags=re.IGNORECASE)
    out = re.sub(r"\bPara Politikası Kurulu\s*\(\s*PPK\s*\)", "Para Politikası Kurulu", out, flags=re.IGNORECASE)

    # Yüzde ifadelerini düzelt: %2,45 veya %2.45 -> ' yüzde 2 virgül 45' (öndeki boşluğu koru)
    out = re.sub(
        r"([+-])?%\s*(\d+)[,\.](\d+)",
        lambda m: f" yüzde {m.group(2)} virgül {m.group(3)}",
        out,
    )
    out = re.sub(r"([+-])?%\s*(\d+)", r" yüzde \2", out)

    # Ekonomik takvimdeki '227K' gibi binlik ifadeleri '227 bin' yap
    out = re.sub(r"\b(\d+(?:[,\.]\d+)?)K\b", r"\1 bin", out)

    # Ondalıklı sayıları 'virgül' ile okunacak hale getir (örn: 34,25 veya 47.8 -> 34 virgül 25)
    out = re.sub(r"\b(\d+)[,\.](\d{1,2})\b", r"\1 virgül \2", out)

    # Para birimi sembolleri
    out = out.replace("$", " dolar ").replace("€", " euro ").replace("₺", " Türk Lirası ")

    # Kısaltma sözlüğü dönüşümleri
    for pattern, replacement in TTS_ABBREVIATION_MAP:
        out = re.sub(pattern, replacement, out)

    # Fazla boşlukları temizle
    out = re.sub(r"\s+", " ", out).strip()
    return out
