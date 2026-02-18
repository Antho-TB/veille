import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys

# Ajouter la racine du projet au path
sys.path.append(os.getcwd())
from src.core.pipeline import Config

def check_stats():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(Config.SHEET_ID)
    ws = sheet.worksheet('Base_Active')
    
    data = ws.get_all_records()
    print(f"Total rows with records: {len(data)}")
    
    crit_counts = {}
    status_counts = {}
    conformity_counts = {}
    
    # On affiche les headers pour être sûr
    headers = ws.row_values(1)
    print(f"Headers: {headers}")
    
    for r in data:
        # Recherche robuste des clés
        c = "MISSING"
        for k in ['Criticité', 'criticite', 'Crit']:
            if k in r and str(r[k]).strip():
                c = str(r[k]).strip()
                break
        crit_counts[c] = crit_counts.get(c, 0) + 1
        
        s = "MISSING"
        for k in ['Statut', 'statut']:
            if k in r and str(r[k]).strip():
                s = str(r[k]).strip()
                break
        status_counts[s] = status_counts.get(s, 0) + 1

        conf = str(r.get('Conformité', 'MISSING')).strip()
        conformity_counts[conf] = conformity_counts.get(conf, 0) + 1
        
    print("\nREPARTITION CRITICITE:", crit_counts)
    print("REPARTITION STATUT:", status_counts)
    print("REPARTITION CONFORMITE:", conformity_counts)

if __name__ == "__main__":
    check_stats()
