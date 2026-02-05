import os
import time
import pandas as pd
import gspread
import google.generativeai as genai
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import sys

# Ajouter le chemin racine pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from src.core.pipeline import Config, fetch_dynamic_context

class AIJustifier:
    def __init__(self):
        self.client = None
        self.model = None
        
    def connect(self):
        # Configuration Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
        self.client = gspread.authorize(creds)
        
        # Configuration Gemini
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def get_data(self, sheet_name):
        sheet = self.client.open_by_key(Config.SHEET_ID)
        ws = sheet.worksheet(sheet_name)
        return pd.DataFrame(ws.get_all_records())

    def justify(self, row, context):
        titre = row.get('Intitulé ', row.get('Intitulé', 'Inconnu'))
        theme = row.get('Thème', 'Inconnu')
        action_resume = row.get('Commentaires', '')
        
        prompt = f"""
        Rôle : Auditeur Certification ISO 14001 pour GDD (Générale de Découpage).
        
        Mission : Analyser ce texte et justifier la conformité selon la structure D-C-P.
        
        CONTEXTE GDD :
        {context}
        
        TEXTE RÉGLEMENTAIRE :
        - Titre : {titre}
        - Thème : {theme}
        - Résumé actuel : {action_resume}
        
        CONSIGNES DE RÉDACTION STRICTES :
        1. Justification D-C-P :
           - Donnée d'entrée : Activité ou aspect de GDD concerné.
           - Critère Réglementaire : Seuil ou exigence spécifique.
           - Preuve attendue : Document ou preuve physique (ex: FDS, Bon d'enlèvement, rapport).
        
        2. Format : Réponse DIRECTE sans introduction (pas de "Okay", "Voici", etc.).
        Structure : "Concerné par [Donnée] car [Critère]. Preuve de conformité : [Preuve]."
        """
        try:
            resp = self.model.generate_content(prompt)
            return resp.text.strip()
        except Exception as e:
            return f"Erreur IA : {str(e)}"

    def run_prototype(self, limit=None):
        print(f"--- Justifications IA ---")
        self.connect()
        
        # 1. Charger le contexte dynamique
        context = fetch_dynamic_context(Config.CONTEXT_DOC_ID)
        if not context:
            context = "GDD est un spécialiste du découpage et de l'emboutissage (métaux), certifié ISO 14001, soumis aux rubriques ICPE 2560, 2561, 2564, 2565."

        # 2. Charger les données de la Base Active
        df = self.get_data('Base_Active')
        if df.empty:
            print("Base Active vide.")
            return

        total_rows = len(df) if limit is None else min(limit, len(df))
        sample = df.head(total_rows)
        
        # 3. Gérer l'onglet Justifications (Récupérer l'existant pour reprise)
        sheet = self.client.open_by_key(Config.SHEET_ID)
        try:
            ws_justif = sheet.worksheet('Justifications')
            print(f"♻️  Nouveau modèle DCP détecté. Régénération complète demandée.")
            processed_titles = set()
            results = []
        except:
            ws_justif = sheet.add_worksheet('Justifications', 2000, 10)
            processed_titles = set()
            results = []

        # 4. Boucle de génération avec sauvegarde périodique
        count = 0
        try:
            for i, row in sample.iterrows():
                titre = row.get('Intitulé ', row.get('Intitulé', ''))
                if titre in processed_titles:
                    continue
                
                print(f"   > Analyse [{i+1}/{total_rows}] : {titre[:50]}...")
                justification = self.justify(row, context)
                results.append({
                    'Date de génération': datetime.now().strftime("%d/%m/%Y"),
                    'Titre du texte': titre,
                    'Thème': row.get('Thème', ''),
                    'Justification Proposée (IA)': justification
                })
                processed_titles.add(titre)
                count += 1
                
                # Sauvegarde toutes les 20 lignes
                if count % 20 == 0:
                    print("   [SAVE] Sauvegarde intermédiaire du travail...")
                    df_res = pd.DataFrame(results)
                    ws_justif.update([df_res.columns.values.tolist()] + df_res.values.tolist())
                
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n⚠️ Interruption détectée. Sauvegarde finale...")
        except Exception as e:
            print(f"\n❌ Erreur : {e}. Sauvegarde finale...")
        finally:
            if results:
                df_res = pd.DataFrame(results)
                ws_justif.update([df_res.columns.values.tolist()] + df_res.values.tolist())
                print(f"--- ✅ TERMINÉ : {len(results)} lignes totales dans 'Justifications' ---")

if __name__ == "__main__":
    justifier = AIJustifier()
    # On traite toute la base
    justifier.run_prototype(limit=None)
