import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import pandas as pd
import time

# Configuration
SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "../config/credentials.json")

THEME_MAPPING = {
    "EAU": ["eau", "effluent", "pluvial", "assainissement", "rivière", "nappe"],
    "DÉCHETS": ["déchet", "ordure", "tri", "recyclage", "amiante", "danois", "rep", "emballage"],
    "AIR / ATMOSPHÈRE": ["air", "émission", "gaz", "poussière", "odeur", "climat", "carbone"],
    "SOLS / SITES POLLUÉS": ["sol", "pollution", "excavation", "site délaissé", "sous-sol"],
    "ÉNERGIE": ["énergie", "électricité", "gaz de ville", "solaire", "photovoltaïque", "facture", "isolation"],
    "SÉCURITÉ": ["sécurité", "incendie", "extincteur", "évacuation", "ateliers", "bruit", "vibration"],
    "ICPE": ["icpe", "2560", "2564", "rubrique", "arrêté préfectoral", "dreal"],
    "MANAGEMENT / ISO": ["iso", "audit", "management", "qualité", "procédure", "stratégie"],
    "BIODIVERSITÉ": ["faune", "flore", "espèce", "nature", "forêt", "arbre"]
}

GRAND_THEME_MAPPING = {
    "ENVIRONNEMENT": ["EAU", "DÉCHETS", "AIR / ATMOSPHÈRE", "SOLS / SITES POLLUÉS", "BIODIVERSITÉ", "SÉCURITÉ"],
    "GOUVERNANCE": ["MANAGEMENT / ISO", "STRATÉGIE", "AUDIT"],
    "RESSOURCES": ["ÉNERGIE", "MATIÈRES PREMIÈRES"]
}

def smart_reclassify():
    print("--- [SMART RECLASSIFY] Reclassification rapide par mots-clés ---")
    
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        ss = client.open_by_key(SHEET_ID)
        
        for ws_name in ['Base_Active', 'Rapport_Veille_Auto']:
            print(f"\n> Traitement de : {ws_name}")
            ws = ss.worksheet(ws_name)
            data = ws.get_all_records()
            if not data: continue
            
            header = ws.row_values(1)
            col_theme = -1
            col_grand = -1
            col_titre = -1
            
            for i, h in enumerate(header):
                h_low = h.lower().strip()
                if 'thème' == h_low or 'theme' == h_low: col_theme = i + 1
                if 'grand thème' == h_low: col_grand = i + 1
                if 'intitulé' in h_low: col_titre = i + 1
            
            if col_theme == -1 or col_titre == -1:
                print(f"   ⚠️ Colonnes Thème ou Intitulé introuvables sur {ws_name}")
                continue

            cells_to_update = []
            modified = 0
            for row_idx, row in enumerate(data):
                real_idx = row_idx + 2
                titre = str(row.get(header[col_titre-1], '')).lower()
                current_theme = str(row.get(header[col_theme-1], '')).strip()
                current_grand = str(row.get(header[col_grand-1], '')) if col_grand != -1 else ""

                updated_this_row = False
                if not current_theme or current_theme in ['-', 'N/A', 'Divers', 'DIVERS']:
                    # Tentative de matching Thème
                    new_theme = None
                    for theme, keywords in THEME_MAPPING.items():
                        if any(k in titre for k in keywords):
                            new_theme = theme
                            break
                    
                    if new_theme:
                        cells_to_update.append(gspread.Cell(row=real_idx, col=col_theme, value=new_theme))
                        print(f"   [BATCH] Ligne {real_idx}: Thème -> {new_theme}")
                        modified += 1
                        current_theme = new_theme
                        updated_this_row = True
                
                if col_grand != -1 and (not current_grand or current_grand in ['-', 'N/A']):
                    # Tentative de matching Grand Thème basé sur le Thème
                    new_grand = None
                    for grand, themes in GRAND_THEME_MAPPING.items():
                        if current_theme in themes:
                            new_grand = grand
                            break
                    
                    if new_grand:
                        cells_to_update.append(gspread.Cell(row=real_idx, col=col_grand, value=new_grand))
                        print(f"   [BATCH] Ligne {real_idx}: Grand Thème -> {new_grand}")
                        modified += 1
                        updated_this_row = True

            if cells_to_update:
                print(f"   > Envoi de {len(cells_to_update)} mises à jour en un seul lot...")
                ws.update_cells(cells_to_update, value_input_option='USER_ENTERED')
                print(f"   ✅ {ws_name} mis à jour.")
            else:
                print(f"   ✅ {ws_name}: Aucune mise à jour nécessaire.")
            
            time.sleep(5) # Pause entre les onglets pour laisser reposer le quota

    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    smart_reclassify()
