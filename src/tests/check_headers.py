import os
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Ajouter la racine du projet au path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from src.core.pipeline import Config

def check_headers():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(Config.SHEET_ID)
    
    for ws_name in ["Base_Active", "Rapport_Veille_Auto"]:
        try:
            ws = sheet.worksheet(ws_name)
            header = ws.row_values(1)
            print(f"--- Headers for {ws_name} ---")
            for i, h in enumerate(header):
                print(f"{i+1}: {h}")
        except Exception as e:
            print(f"Error reading {ws_name}: {e}")

if __name__ == "__main__":
    check_headers()
