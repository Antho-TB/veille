# ---------------------------------------------------------------------------
# Sanitize Sheets - Veille Réglementaire
# ---------------------------------------------------------------------------
# Ce script purge les données non-officielles des Google Sheets.
# ---------------------------------------------------------------------------

import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys

# Ajouter la racine du projet au path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from src.core.pipeline import Config

# --- CONFIGURATION ---
OFFICIAL_TYPES = ['Arrêté', 'Décret', 'Loi', 'Règlement', 'Directive', 'Décision', 'Ordonnance', 'Avis']

class DataSanitizer:
    def __init__(self):
        self.client = None
        self.sheet = None

    def connect(self):
        if not os.path.exists(Config.CREDENTIALS_FILE):
            raise FileNotFoundError("Manque credentials.json")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope))
        self.sheet = self.client.open_by_key(Config.SHEET_ID)

    def sanitize_worksheet(self, worksheet_name):
        print(f"--- Nettoyage de l'onglet : {worksheet_name} ---")
        try:
            ws = self.sheet.worksheet(worksheet_name)
            data = ws.get_all_records()
            if not data:
                print(f"   > L'onglet {worksheet_name} est vide.")
                return
            
            df = pd.DataFrame(data)
            total_before = len(df)
            
            if 'Type de texte' not in df.columns:
                print(f"   > ⚠️ Colonne 'Type de texte' manquante dans {worksheet_name}.")
                return

            # Filtrage strict
            df_clean = df[df['Type de texte'].astype(str).str.strip().str.capitalize().isin(OFFICIAL_TYPES)]
            
            total_after = len(df_clean)
            removed = total_before - total_after
            
            if removed > 0:
                print(f"   > {removed} lignes non-officielles identifiées pour suppression.")
                # Ré-upload du dataframe nettoyé
                ws.clear()
                ws.append_row(df.columns.tolist())
                if not df_clean.empty:
                    ws.append_rows(df_clean.astype(str).values.tolist())
                print(f"   > ✅ Onglet {worksheet_name} nettoyé.")
            else:
                print(f"   > ✅ Aucun texte non-officiel détecté dans {worksheet_name}.")
                
        except Exception as e:
            print(f"   > ❌ Erreur lors du nettoyage de {worksheet_name} : {e}")

if __name__ == "__main__":
    sanitizer = DataSanitizer()
    sanitizer.connect()
    sanitizer.sanitize_worksheet('Rapport_Veille_Auto')
    sanitizer.sanitize_worksheet('Base_Active')
