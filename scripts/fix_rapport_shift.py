import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import time

# Configuration
SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "../config/credentials.json")

def surgical_fix_shift():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    ss = client.open_by_key(SHEET_ID)
    ws = ss.worksheet('Rapport_Veille_Auto')
    
    # On prend tout d'un coup pour éviter les appels répétitifs
    data = ws.get_all_values()
    header = data[0]
    rows = data[1:]
    
    cells_to_update = []
    fixed_count = 0
    
    for i, row in enumerate(rows):
        row_num = i + 2
        # Q=17 (index 16), R=18 (index 17), S=19 (index 18)
        q_val = row[16].strip() if len(row) > 16 else ""
        r_val = row[17].strip() if len(row) > 17 else ""
        s_val = row[18].strip() if len(row) > 18 else ""
        
        # Détection du shift : Q contient une criticité
        if q_val.lower() in ['haute', 'moyenne', 'basse']:
            # 1. Déplacer Q -> R (Criticité)
            cells_to_update.append(gspread.Cell(row=row_num, col=18, value=q_val))
            
            # 2. Déplacer R -> S (Preuve)
            # Si S est vide ou contient déjà la même chose, on écrase avec R (qui est la nouvelle preuve IA)
            # Si S a déjà une preuve différente, on peut envisager de concaténer, mais ici R est le résultat frais de l'IA.
            if r_val:
                new_s = r_val
                if s_val and s_val != r_val:
                    new_s = f"{s_val} | {r_val}"
                cells_to_update.append(gspread.Cell(row=row_num, col=19, value=new_s))
            
            # 3. Vider Q (Evaluation site)
            cells_to_update.append(gspread.Cell(row=row_num, col=17, value=""))
            fixed_count += 1
            
    if cells_to_update:
        print(f"Correction de {fixed_count} lignes (envoi de {len(cells_to_update)} cellules)...")
        # Envoi par lots de 500 cellules pour éviter les timeouts
        batch_size = 500
        for i in range(0, len(cells_to_update), batch_size):
            batch = cells_to_update[i:i+batch_size]
            ws.update_cells(batch)
            print(f"  Batch {i//batch_size + 1} envoyé.")
            time.sleep(1)
        print("✅ Correction terminée.")
    else:
        print("Aucune ligne à corriger.")

if __name__ == "__main__":
    surgical_fix_shift()
