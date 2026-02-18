import os
import sys
import pandas as pd
from datetime import datetime

# Ajout du chemin pour importer les modules du core
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.core.pipeline import Config, DataManager, VectorEngine, Brain, fetch_dynamic_context
import mlflow

def run_deep_scan():
    """
    Pipeline de scan approfondi (Deep Scan) :
    - Pas de limite de date (Période: Baseline)
    - Jusqu'à 50 résultats par mot-clé
    - Focus sur la reconstruction d'un historique complet
    """
    # Override de la config pour le scan profond
    Config.SEARCH_PERIOD = None  # Pas de limite de temps
    Config.SEARCH_MAX_RESULTS = 50 
    Config.RUN_FULL_AUDIT = True
    
    print(f"\n🚀 >>> LANCEMENT SCAN HISTORIQUE PROFOND (Cible: {Config.SEARCH_MAX_RESULTS} rêsultats/mot-clé) <<<")
    
    if not os.path.exists(Config.CREDENTIALS_FILE):
        print("❌ Erreur: credentials.json manquant.")
        return

    # 1. Chargement Contexte
    dynamic_context = fetch_dynamic_context(Config.CONTEXT_DOC_ID)
    if dynamic_context:
        # On injecte le contexte dans le module brain_new si nécessaire (il le lit déjà via Config)
        print("   > Contexte chargé depuis Google Doc.")
    
    # 2. Initialisation des moteurs
    dm, ve = DataManager(), VectorEngine()
    # Utilisation du modèle Gemini 3 Pro pour le scan historique profond
    brain = Brain(context=dynamic_context if dynamic_context else CONTEXTE_ENTREPRISE, 
                  model_name='models/gemini-3-pro-preview')
    df_base, conf = dm.load_data()
    
    # Création des sets pour déduplication
    existing_urls = set(df_base['url'].astype(str).tolist())
    existing_titles = set(df_base['titre'].astype(str).tolist())
    
    # 3. MLflow Tracking
    mlflow.set_experiment("Veille_Historique_Profond")
    with mlflow.start_run(run_name=f"Deep_Scan_{datetime.now().strftime('%d-%m_%Hh%M')}"):
        mlflow.log_params({
            "mode": "Deep Historical",
            "max_results_per_k": Config.SEARCH_MAX_RESULTS,
            "period": "All Time"
        })
        
        # 4. Génération de mots-clés exhaustifs
        print("   > Génération de mots-clés par l'IA...")
        keywords = brain.generate_keywords()
        print(f"   > {len(keywords)} thématiques identifiées.")
        
        report = []
        
        # 5. Boucle de scan intensif
        for k in keywords:
            print(f"\n   [🔍] Recherche intensive : {k}")
            res = brain.search(
                q=k, 
                num_results=Config.SEARCH_MAX_RESULTS,
                search_api_key=Config.SEARCH_API_KEY,
                search_engine_id=Config.SEARCH_ENGINE_ID,
                search_period=Config.SEARCH_PERIOD,
                tavily_api_key=Config.TAVILY_API_KEY
            )
            print(f"      -> {len(res)} résultats trouvés.")
            
            for r in res:
                if r['url'] in existing_urls or r['titre'] in existing_titles:
                    continue
                
                # Analyse de pertinence par l'IA
                print(f"      [?] Analyse : {r['titre'][:50]}...")
                ana = brain.analyze_news(f"{r['titre']} {r['snippet']}")
                
                if ana.get('criticite') in ['Haute', 'Moyenne']:
                    r.update(ana)
                    report.append(r)
                    print(f"         ✅ PERTINENT : {r['titre'][:60]}")
                    existing_urls.add(r['url'])
                    existing_titles.add(r['titre'])

        # 6. Sauvegarde et Clôture
        if report:
            print(f"\n--- Fin du Deep Scan : {len(report)} nouveaux textes identifiés ---")
            dm.save_report(pd.DataFrame(report))
            mlflow.log_metric("new_historical_texts", len(report))
            
            # Artifact: Listing complet
            summary = "\n".join([f"- {r['titre']} ({r['url']})" for r in report])
            mlflow.log_text(summary, "deep_scan_findings.txt")
        else:
            print("\n--- Deep Scan terminé : Aucun nouveau texte pertinent identifié ---")

if __name__ == "__main__":
    run_deep_scan()
