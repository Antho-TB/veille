import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import time

# Configuration
SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "../config/credentials.json")

def standardize_format():
    print("--- [UI] Standardisation de la mise en forme du Google Sheet ---")
    
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        ss = client.open_by_key(SHEET_ID)
        
        worksheets = ss.worksheets()
        
        for ws in worksheets:
            print(f"   > Formatage de l'onglet : {ws.title}")
            
            # 1. Récupération des dimensions
            rows = ws.row_count
            cols = ws.col_count
            header_values = ws.row_values(1)
            num_cols = len(header_values)
            
            if num_cols == 0: continue

            # 2. Préparation du Batch Update (Plus efficace)
            # - Freeze row 1
            # - Header style (Dark Slate, White, Bold)
            # - Alternating colors (Banding)
            # - Borders subtle
            
            # Note: On utilise format() pour la simplicité si dispo, sinon batch_update
            
            # Header Format
            header_range = f"A1:{gspread.utils.rowcol_to_a1(1, num_cols)}"
            ws.format(header_range, {
                "backgroundColor": {"red": 0.08, "green": 0.2, "blue": 0.35}, # Professional Deep Blue #153359
                "horizontalAlignment": "CENTER",
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True, "fontSize": 10}
            })
            
            # Body Basic Format
            body_range = f"A2:{gspread.utils.rowcol_to_a1(rows, num_cols)}"
            ws.format(body_range, {
                "verticalAlignment": "MIDDLE",
                "textFormat": {"fontSize": 9},
                "padding": {"top": 3, "bottom": 3, "left": 5, "right": 5}
            })

            # Alternating Colors (Banding) for "Not Sad" look
            try:
                # Supprimer le banding existant pour réinitialiser
                # ws.clear_basic_filter() # Non, ça vire les filtres
                ws.add_banding(body_range, 
                               first_band_color={"red": 1, "green": 1, "blue": 1}, 
                               second_band_color={"red": 0.94, "green": 0.96, "blue": 1.0}) # Light Blue Banding
            except: 
                print(f"      [INFO] Banding déjà présent ou non supporté sur {ws.title}")

            # Figer la ligne 1
            ws.freeze(rows=1)
            
            try: ws.set_basic_filter()
            except: pass
            
            print(f"      [OK] Style & Banding appliqués.")
            time.sleep(0.5)
            
        print("\n--- ✅ Mise en forme terminée pour l'ensemble du classeur ---")
        
    except Exception as e:
        print(f"   > ❌ Erreur : {e}")

if __name__ == "__main__":
    standardize_format()
