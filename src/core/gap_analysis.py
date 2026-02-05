import os
import sys
import pandas as pd
import gspread
import google.generativeai as genai
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Ajouter la racine du projet au path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from src.core.pipeline import Config, fetch_dynamic_context

class GapAnalyzer:
    def __init__(self):
        self.client = None
        # RECOMMANDATION : Utiliser un modèle PRO pour l'audit de complétude (Grande fenêtre de contexte)
        # On utilise gemini-1.5-pro ou gemini-2.0-pro si disponible
        self.model_name = 'gemini-1.5-pro' 
        self.model = None

    def connect(self):
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
        self.client = gspread.authorize(creds)
        genai.configure(api_key=Config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(self.model_name)

    def run_audit(self):
        print(f"🕵️ Démarrage de l'Audit de Complétude Mensuel ({self.model_name})...")
        self.connect()
        
        # 1. Charger contexte GDD
        context = fetch_dynamic_context(Config.CONTEXT_DOC_ID)
        
        # 2. Charger toute la Base Active
        sheet = self.client.open_by_key(Config.SHEET_ID)
        ws_base = sheet.worksheet("Base_Active")
        df_base = pd.DataFrame(ws_base.get_all_records())
        
        # 3. Préparer la liste des titres existants (pour éviter les doublons)
        existing_titles = "\n".join(df_base['Intitulé'].astype(str).tolist())
        
        # 4. Prompt d'Audit Massif
        prompt = f"""
        Rôle : Auditeur Expert QHSE pour certification ISO 14001.
        Objectif : Effectuer un gap analysis complet de la base réglementaire de l'entreprise GDD.
        
        CONTEXTE GDD :
        {context}
        
        BASE RÉGLEMENTAIRE ACTUELLE (Titres) :
        {existing_titles}
        
        MISSION :
        En te basant sur tes connaissances approfondies du droit de l'environnement industriel français (ICPE, Déchets, Eau, Air, RSE), identifie les TEXTES RÉGLEMENTAIRES MAJEURS qui manqueraient à cette base pour assurer une conformité totale.
        
        CONSIGNES :
        - Ne cite que des textes OFFICIELS (Lois, Décrets, Arrêtés).
        - Focus sur le découpage métaux, rubriques ICPE 2560+, et nouvelles obligations 2024-2025.
        - Cite maximum 5 textes prioritaires manquants.
        
        FORMAT DE RÉPONSE (JSON STRICT) :
        [
            {{
                "titre": "...",
                "theme": "...",
                "criticite": "Haute",
                "manque_justification": "Expliquer pourquoi ce texte est vital pour GDD",
                "action": "Ajouter à la base et évaluer"
            }}
        ]
        """
        
        try:
            print("   > Analyse en cours (cela peut prendre 1-2 minutes)...")
            resp = self.model.generate_content(prompt)
            from src.core.pipeline import extract_json
            missing_texts = extract_json(resp.text)
            
            if missing_texts:
                print(f"   > ✅ Audit terminé. {len(missing_texts)} textes manquants identifiés.")
                # Optionnel : Enregistrer dans un onglet "Audit_Gap"
                try:
                    ws_audit = sheet.worksheet("Audit_Gap")
                except:
                    ws_audit = sheet.add_worksheet("Audit_Gap", 100, 10)
                    ws_audit.append_row(["Date Audit", "Titre Manquant", "Thème", "Criticité", "Justification", "Action"])
                
                rows_to_add = []
                for m in missing_texts:
                    rows_to_add.append([
                        datetime.now().strftime("%d/%m/%Y"),
                        m.get('titre'), m.get('theme'), m.get('criticite'),
                        m.get('manque_justification'), m.get('action')
                    ])
                ws_audit.append_rows(rows_to_add)
                print("   > 📊 Résultats enregistrés dans l'onglet 'Audit_Gap'.")
            else:
                print("   > ✨ Aucun manque majeur identifié par l'IA.")
                
        except Exception as e:
            print(f"❌ Erreur lors de l'audit : {e}")

if __name__ == "__main__":
    analyzer = GapAnalyzer()
    analyzer.run_audit()
