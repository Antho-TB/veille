import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys

# Ajouter la racine du projet au path
sys.path.append(os.getcwd())
from src.core.pipeline import Config

def search_missing_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(Config.SHEET_ID)
    
    search_terms = ['2024/573', '2025-804', '2025/40', 'emballages']
    found = False
    
    print(f"--- Recherche exhaustive dans le Sheet: {sheet.title} ---")
    
    for ws in sheet.worksheets():
        print(f"Analyse de {ws.title}...")
        try:
            vals = ws.get_all_values()
            for i, row in enumerate(vals):
                line = ' '.join(str(cell) for cell in row).lower()
                for term in search_terms:
                    if term.lower() in line:
                        print(f"MATCH: '{term}' trouvé dans '{ws.title}' à la ligne {i+1}")
                        found = True
        except Exception as e:
            print(f"Erreur lecture {ws.title}: {e}")
            
    if not found:
        print("AUCUNE CORRESPONDANCE TROUVÉE")

if __name__ == "__main__":
    search_missing_data()
