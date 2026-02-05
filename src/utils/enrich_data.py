# ---------------------------------------------------------------------------
# Outil d'Enrichissement - Veille Réglementaire
# ---------------------------------------------------------------------------
# Ce script parcourt la Base Active et le Rapport pour :
# 1. Identifier les textes qui ont un titre mais PAS d'action/commentaire.
# 2. Utiliser l'IA (Gemini) pour générer une analyse contextuelle (GDD).
# 3. Mettre à jour le Google Sheet automatiquement.
# ---------------------------------------------------------------------------

import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from pipeline_veille import Config, Brain, CONTEXTE_ENTREPRISE, extract_json
import time

class DataEnricher:
    def __init__(self):
        self.client = None
        self.brain = Brain()

    def connect(self):
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
        
        # Normalisation des colonnes pour éviter les erreurs d'espaces
        df.columns = [c.strip() for c in df.columns]
        
        # Vérification des colonnes nécessaires
        if 'Intitulé' not in df.columns or 'Commentaires' not in df.columns:
            print("Colonnes 'Intitulé' ou 'Commentaires' manquantes.")
            return

        updates = 0
        
        # On itère sur les lignes (attention l'index DF commence à 0, Sheet à 2)
        for idx, row in df.iterrows():
            titre = str(row.get('Intitulé', '')).strip()
            action = str(row.get('Commentaires', '')).strip()
            
            # Condition : Titre présent MAIS Action vide (ou générique)
            if titre and (not action or action.lower() in ["aucune action spécifiée", "titre manquant"]):
                print(f"   > 🔍 Analyse IA pour ligne {idx+2} : {titre[:50]}...")
                
                # Appel IA
                analysis = self.brain.analyze_news(titre)
                
                # Construction du commentaire enrichi
                new_action = f"{analysis.get('resume', '')} (Action: {analysis.get('action', '')})"
                
                if len(new_action) > 20: # Si l'IA a renvoyé quelque chose de consistant
                    # Mise à jour dans le Sheet
                    # On doit trouver la colonne 'Commentaires' (ou 'Commentaires (ALSAPE...)')
                    # Ici on suppose que la colonne cible est 'Commentaires'
                    
                    # On cherche l'index de la colonne 'Commentaires' dans le header original
                    # Attention : gspread utilise des coordonnées (row, col) 1-based
                    try:
                        col_idx = ws.find("Commentaires").col
                        ws.update_cell(idx + 2, col_idx, new_action)
                        print(f"      ✅ Mis à jour : {new_action[:60]}...")
                        updates += 1
                        time.sleep(1.5) # Pause pour quota API
                    except Exception as e:
                        print(f"      ❌ Erreur update : {e}")
                else:
                    print("      ⚠️ L'IA n'a pas renvoyé de résultat pertinent.")

        if updates == 0:
            print("   > Aucune ligne à enrichir.")
        else:
            print(f"   > {updates} lignes enrichies avec succès.")

if __name__ == "__main__":
    enricher = DataEnricher()
    # On enrichit la Base Active en priorité
    enricher.enrich_sheet('Base_Active')
    # Puis le rapport
    enricher.enrich_sheet('Rapport_Veille_Auto')
