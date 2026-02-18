
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# CONFIG
SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
CREDENTIALS_FILE = "config/credentials.json"

def repair_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    
    new_cols = ['Criticité', 'Preuve de Conformité Attendue']
    
    for ws_name in ['Base_Active', 'Rapport_Veille_Auto']:
        try:
            ws = sheet.worksheet(ws_name)
            headers = ws.row_values(1)
            missing = [c for c in new_cols if c not in headers]
            
            if missing:
                start_col = len(headers) + 1
                for i, col_name in enumerate(missing):
                    ws.update_cell(1, start_col + i, col_name)
                print(f"✅ Ajouté {missing} à {ws_name}")
            else:
                print(f"ℹ️ {ws_name} déjà à jour.")
            
            # On récupère les headers à jour
            headers = ws.row_values(1)
            crit_idx = headers.index('Criticité') + 1
            
            # On récupère toutes les lignes (pour voir combien on a)
            all_values = ws.get_all_values()
            num_rows = len(all_values) - 1 # Sans header
            
            if num_rows > 0:
                print(f"🔄 Mise à jour de {num_rows} lignes dans {ws_name}...")
                cells_to_update = []
                for i in range(num_rows):
                    row_idx = i + 2
                    # On injecte de la variété pour les tests : 
                    # 5 premières = Haute, 5 suivantes = Moyenne, le reste = Basse
                    if i < 5: val = "Haute"
                    elif i < 10: val = "Moyenne"
                    else: val = "Basse"
                    
                    cells_to_update.append(gspread.Cell(row=row_idx, col=crit_idx, value=val))
                
                # Mise à jour par lots pour la performance (batch)
                ws.update_cells(cells_to_update)
                print(f"✅ Injecté criticités variées dans {ws_name}")

        except Exception as e:
            print(f"❌ Erreur sur {ws_name} : {e}")

if __name__ == "__main__":
    repair_sheets()
