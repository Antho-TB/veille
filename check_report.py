# ---------------------------------------------------------------------------
# Outil de Diagnostic - Qualité des Données
# ---------------------------------------------------------------------------
# Ce script utilitaire permet de :
# 1. Auditer le contenu de l'onglet Rapport_Veille_Auto.
# 2. Détecter les anomalies (titres manquants, types incorrects).
# 3. Fournir des statistiques sur les données importées.
# ---------------------------------------------------------------------------

import os
import json
import gspread
import pandas as pd
import re
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION (Copied from pipeline_veille.py) ---
class Config:
    SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
    CREDENTIALS_FILE = "credentials.json"

# --- DATA MANAGER (Simplified) ---
class DataManager:
    def __init__(self):
        self.client = None
    
    def _connect(self):
        if not os.path.exists(Config.CREDENTIALS_FILE): 
            raise FileNotFoundError("Manque credentials.json")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope))

def check_report():
    print("--- Audit du Rapport_Veille_Auto ---")
    dm = DataManager()
    try:
        dm._connect()
        sheet = dm.client.open_by_key(Config.SHEET_ID)
        try:
            ws = sheet.worksheet('Rapport_Veille_Auto')
        except:
            print("❌ Feuille 'Rapport_Veille_Auto' introuvable.")
            return

        data = ws.get_all_records()
        if not data:
            print("⚠️ La feuille est vide.")
            return

        df = pd.DataFrame(data)
        print(f"📊 Total lignes : {len(df)}")
        
        if 'Type de texte' in df.columns:
            print("\n--- Répartition par Type ---")
            print(df['Type de texte'].value_counts())
            
            official_types = ['Arrêté', 'Décret', 'Loi', 'Règlement', 'Directive', 'Décision', 'Ordonnance', 'Avis']
            
            # Filter for potentially non-official texts
            # We normalize to title case for comparison just in case
            mask = ~df['Type de texte'].astype(str).apply(lambda x: x.strip().capitalize() in official_types or x.strip() == "")
            non_official = df[mask]
            
            if not non_official.empty:
                print(f"\n⚠️ {len(non_official)} Textes potentiellement NON OFFICIELS détectés :")
                for idx, row in non_official.iterrows():
                    print(f"- [Ligne {idx+2}] {row.get('Type de texte', '?')}: {row.get('Intitulé ', 'Sans titre')[:80]}...")
            else:
                print("\n✅ Tous les textes semblent avoir un type officiel.")
        else:
            print("⚠️ Colonne 'Type de texte' manquante.")

        # Check for empty titles
        empty_titles = df[df['Intitulé '] == ""]
        if not empty_titles.empty:
            print(f"\n⚠️ {len(empty_titles)} lignes sans titre.")

    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    check_report()
