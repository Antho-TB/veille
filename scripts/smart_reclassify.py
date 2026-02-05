
import os
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import sys

# Ajouter le chemin racine pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.core.pipeline import Config

def smart_reclassify():
    print("--- 🧠 Smart Reclassification (Auditor Logic) ---")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(Config.SHEET_ID)
    ws = sheet.worksheet('Base_Active')
    
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    
    # Normalisation des noms de colonnes (robuste)
    cols = df.columns.tolist()
    title_col = [c for c in cols if 'Intitulé' in c or 'Titre' in c][0]
    comment_col = [c for c in cols if 'Commentaires' in c][0]
    crit_col = [c for c in cols if 'Criticité' in c][0]
    
    print(f"   > Colonnes détectées : Titre='{title_col}', Comment='{comment_col}', Crit='{crit_col}'")
    print(f"   > Analyse de {len(df)} lignes...")

    # Grille de mots-clés
    HAUTE_KEYWORDS = [
        "arrêté préfectoral", "vle", "v.l.e", "valeur limite", "rejet", "seuil",
        "icpe 2561", "icpe 2564", "icpe 2565", "icpe 2560", "sanction", "pénal",
        "reach", "rohs", "interdiction", "amende", "mise en demeure"
    ]
    
    MOYENNE_KEYWORDS = [
        "rep ", "loi agec", "responsabilité élargie", "registre", "bsd", "trackdechets",
        "rndts", "déclaration", "tri ", "audit périodique", "fluide frigorigène",
        "contrôle technique", "périodicité", "formation", "affichage"
    ]

    cells_to_update = []
    headers = ws.row_values(1)
    # On cherche l'index exact dans le Google Sheet (1-based)
    crit_idx = headers.index(crit_col) + 1
    
    updates = 0
    for i, row in df.iterrows():
        text_to_scan = (str(row[title_col]) + " " + str(row[comment_col])).lower()
        
        new_crit = "Basse" # Par défaut
        
        # Test MOYENNE
        if any(k in text_to_scan for k in MOYENNE_KEYWORDS):
            new_crit = "Moyenne"
            
        # Test HAUTE (écrase Moyenne)
        if any(k in text_to_scan for k in HAUTE_KEYWORDS):
            new_crit = "Haute"
            
        cells_to_update.append(gspread.Cell(row=i+2, col=crit_idx, value=new_crit))
        updates += 1

    if cells_to_update:
        print(f"   > Envoi de {len(cells_to_update)} mises à jour vers Google Sheets...")
        for j in range(0, len(cells_to_update), 500):
            ws.update_cells(cells_to_update[j:j+500])
        print("✅ Reclassification terminée.")

if __name__ == "__main__":
    smart_reclassify()
