import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import pandas as pd

# Configuration
SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "../config/credentials.json")

def check_data_integrity():
    print("--- [HEALTH CHECK] Vérification de l'intégrité des données ---")
    
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        ss = client.open_by_key(SHEET_ID)
        
        worksheets = [ws for ws in ss.worksheets() if ws.title in ['Base_Active', 'Rapport_Veille_Auto', 'Informative']]
        
        for ws in worksheets:
            print(f"\n> État de l'onglet : {ws.title}")
            data = ws.get_all_records()
            if not data:
                print("   ⚠️ Onglet vide.")
                continue
                
            df = pd.DataFrame(data)
            df.columns = [c.strip() for c in df.columns]
            
            total_rows = len(df)
            print(f"   Total : {total_rows} lignes.")
            
            # Colonnes critiques à surveiller
            critical_cols = [
                'Intitulé', 'Thème', 'Grand thème', 'Statut', 
                'Conformité', 'Criticité', 'Type de texte', 'Date'
            ]
            
            for col in critical_cols:
                # On cherche les colonnes qui "contiennent" le nom (car parfois espaces ou accents)
                actual_col = None
                for c in df.columns:
                    if col.lower() in c.lower().strip():
                        actual_col = c
                        break
                
                if actual_col:
                    missing = df[actual_col].astype(str).str.strip().replace(['', '-', 'None', 'nan', 'N/A', 'Inconnue'], pd.NA).isna().sum()
                    perc = (missing / total_rows) * 100
                    status = "✅" if perc < 5 else "⚠️" if perc < 20 else "❌"
                    print(f"   {status} {col:<15} : {missing:>4} vides ({perc:>5.1f}%)")
                # else:
                #    print(f"   ❓ {col:<15} : Colonne introuvable.")

    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    check_data_integrity()
