import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys

# Ajouter la racine du projet au path
sys.path.append(os.getcwd())
from src.core.pipeline import Config

def add_missing_columns():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(Config.SHEET_ID)
    ws = sheet.worksheet('Base_Active')
    
    headers = ws.row_values(1)
    missing = ['Criticité', 'Preuve de Conformité Attendue', 'Justificatif de déclaration et contrôle', 'Plan Action', 'Responsable', 'Échéance']
    
    to_add = [m for m in missing if m not in headers]
    
    if to_add:
        start_col = len(headers) + 1
        for i, col_name in enumerate(to_add):
            ws.update_cell(1, start_col + i, col_name)
        print(f"✅ Ajouté {len(to_add)} colonnes: {to_add}")
    else:
        print("✅ Toutes les colonnes sont déjà présentes.")

if __name__ == "__main__":
    add_missing_columns()
