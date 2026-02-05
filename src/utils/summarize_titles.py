# ---------------------------------------------------------------------------
# Outil de Nettoyage - Résumé des Titres
# ---------------------------------------------------------------------------
# Ce script utilitaire permet de :
# 1. Parcourir les intitulés longs et complexes.
# 2. Générer des résumés courts et lisibles pour l'humain.
# 3. Mettre à jour la colonne 'Intitulé' pour une meilleure lisibilité.
# ---------------------------------------------------------------------------

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import re

SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
CREDENTIALS_FILE = "credentials.json"

# Connect to Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)

sheet = client.open_by_key(SHEET_ID)
ws = sheet.worksheet('Rapport_Veille_Auto')

# Load data into DataFrame
raw = ws.get_all_values()
header = raw[0]
rows = raw[1:]

df = pd.DataFrame(rows, columns=header)

print(f"📊 {len(df)} lignes à traiter")

# Helper to create a concise summary from the original title

def summarize_title(title: str) -> str:
    """Return a short summary of the document.
    Heuristics:
    - Keep the document type (Arrêté, Décret, Loi, etc.)
    - Extract the main subject after keywords like 'relatif aux', 'relatif à', 'concernant', 'sur', etc.
    - Truncate to ~8 words.
    """
    title = title.strip()
    if not title:
        return ""
    # Detect document type
    doc_type_match = re.match(r"^(arrêté|décret|loi|circulaire|directive|ordonnance|règlement)", title, re.I)
    doc_type = doc_type_match.group(1).capitalize() if doc_type_match else "Document"

    # Try to find the subject after common connectors
    subject = ""
    patterns = [
        r"relatif aux? (.+?)$",
        r"concernant (.+?)$",
        r"sur (.+?)$",
        r"de (.+?)$",
    ]
    for pat in patterns:
        m = re.search(pat, title, re.I)
        if m:
            subject = m.group(1)
            break
    # Fallback: remove the date part (e.g., 'Arrêté du 2 février 1998')
    if not subject:
        subject = re.sub(r"arrêté du \d{1,2} \w+ \d{4}", "", title, flags=re.I).strip()
    # Clean up punctuation
    subject = re.sub(r"[:;\-]", "", subject)
    # Limit length
    words = subject.split()
    if len(words) > 8:
        subject = " ".join(words[:8]) + "…"
    return f"{doc_type}: {subject}" if subject else doc_type

# Apply summarization
updates = 0
for idx, row in df.iterrows():
    original = str(row.get('Intitulé ', '')).strip()
    if not original:
        continue
    new_summary = summarize_title(original)
    if new_summary != original:
        df.at[idx, 'Intitulé '] = new_summary
        updates += 1
        print(f"🔧 Ligne {idx+1}: '{original[:60]}...' → '{new_summary}'")

if updates:
    print(f"\n💾 Sauvegarde des {updates} lignes avec nouveaux intitulés...")
    # Clear sheet and write back (preserve header)
    ws.clear()
    ws.append_row(header)
    rows_to_write = df.fillna('').astype(str).values.tolist()
    if rows_to_write:
        ws.append_rows(rows_to_write)
    print("✅ Mise à jour terminée")
else:
    print("ℹ️ Aucun changement nécessaire")

print(f"🔗 Vérifier: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid={ws.id}")
