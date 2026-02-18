import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json

# Configuration
SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "../config/credentials.json")

def debug_shift():
    print("--- [DEBUG] Analyse du décalage des colonnes (1-100) ---")
    
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        ss = client.open_by_key(SHEET_ID)
        ws = ss.worksheet("Rapport_Veille_Auto")
        
        rows = ws.get_all_values()[:100]
        header = rows[0]
        
        print(f"Index des colonnes :")
        for i, h in enumerate(header):
            print(f"  {i}: {h}")

        print("-" * 120)
        print(f"{'Ligne':<6} | {'J (Lien)':<20} | {'K (Statut)':<15} | {'L (Conf)':<15} | {'M (Delai)':<20} | {'N (Comm)':<20}")
        print("-" * 120)
        
        for i, row in enumerate(rows[1:]):
            idx = i + 2
            j = row[9] if len(row) > 9 else ""
            k = row[10] if len(row) > 10 else ""
            l = row[11] if len(row) > 11 else ""
            m = row[12] if len(row) > 12 else ""
            n = row[13] if len(row) > 13 else ""
            
            # On affiche focus sur 30-35
            show = (30 <= idx <= 35) or (idx % 10 == 0)
            
            if show:
                print(f"{idx:<6} | {j[:20]:<20} | {k:<15} | {l:<15} | {m[:20]:<20} | {n[:20]:<20}")

    except Exception as e:
        print(f"❌ Erreur : {e}")

    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    debug_shift()
