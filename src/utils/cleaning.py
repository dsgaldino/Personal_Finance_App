import re
import unicodedata
import pandas as pd


def _dedupe_keep_order(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


# Unifica e deduplica tudo em uma lista só
RAW_TOKENS = [
    # BANK_TOKENS
    "IBAN", "BIC", "ABNA", "ABNANL", "INGB", "RABO", "COBA", "CITI", "NL",

    # TIKKIE_TOKENS (como estava)
    "SEPA", "OVERBOEKING", "INCASSO", "IDEAL", "BETAALVERZOEK","A NAAM", 
    "NAAM", "IBAN", "BIC", "ABNANL2A", "KENMERK", "NOTPROVIDED","ECOM",
    "APPLE", "PAY", "BEA", "PAS NR", "A NAME", "ID", "BETAALPAS", "CSID", 
    "NAME","TIKKIE", "OMSCHRIJVING", "TIKKIE ID", "VIA TIKKIE", "TERUGBOEKING",
    "TRANSACTIE","AAB", "INZ", "ABNA", "ABN", "RABO", "INGB", "ALGEMEEN",
    "MARF E DEUT DEUT", "LU BCIRLULL", "DOORLOPEND", "ZZZ", "E DEUT",
    "CFROM TO DIRECT SAVINGS FOR INTEREST RATES PLEASE VISIT WWW MRO RENTE",
    "AMRO BANK NV", "FACTUUR", "BE TRWIBEB", "OMSCHRIJVING", "PAKKET", 
    "PAKKETPOLISNR", "BNGH","KENMERK", "MACHTIGING", "EREF", "REMI", "ADYB",
    "BOFA BOFA", "AXXX", "MARF A", "DE NTSBDEB XXX", "LU PPLXLUL XXX", "TRTP",
    "INCASSANT", "PERIODE","NR H IB PVV", "COAXX", "ORDP RKJX E DR R", 
    "TERMIJN TERMIJN (VERVALDATUM MEI BETALINGSREGELING DEUT)","DUBLIN",
    "LAND", "NL", "ST", "CCV", "TVM", "CSO", "BCK", "NX",
]

TOKENS = _dedupe_keep_order([t.strip().upper() for t in RAW_TOKENS if str(t).strip()])


def _normalize_text_upper(desc: str) -> str:
    if pd.isna(desc):
        return ""
    desc = str(desc).upper()
    desc = unicodedata.normalize("NFKD", desc).encode("ASCII", "ignore").decode("ASCII")
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc


def clean_basic_description(desc: str) -> str:
    """
    Hard cleaning:
    - uppercase
    - normalize accents
    - drop special chars (keep only A-Z and spaces)
    """
    desc = _normalize_text_upper(desc)
    if not desc:
        return ""

    desc = re.sub(r"[^A-Z\s]", " ", desc)
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc


def clean_tikkie(desc_cleaned: str) -> str:
    """
    Universal cleaner:
    1) Remove tokens
    2) Remove isolated single letters (except inside parentheses)
    3) Apply VAN/VIA logic:
       - X VAN Y → X (Y)
       - X VIA Y → Y (X)
    """
    desc = _normalize_text_upper(desc_cleaned)
    if not desc:
        return ""

    # 1) Remove tokens as whole-words (safer than plain replace)
    tmp = " " + desc + " "
    for token in TOKENS:
        tmp = re.sub(rf"(?<!\w){re.escape(token)}(?!\w)", " ", tmp)
    tmp = re.sub(r"\s+", " ", tmp).strip()

    # 2) Remove isolated single letters, preserving inside (...)
    tmp = re.sub(r"\(([^)]*)\)", r"@@@PROTECTED@@@ \1 @@@PROTECTED@@@", tmp)
    tmp = re.sub(r"\b[A-Z]\b(?!\s*\()", " ", tmp)
    tmp = re.sub(r"@@@PROTECTED@@@", "", tmp)
    tmp = re.sub(r"\s+", " ", tmp).strip()

    # 3) VAN / VIA logic
    words = tmp.split()
    for i, word in enumerate(words):
        if word == "VAN":
            label = " ".join(words[:i]).strip()
            name = " ".join(words[i + 1:]).strip()
            if label and name:
                return f"{label} ({name})"
        if word == "VIA":
            label = " ".join(words[i + 1:]).strip()
            name = " ".join(words[:i]).strip()
            if label and name:
                return f"{label} ({name})"

    return tmp


def clean_description_for_rules(desc: str) -> str:
    """
    Pipeline única para regras:
    - basic normalize
    - token removal + heurísticas
    """
    base = clean_basic_description(desc)
    return clean_tikkie(base)
