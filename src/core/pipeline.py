"""
=============================================================================
PIPELINE DE VEILLE RÉGLEMENTAIRE AUTOMATISÉE - GDD
=============================================================================

Ce script est le chef d'orchestre de l'application. 
Il coordonne la recherche, l'analyse et la sauvegarde des nouvelles 
obligations réglementaires pour l'usine GDD (Générale de Découpage).

En tant que développeur Junior, ce script vous montre comment structurer 
une application "Data-Driven" (pilotée par les données) en utilisant 
des modules séparés pour plus de clarté.

Étapes principales :
1. Initialisation de l'IA et connexion aux données.
2. Recherche Web (Google / Tavily).
3. Filtrage de pertinence par l'IA Gemini.
4. Historisation et mise à jour du Dashboard.

"""

import os
import time
import pandas as pd
import mlflow
from datetime import datetime

# Importation de nos propres modules (Modulisation Senior)
from src.core.config_manager import Config
from src.core.brain_new import Brain
from src.utils.data_manager import DataManager
from src.utils.vector_engine import VectorEngine
from src.utils.drive_uploader import run_upload
from src.utils.azure_uploader import run_azure_upload
from src.mcp.mcp_client import get_mcp_results

# Configuration de MLflow pour le suivi des expériences
# Junior Tip : MLflow permet de garder une trace de chaque exécution (le "Run")
# mlflow.set_experiment("Veille_QHSE_Production") # Déplacé dans run_pipeline()

import re
import json

def sanitize_name(name):
    """Nettoie une chaîne pour être compatible avec MLflow"""
    return re.sub(r'[^a-zA-Z0-9_\-\.\ \/]', '_', name)

def extract_json(text):
    """Extrait un bloc JSON d'un texte brut (IA)"""
    try:
        # Recherche d'une liste JSON
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        # Recherche d'un objet JSON unique
        match = re.search(r'\{\s*".*"\s*:.*\}', text, re.DOTALL)
        if match:
            obj = json.loads(match.group(0))
            return [obj] if isinstance(obj, dict) else obj
        return []
    except:
        return []

def fetch_google_doc_text(doc_id):
    """
    Recupere le texte brut d'un document Google Docs.
    Utilise l'API Google Docs v1 pour extraire le contenu structurellement.
    """
    try:
        from googleapiclient.discovery import build
        from oauth2client.service_account import ServiceAccountCredentials
        
        # Junior Tip : Google Docs a son propre scope d'autorisation
        scopes = ["https://www.googleapis.com/auth/documents.readonly"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scopes)
        service = build('docs', 'v1', credentials=creds)
        
        doc = service.documents().get(documentId=doc_id).execute()
        content = doc.get('body').get('content')
        
        full_text = ""
        for element in content:
            if 'paragraph' in element:
                elements = element.get('paragraph').get('elements')
                for el in elements:
                    if 'textRun' in el:
                        full_text += el.get('textRun').get('content')
        return full_text
    except Exception as e:
        print(f"      [!] Erreur lecture Google Doc ({doc_id}) : {e}")
        return None

def fetch_dynamic_context(doc_id):
    """
    Recupere le contexte dynamique de l'usine GDD.
    Tente de lire le Google Doc (Fiche d'identite), puis se rabat sur le Sheet si echec.
    """
    print(f"--- [Pipeline] Recuperation du contexte GDD ({doc_id}) ---")
    
    # Tentative 1 : Google Doc (Nouveau standard GDD)
    context_text = fetch_google_doc_text(doc_id)
    if context_text and len(context_text.strip()) > 100:
        print("      > Contexte extrait avec succes depuis Google Docs.")
        return context_text
    
    # Tentative 2 : Fallback sur l'ancien onglet 'Contexte_Site' du Google Sheet
    try:
        from src.utils.data_manager import DataManager
        dm = DataManager()
        if not dm.client: dm._connect()
        
        sheet = dm.client.open_by_key(Config.SHEET_ID)
        try:
            ws = sheet.worksheet("Contexte_Site")
            vals = ws.get_all_values()
            print("      > Contexte extrait depuis Google Sheets (Fallback).")
            return "\n".join([" ".join(row) for row in vals])
        except:
            # Junior Tip : Si tout echoue, on utilise une base metier solide
            return "GDD est une entreprise de decoupage-emboutissage certifiee ISO 14001, situee en France. Principaux risques : ICPE 2560, dechets, REACH, bruit, vibrations."
    except Exception as e:
        print(f"      [!] Erreur lors de la recuperation du contexte : {e}")
        return "Contexte industriel GDD par defaut."

def run_pipeline():
    """Fonction principale de pilotage du pipeline"""
    mlflow.set_experiment("Veille_QHSE_Production")
    print(f">>> LANCEMENT DU PIPELINE GDD (Mode: {Config.SEARCH_PERIOD}) <<<")
    
    # 1. INITIALISATION
    dm = DataManager()
    ve = VectorEngine()
    
    # On charge le contexte (ce qui définit l'usine) pour l'IA
    # On utilise d'abord le module Brain pour récupérer le contexte dynamique
    brain_setup = Brain(model_name=Config.MODEL_NAME)
    dynamic_context = fetch_dynamic_context(Config.CONTEXT_DOC_ID)
    
    contexte_final = dynamic_context if dynamic_context else "Contexte par défaut"
    brain = Brain(context=contexte_final, model_name=Config.MODEL_NAME)
    
    # 2. CHARGEMENT DES DONNÉES HISTORIQUES
    df_base, conf = dm.load_data()
    ve.index(df_base) # Indexation pour recherche sémantique
    
    existing_urls = set(df_base['url'].astype(str).tolist())
    existing_titles = set(df_base['titre'].astype(str).tolist())
    
    report = []
    
    # --- DÉMARRAGE DU RUN MLFLOW ---
    start_time = time.time()
    run_name = sanitize_name(f"Scan_{datetime.now().strftime('%d-%m_%Hh%M')}")
    
    with mlflow.start_run(run_name=run_name) as parent_run:
        mlflow.log_params({
            "search_period": Config.SEARCH_PERIOD,
            "full_audit": Config.RUN_FULL_AUDIT,
            "model_name": Config.MODEL_NAME
        })

        # 3. AUDIT DES MANQUES (GAP ANALYSIS)
        if Config.RUN_FULL_AUDIT:
            print("--- [1/3] Audit de complétude (Gap Analysis) ---")
            manquants = brain.audit_manquants(df_base['titre'].astype(str).tolist())
            for m in manquants:
                if m.get('titre') in existing_titles: continue
                report.append(m)
                print(f"      [!] Manque détecté : {m.get('titre', 'N/A')}")

        # 4. VEILLE OFFICIELLE (MCP) & VEILLE WEB (GOOGLE)
        print(f"--- [2/3] Recherche d'Informations ({Config.SEARCH_PERIOD}) ---")
        keywords = conf['keywords'].tolist() if 'keywords' in conf.columns else []
        if not keywords:
            keywords = brain.generate_keywords()
            
        total_scanned = 0
        findings = 0
        
        # PLAN A : Sources Officielles via Serveur MCP Maison (Legifrance, Data.gouv, Ineris)
        print("\n   >>> PLAN A : Interrogation des sources officielles (Serveur MCP GDD)...")
        mcp_results = get_mcp_results(keywords[:5]) # On limite pour ne pas saturer l'API
        total_mcp = len(mcp_results)
        print(f"   >>> {total_mcp} résultats bruts obtenus des sources officielles.\n")
        
        # PLAN B : Recherche Web Google (Élargissement)
        print("   >>> PLAN B : Interrogation du Web (Google/Tavily)...")
        
        for k in keywords[:10]: # On limite à 10 mots clés max
            if not k: continue
            print(f"   > Mot-clé : {k}")
            
            # Récupérer les résultats web
            web_results = brain.search(
                q=k, 
                num_results=Config.SEARCH_MAX_RESULTS,
                search_api_key=Config.SEARCH_API_KEY,
                search_engine_id=Config.SEARCH_ENGINE_ID,
                search_period=Config.SEARCH_PERIOD,
                tavily_api_key=Config.TAVILY_API_KEY
            )
            
            # Fusionner MCP et Web pour ce mot-clé
            all_results = [r for r in mcp_results if k in r.get('titre', '')] + web_results
            total_scanned += len(all_results)
            
            for r in all_results:
                # Déduplication Exacte
                if r['url'] in existing_urls or r['titre'] in existing_titles:
                    continue
                
                # Déduplication Sémantique (ChromaDB VectorEngine)
                # Junior Tip : On concatene le titre et le snippet pour avoir un contexte max
                if ve.is_duplicate(f"{r['titre']} {r.get('snippet', '')}"):
                    print(f"      [-] Ignoré (Doublon Sémantique) : {r['titre'][:40]}...")
                    continue
                
                # Analyse IA de la pertinence
                ana = brain.analyze_news(f"{r['titre']} {r['snippet']}")
                if ana.get('criticite') in ['Haute', 'Moyenne']:
                    findings += 1
                    r.update(ana)
                    report.append(r)
                    print(f"      [+] Pertinent : {r['titre'][:50]}...")
                    existing_urls.add(r['url'])
            
            time.sleep(1) # Politesse pour les APIs

        # 5. FINALISATION ET SAUVEGARDE
        print("--- [3/3] Finalisation et mise à jour Dashboard ---")
        mlflow.log_metrics({
            "total_web_result": total_scanned,
            "nb_new_rows": len(report),
            "duration_second": time.time() - start_time
        })
        
        # --- ECRITURE GOOGLE SHEETS HISTORIQUE ---
        dm.save_historique({
            "Date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Modèle IA": Config.MODEL_NAME,
            "Mode Recherche": Config.SEARCH_PERIOD,
            "Textes Scannés": total_scanned,
            "Nouveautés Ajoutées": len(report),
            "Durée (s)": time.time() - start_time
        })
        
        if report:
            dm.save_report(pd.DataFrame(report))
            # Déclenchement de la mise à jour HTML
            try:
                from src.core.checklists import ChecklistGenerator
                cg = ChecklistGenerator(client=dm.client)
                df_news = cg.get_data('Rapport_Veille_Auto')
                df_base_f = cg.get_data('Base_Active')
                cg.generate_dashboard_stats(df_base_f, df_news)
                cg.generate_html(df_news, "Nouveautés", "output/checklist_nouveautes.html", False)
                print("      [OK] Dashboard & Checklists mis à jour.")
                
                # --- SYNCHRONISATION DRIVE & AZURE ---
                print("--- [4/3] Synchronisation Cloud ---")
                run_upload()
                run_azure_upload()
                
            except Exception as e:
                print(f"      [!] Erreur Dashboard ou Drive : {e}")

    print(f"\n✅ PIPELINE TERMINÉ AVEC SUCCÈS ({len(report)} nouvelles alertes).")

if __name__ == "__main__":
    run_pipeline()