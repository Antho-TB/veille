"""
=============================================================================
MODULE DE RÉÉVALUATION AUTOMATIQUE - VEILLE GDD
=============================================================================

Ce script permet de vérifier périodiquement si les textes de la 'Base Active'
sont toujours sous contrôle. 

Règles Métier GDD :
1. Réévaluation tous les 3 ans par défaut.
2. Vérification automatique : si les 'preuves attendues' sont mentionnées dans
   la fiche d'identité (contexte), le statut passe en 'Conforme'.
3. Repli : si l'IA doute, elle propose une action concrète à l'équipe.

"""

import pandas as pd
from datetime import datetime, timedelta
from src.core.config_manager import Config
from src.core.brain_new import Brain
from src.utils.data_manager import DataManager

class ReEvaluator:
    def __init__(self):
        self.dm = DataManager()
        self.brain = None # Sera initialise avec le contexte complet
        
    def run_reevaluation(self):
        """Lance le scan de la Base Active pour reevaluer les lignes obsoletes"""
        print("--- [ReEvaluation] Scan de la Base Active en cours ---")
        
        # 1. Chargement des donnees
        df, _ = self.dm.load_data()
        if df.empty: return
        
        # On ne garde que les textes de la base active (ceux qui ont une date de prochaine evaluation)
        # Junior Tip : On convertit les dates pour pouvoir faire des calculs
        df['next_eval'] = pd.to_datetime(df['date de la prochaine évaluation'], errors='coerce')
        today = datetime.now()
        
        # Filtre : Texte dont la date d'evaluation est depassee ou absente
        mask_to_eval = (df['next_eval'].isna()) | (df['next_eval'] <= today)
        df_to_process = df[mask_to_eval].copy()
        
        if df_to_process.empty:
            print("      > Tout est a jour. Aucune reevaluation necessaire.")
            return

        print(f"      > {len(df_to_process)} textes a reevaluer.")
        
        # 2. Initialisation du cerveau avec le contexte Google Doc
        # On importe la fonction de pipeline pour eviter la duplication
        from src.core.pipeline import fetch_dynamic_context
        context = fetch_dynamic_context(Config.CONTEXT_DOC_ID)
        self.brain = Brain(context=context)
        
        results = []
        for _, row in df_to_process.iterrows():
            res = self._evaluate_row(row)
            results.append(res)
            
        # 3. Mise a jour (Simulation ou sauvegarde directe selon besoin)
        print("✅ Scan de reevaluation termine.")
        return results

    def _evaluate_row(self, row):
        """Evalue une ligne specifique via l'IA"""
        titre = row.get('titre', 'Texte inconnu')
        preuve = row.get('Preuve de Conformité Attendue', '')
        
        print(f"      [IA] Analyse de : {titre[:50]}...")
        
        prompt = f"""
        Expert Conformite GDD. 
        CONTEXTE USINE : {self.brain.context}
        TEXTE A EVALUER : {titre}
        PREUVE ATTENDUE : {preuve}
        
        MISSION :
        Verifie si la preuve attendue est deja presente ou decrite dans le contexte usine.
        - Si OUI : Statut = 'Conforme'.
        - Si DOUTE : Statut = 'A verifier' et propose une ACTION CONCRETE (ex: "Verifier le registre des dechets 2024").
        
        Reponds en JSON : {{"conformite": "Conforme/A verifier", "action_proposee": "..."}}
        """
        
        try:
            resp = self.brain.model.generate_content(prompt)
            data = self.brain._extract_json(resp.text)
            
            # Calcul de la prochaine date (+3 ans)
            next_date = (datetime.now() + timedelta(days=3*365)).strftime("%d/%m/%Y")
            
            return {
                "titre": titre,
                "conformite": data.get('conformite', 'A verifier'),
                "action": data.get('action_proposee', 'Revue manuelle requise'),
                "prochaine_eval": next_date
            }
        except:
            return {"titre": titre, "conformite": "Erreur", "action": "Echec IA"}

if __name__ == "__main__":
    rev = ReEvaluator()
    rev.run_reevaluation()
