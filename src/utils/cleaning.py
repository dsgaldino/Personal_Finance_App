import re
import unicodedata
import pandas as pd

BANK_TOKENS = ['IBAN', 'BIC', 'ABNA', 'ABNANL', 'INGB', 'RABO', 'COBA', 'CITI', 'NL']

TIKKIE_TOKENS = [
    # SEPA structure
    "SEPA", "OVERBOEKING", "INCASSO", "IDEAL", "BETAALVERZOEK",
    "A NAAM", "NAAM", "IBAN", "BIC", "ABNANL2A", "KENMERK", "NOTPROVIDED",
    "ECOM", "APPLE", "PAY", "BEA", "PAS NR", "A NAME", "ID", "BETAALPAS", "CSID", "NAME",
    # Tikkie specific
    "TIKKIE", "OMSCHRIJVING", "TIKKIE ID", "VIA TIKKIE", "TERUGBOEKING", "TRANSACTIE",
    # Bank/Institution
    "AAB", "INZ", "ABNA", "ABN", "RABO", "INGB", "ALGEMEEN", "MARF E DEUT DEUT", "LU BCIRLULL", 
    "DOORLOPEND", "ZZZ", "E DEUT",
    "CFROM TO DIRECT SAVINGS FOR INTEREST RATES PLEASE VISIT WWW MRO RENTE",
    "AMRO BANK NV", "FACTUUR", "BE TRWIBEB", "OMSCHRIJVING", "PAKKET", "PAKKETPOLISNR", "BNGH",
    # Metadata
    "KENMERK", "MACHTIGING", "EREF", "REMI", "ADYB", "BOFA BOFA", "AXXX", "MARF A",
    "DE NTSBDEB XXX", "LU PPLXLUL XXX", "TRTP", "INCASSANT", "PERIODE", 
    "NR H IB PVV", "COAXX", "ORDP RKJX E DR R",
    "TERMIJN TERMIJN (VERVALDATUM MEI BETALINGSREGELING DEUT)",
    # Locations
    "DUBLIN", "LAND", "NL", "ST", "CCV", "TVM", "CSO", "BCK", "NX",
]

def clean_basic_description(desc: str) -> str:
    """Hard cleaning: uppercase, remove bank tokens, normalize accents, drop special chars."""
    if pd.isna(desc):
        return ""
    desc = str(desc).upper()
    for token in BANK_TOKENS:
        desc = desc.replace(token, " ")
    desc = unicodedata.normalize("NFKD", desc).encode("ASCII", "ignore").decode("ASCII")
    desc = re.sub(r"[^A-Z\s]", " ", desc)
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc

def clean_tikkie_v2(desc_cleaned: str) -> str:
    """
    Universal Tikkie cleaner:
    1) Remove Tikkie tokens
    2) Remove isolated single letters (except inside parentheses)
    3) Apply VAN/VIA logic:
       - X VAN Y → X (Y)
       - X VIA Y → Y (X)
    """
    if pd.isna(desc_cleaned):
        return ""
    desc = str(desc_cleaned)

    # 1) Remove tokens
    tmp = " " + desc + " "
    for token in TIKKIE_TOKENS:
        tmp = tmp.replace(" " + token + " ", " ")
    tmp = re.sub(r"\s+", " ", tmp).strip()

    # 2) Remove isolated single letters, preserving inside (...)
    tmp = re.sub(r"\(([^)]*)\)", r"@@@PROTECTED@@@ \1 @@@PROTECTED@@@", tmp)
    tmp = re.sub(r"\b[A-Z]\b(?!\s*\()", " ", tmp)
    tmp = re.sub(r"@@@PROTECTED@@@", "", tmp)
    tmp = re.sub(r"\s+", " ", tmp).strip()

    # 3) VAN / VIA logic
    words = tmp.split()
    for i, word in enumerate(words):
        if word.upper() == "VAN":
            label = " ".join(words[:i]).strip()
            name  = " ".join(words[i+1:]).strip()
            if label and name:
                return f"{label} ({name})"
        elif word.upper() == "VIA":
            label = " ".join(words[i+1:]).strip()
            name  = " ".join(words[:i]).strip()
            if label and name:
                return f"{label} ({name})"

    # Fallback: cleaned text
    return tmp