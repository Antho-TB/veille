import gspread
import pandas as pd
import os
import sys
import time
from oauth2client.service_account import ServiceAccountCredentials

# Ajouter la racine au path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from src.core.pipeline import Config, Brain, extract_json

class DataEnricher:
    def __init__(self):
        self.client = None
        self.brain = Brain()

    def connect(self):
        if not os.path.exists(Config.CREDENTIALS_FILE):
            raise FileNotFoundError(f"Fichier credentials.json manquant à l'emplacement : {Config.CREDENTIALS_FILE}")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope))

    def enrich_sheet(self, sheet_name):
        print(f"--- Enrichissement de : {sheet_name} ---")
        if not self.client: self.connect()
        
        sheet = self.client.open_by_key(Config.SHEET_ID)
        try:
            ws = sheet.worksheet(sheet_name)
        except:
            print(f"Onglet {sheet_name} introuvable.")
            return

        # On récupère tout
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        df.columns = [c.strip() for c in df.columns]
        
        header = ws.row_values(1)
        
        # Identification des colonnes cibles
        comment_col = "Commentaires"
        proof_col = "Preuve de Conformité Attendue"
        
        if comment_col not in df.columns:
            # Fallback sur Commentaires (ALSAPE...)
            comment_col = next((c for c in df.columns if "Commentaires" in c), None)
            
        if proof_col not in header:
            print(f"➕ Ajout de la colonne '{proof_col}'...")
            ws.update_cell(1, len(header) + 1, proof_col)
            header.append(proof_col)
            df[proof_col] = "" # Ajouter à la DF locale

        try:
            comment_idx = header.index(comment_col) + 1
            proof_idx = header.index(proof_col) + 1
        except Exception as e:
            print(f"❌ Erreur colonnes : {e}")
            return

        updates = 0
        
        for idx, row in df.iterrows():
            titre = str(row.get('Intitulé', row.get('Intitulé ', ''))).strip()
            action = str(row.get(comment_col, '')).strip()
            preuve = str(row.get(proof_col, '')).strip()
            
            # Condition 1 : Action manquante
            need_action = titre and (not action or action.lower() in ["aucune action spécifiée", "titre manquant", "nan", ""])
            
            # Condition 2 : Preuve manquante (Nouveau !)
            need_proof = titre and (not preuve or preuve.lower() in ["non spécifiée", "nan", ""])
            
            if need_action or need_proof:
                print(f"   > 🔍 Analyse IA pour ligne {idx+2} : {titre[:40]}...")
                
                # Appel IA (utilise analyze_news qui renvoie un dict avec D-C-P)
                analysis = self.brain.analyze_news(titre)
                
                if analysis.get('criticite') == "Non":
                    continue

                if need_action:
                    new_action = f"{analysis.get('resume', '')} (Action: {analysis.get('action', '')})"
                    if len(new_action) > 10:
                        ws.update_cell(idx + 2, comment_idx, new_action)
                        print(f"      ✅ Action mise à jour")
                        updates += 1
                
                if need_proof:
                    new_proof = analysis.get('preuve_attendue', '')
                    if len(new_proof) > 5:
                        ws.update_cell(idx + 2, proof_idx, new_proof)
                        print(f"      ✅ Preuve mise à jour")
                        updates += 1
                
                time.sleep(1.2) # Quota

        print(f"--- FIN : {updates} mises à jour effectuées ---")

if __name__ == "__main__":
    enricher = DataEnricher()
    # On peut restreindre si besoin, ici on traite tout
    enricher.enrich_sheet('Base_Active')
    enricher.enrich_sheet('Rapport_Veille_Auto')
