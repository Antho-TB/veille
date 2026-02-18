# ---------------------------------------------------------------------------
# Pipeline de Veille Réglementaire Automatisée - GDD
# ---------------------------------------------------------------------------
# Ce script est le moteur principal de l'application :
# 1. Recherche les nouveaux textes réglementaires via Google Custom Search.
# 2. Analyse la pertinence et résume le contenu via Google Gemini (IA).
# 3. Alimente le Rapport de Veille dans Google Sheets.
# ---------------------------------------------------------------------------

import os
import time
import json
import smtplib
import requests
import pandas as pd
import chromadb
import gspread
import google.generativeai as genai
import re
from oauth2client.service_account import ServiceAccountCredentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
import mlflow
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from src.core.brain_new import Brain

# Charger les variables d'environnement (depuis config/.env)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../config/.env"))

# --- CONTEXTE ENTREPRISE (GDD) ---
CONTEXTE_ENTREPRISE = """
Fiche de synthèse – Veille Réglementaire QHSE GDD
ACTIVITÉ : Découpage, emboutissage technique. 
SITE : Puy-de-Dôme (63).
ICPE : 2560, 2561, 2564, 2565.
CERTIFICATIONS : ISO 9001, 14001, FSC.
"""

# --- CONFIGURATION ---
class Config:
    # 1. CLÉS RÉCUPÉRÉES DEPUIS .ENV
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "VOTRE_CLE_GEMINI")
    SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "VOTRE_CLE_SEARCH")
    SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID", "VOTRE_CX")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    
    SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
    # Chemin vers les credentials (depuis la racine du projet)
    CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "../../config/credentials.json")
    EMAIL_SENDER = "a.bezille@tb-groupe.fr"
    SMTP_SERVER, SMTP_PORT = "smtp.gmail.com", 587
    
    # --- REGLAGES RECHERCHE ---
    RUN_FULL_AUDIT = True    
    SEARCH_PERIOD = 'm1'   
    MLFLOW_TRACKING = True
    MODEL_NAME = "gemini-3-flash-preview"
    SEARCH_MAX_RESULTS = 10
    
    # --- DYNAMIC CONTEXT ---
    CONTEXT_DOC_ID = "1WnTuZOgb3SnkzrK7BOiznp51Z2n4H1FjFoDoebLHYsc"

if "VOTRE_CLE" not in Config.GEMINI_API_KEY:
    genai.configure(api_key=Config.GEMINI_API_KEY)

# --- FONCTION UTILITAIRE JSON ---
def extract_json(text):
    try:
        match = re.search(r'(\[.*\]|\{.*\})', text.replace('\n', ' '), re.DOTALL)
        if match: return json.loads(match.group(1))
        return json.loads(text)
    except: return []

# --- FONCTION RECUPERATION CONTEXTE DYNAMIQUE ---
def fetch_dynamic_context(file_id):
    print(f"--- [0/4] Chargement Contexte Dynamique (Doc ID: {file_id}) ---")
    try:
        if not os.path.exists(Config.CREDENTIALS_FILE):
            print("   > ⚠️ Fichier credentials.json manquant. Utilisation du contexte par défaut.")
            return None
            
        scope = ["https://www.googleapis.com/auth/drive.readonly"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
        access_token = creds.get_access_token().access_token
        
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=text/plain"
        
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            content = resp.text
            print(f"   > ✅ Contexte chargé avec succès ({len(content)} caractères).")
            return content
        else:
            print(f"   > ⚠️ Erreur chargement contexte (Status: {resp.status_code}): {resp.text}")
            return None
    except Exception as e:
        print(f"   > ⚠️ Exception chargement contexte: {e}")
        return None

# --- 1. GESTION DONNÉES ---
class DataManager:
    def __init__(self):
        self.client = None
    
    def _connect(self):
        if not os.path.exists(Config.CREDENTIALS_FILE): raise FileNotFoundError("Manque credentials.json")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope))

    def load_data(self):
        print("--- [1/4] Chargement et Déduplication multi-feuilles ---")
        try:
            if not self.client: self._connect()
            sheet = self.client.open_by_key(Config.SHEET_ID)
            
            # Recherche exhaustive sur les 3 onglets de données pour éviter les doublons
            all_dfs = []
            for ws_name in ['Base_Active', 'Rapport_Veille_Auto', 'Informative']:
                try:
                    ws = sheet.worksheet(ws_name)
                    data = ws.get_all_records()
                    if data:
                        temp_df = pd.DataFrame(data)
                        temp_df.columns = [c.strip() for c in temp_df.columns]
                        all_dfs.append(temp_df)
                except: continue
            
            if not all_dfs:
                return pd.DataFrame(), pd.DataFrame()
                
            df = pd.concat(all_dfs, ignore_index=True)
            
            # Mapping flexible pour la déduplication
            mapping = {
                "Intitulé": "titre", "Intitulé ": "titre",
                "Lien Internet": "url", "Lien internet": "url", "Lien": "url", "URL": "url"
            }
            df = df.rename(columns=mapping)
            
            # Garantir les colonnes minimales
            for col in ['titre', 'url']:
                if col not in df.columns: df[col] = ""
            
            print(f"   > {len(df)} textes historiques analysés (Base + Auto + Informative).")

            try: df_conf = pd.DataFrame(sheet.worksheet('Config_IA').get_all_records())
            except: df_conf = pd.DataFrame({'keywords': ['Arrêté type 2560', 'ICPE 2564']})

            return df, df_conf
        except Exception as e:
            print(f"❌ ERREUR CHARGEMENT : {e}")
            return pd.DataFrame(), pd.DataFrame()

    def save_report(self, df_report):
        print("--- [4/4] Sauvegarde et Routage des données ---")
        if df_report.empty: 
            print("   > Aucune donnée à sauvegarder.")
            return
        
        # Structure de colonnes unifiée (Base Active + Justificatifs + Plan d'action)
        cols = [
            'Mois', 'Sources', 'Type de texte', 'N°', 'Date', 'Intitulé ', 'Thème', 
            'Grand thème', 'Commentaires (ALSAPE, APORA…)', 'Lien Internet', 'Statut', 'Conformité', 
            "Délai d'application", 'Commentaires', 'date de la dernère évaluation', 
            'date de la prochaine évaluation', "Evaluation pour le site Pommier (date d'évaluation)",
            'Criticité', 'Preuve de Conformité Attendue', 'Justificatif de déclaration et contrôle',
            'Plan Action', 'Responsable', 'Échéance'
        ]
        
        # Enrichissement
        df_report['Mois'] = datetime.now().strftime("%B %Y")
        df_report['Sources'] = "Veille Auto"
        df_report['Intitulé '] = df_report.get('titre', '')
        df_report['Lien Internet'] = df_report.get('url', '')
        df_report['Type de texte'] = df_report.get('type_texte', 'Autre')
        df_report['Date'] = df_report.get('date', '')
        df_report['Preuve de Conformité Attendue'] = df_report.get('preuve_attendue', '')
        df_report['Commentaires'] = df_report.apply(lambda x: f"{x.get('resume', '')} (Action: {x.get('action', '')})", axis=1)
        df_report['Statut'] = "A traiter"
        df_report['Justificatif de déclaration et contrôle'] = "" # Zone métier
        df_report['Plan Action'] = ""
        
        for c in cols: 
            if c not in df_report.columns: df_report[c] = ""
        
        # ROUTAGE : Distinction Alertes vs Informatif
        # Si criticité "Non" ou "Informatif" ou thématique secondaire
        mask_info = (df_report['criticite'].isin(['Non', 'Informatif']))
        df_alerts = df_report[~mask_info]
        df_info = df_report[mask_info]

        try:
            if not self.client: self._connect()
            sheet = self.client.open_by_key(Config.SHEET_ID)
            
            def safe_append(ws_name, data_df):
                if data_df.empty: return
                try: ws = sheet.worksheet(ws_name)
                except: ws = sheet.add_worksheet(ws_name, 1000, 25)
                
                rows = data_df[cols].fillna("").astype(str).values.tolist()
                
                # POLITIQUE D'INCREMENTATION ROBUSTE : 
                # On trouve la première ligne vraiment vide (Intitulé vide)
                # Note: ws.append_rows est pratique mais peut créer des gaps si le sheet a des lignes vides formatées.
                # On utilise append_rows avec table_prefix si possible, ou on nettoie.
                ws.append_rows(rows, value_input_option='USER_ENTERED')
                print(f"      [OK] {len(rows)} lignes ajoutées dans '{ws_name}'.")

            safe_append('Rapport_Veille_Auto', df_alerts)
            safe_append('Informative', df_info)
            
        except Exception as e: print(f"   > Erreur sauvegarde : {e}")

# --- 2. VECTOR STORE ---
class VectorEngine:
    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection("veille_db")

    def index(self, df):
        if df.empty: return
        df = df[df['titre'] != ""]
        if self.collection.count() >= len(df): return 
        
        ids = [f"row_{i}" for i in range(len(df))]
        docs = df['titre'].astype(str).tolist()
        metas = [{'titre': t[:100]} for t in docs]
        try: self.collection.upsert(documents=docs, metadatas=metas, ids=ids)
        except: pass

# --- 3. INTELLIGENCE (IA) ---
# --- (Brain class removed to use external version) ---

# --- MAIN ---
if __name__ == "__main__":
    print(f">>> LANCEMENT PIPELINE (Mode: {Config.SEARCH_PERIOD}) <<<")
    if not os.path.exists(Config.CREDENTIALS_FILE): exit()

    # Chargement contexte dynamique
    dynamic_context = fetch_dynamic_context(Config.CONTEXT_DOC_ID)
    if dynamic_context:
        CONTEXTE_ENTREPRISE = dynamic_context
        print("   > Contexte mis à jour depuis Google Doc.")
    else:
        print("   > Utilisation du contexte par défaut (Hardcodé).")

    dm, ve = DataManager(), VectorEngine()
    brain = Brain(context=CONTEXTE_ENTREPRISE, model_name=Config.MODEL_NAME)
    df_base, conf = dm.load_data()
    
    # Indexation pour RAG (optionnel ici mais conservé)
    ve.index(df_base)
    
    # Création des sets pour déduplication rapide
    existing_urls = set(df_base['url'].astype(str).tolist())
    existing_titles = set(df_base['titre'].astype(str).tolist())
    
    report = []

    def sanitize_mlflow_name(name):
        import re
        # Ne garder que alphanum, _, -, ., espace et /
        return re.sub(r'[^a-zA-Z0-9_\-\.\ \/]', '_', name)

    # --- INITIALISATION MLFLOW (Parent Run) ---
    mlflow.set_experiment("Veille_QHSE_Production")
    start_time = time.time()
    parent_run = mlflow.start_run(run_name=sanitize_mlflow_name(f"Scan_{datetime.now().strftime('%d-%m_%Hh%M')}"))
    mlflow.log_params({
        "search_period": Config.SEARCH_PERIOD,
        "full_audit": Config.RUN_FULL_AUDIT,
        "context_source": "Google Doc" if dynamic_context else "Hardcoded",
        "model_name": Config.MODEL_NAME
    })

    # --- SYNTHESE QUOTIDIENNE (Historique_Synthese) ---
    def log_synthesis_history(run_id, model, findings_count, scan_results):
        """
        Trace l'utilisation de la Fiche de Synthèse pour la conformité.
        """
        print("   > Historisation de la synthèse (MLflow + Sheets)...")
        with mlflow.start_run(run_name="synthesis_verification", nested=True):
            mlflow.log_param("status", "verified")
            
        # Google Sheets
        try:
            dm_local = DataManager() # Use a local instance to avoid conflicts
            if not dm_local.client: dm_local._connect()
            sheet = dm_local.client.open_by_key(Config.SHEET_ID)
            try:
                ws = sheet.worksheet("Historique_Synthese")
            except:
                # Création si nécessaire avec les nouvelles colonnes MLflow
                ws = sheet.add_worksheet(title="Historique_Synthese", rows="1000", cols="8")
                ws.append_row(["Date", "Run ID", "Modèle", "Alertes", "Scannés", "Action", "Lien MLflow", "Commentaire"])
            
            # Formatage du lien MLflow local
            mlflow_url = f"http://127.0.0.1:5000/#/experiments/0/runs/{run_id}"
            
            ws.append_row([
                datetime.now().strftime("%d/%m/%Y %H:%M"),
                run_id,
                model,
                findings_count,
                scan_results,
                "Scan Automatique QHSE",
                mlflow_url,
                f"Période: {Config.SEARCH_PERIOD or 'Baseline'}"
            ])
            print(f"      [OK] Synthèse historisée dans Google Sheets ({findings_count} alertes).")
        except Exception as e:
            print(f"      [ERREUR LOG SHEETS] {e}")
        
    # 2. Audit des manques (Gap Analysis)
    if Config.RUN_FULL_AUDIT:
        manquants = brain.audit_manquants(df_base['titre'].astype(str).tolist())
        for m in manquants:
            if m.get('titre') in existing_titles: continue  # Déjà présent
            report.append(m)
            print(f"   [!] Manque détecté : {m.get('titre', 'Titre Inconnu')}")

    # 2. VEILLE WEB
    print(f"--- [3/4] Veille Web ({Config.SEARCH_PERIOD}) ---")
    
    keywords = []
    if 'keywords' in conf.columns:
        keywords = conf['keywords'].tolist()
    
    if not keywords or len(keywords) < 3:
        keywords_ia = brain.generate_keywords()
        keywords.extend(keywords_ia)
        keywords = list(set(keywords))

    if not keywords: keywords = ['Arrêté ICPE 2560', 'Déchets métaux']
    
    print(f"   > Mots-clés utilisés : {', '.join(keywords[:5])}...")
    mlflow.log_param("keywords_count", len(keywords))
    mlflow.log_text(", ".join(keywords), "search_keywords.txt")
    
    total_results_scanned = 0
    pertinent_findings = 0
    type_distribution = {}
    
    for k in keywords:
        if not k: continue
        print(f"   > Scan: {k}")
        res = brain.search(
            q=k, 
            num_results=Config.SEARCH_MAX_RESULTS,
            search_api_key=Config.SEARCH_API_KEY,
            search_engine_id=Config.SEARCH_ENGINE_ID,
            search_period=Config.SEARCH_PERIOD,
            tavily_api_key=Config.TAVILY_API_KEY
        )
        total_results_scanned += len(res)
        
        for r in res:
            # DEDUPLICATION
            if r['url'] in existing_urls:
                continue
            if r['titre'] in existing_titles:
                continue
            
            # ANALYSE IA
            ana = brain.analyze_news(f"{r['titre']} {r['snippet']}")
            if ana.get('criticite') in ['Haute', 'Moyenne']:
                pertinent_findings += 1
                t_type = ana.get('type_texte', 'Inconnu')
                type_distribution[t_type] = type_distribution.get(t_type, 0) + 1
                
                r.update(ana)
                report.append(r)
                print(f"      [+] Pertinent ({t_type}): {r['titre'][:40]}...")
                
                # On ajoute aux sets pour éviter les doublons dans la même exécution
                existing_urls.add(r['url'])
            time.sleep(1)

    # Logging des métriques finales dans MLflow
    mlflow.log_metric("total_web_results", total_results_scanned)
    mlflow.log_metric("pertinent_items_found", pertinent_findings)
    mlflow.log_metric("duration_seconds", time.time() - start_time)
    
    # Détails des types (Sanitisés)
    for t_type, count in type_distribution.items():
        mlflow.log_metric(sanitize_mlflow_name(f"type_{t_type}"), count)
    
    # Artifact: Liste détaillée des trouvailles
    if report:
        finding_summary = "\n".join([f"- {r.get('titre', 'N/A')} ({r.get('url', 'Pas d_URL')})" for r in report])
        mlflow.log_text(finding_summary, "findings_report.txt")

    mlflow.set_tag("execution_status", "success")
    
    # FINALISATION : LOG SYNTHESE
    # Historisation avec métriques réelles
    log_synthesis_history(
        run_id=parent_run.info.run_id, 
        model=Config.MODEL_NAME, 
        findings_count=pertinent_findings, 
        scan_results=total_results_scanned
    )
    
    mlflow.end_run()
    print("\n✅ PIPELINE TERMINÉ AVEC SUCCÈS.")
    
    dm.save_report(pd.DataFrame(report))
    # --- MISE À JOUR DASHBOARD & CHECKLISTS ---
    # Pour un MLE, c'est l'étape de 'Post-processing' et de 'Reporting'.
    # On déclenche la régénération des fichiers HTML et du JSON de stats.
    print("\n--- [DASHBOARD] Mise à jour des statistiques et fiches ---")
    try:
        from src.core.checklists import ChecklistGenerator, OUTPUT_NOUVEAUTES, OUTPUT_BASE
        # On réutilise le client Google existant pour éviter les erreurs de reconnexion
        cg = ChecklistGenerator(client=dm.client) 
        
        # On recharge les données fraîches depuis le Sheet (Source of Truth)
        df_news_final = cg.get_data('Rapport_Veille_Auto')
        df_base_final = cg.get_data('Base_Active')
        
        # Calcul des métriques métier (KPIs)
        cg.generate_dashboard_stats(df_base_final, df_news_final)
        
        # Generation des vues utilisateurs (Dashboard + Checklists)
        cg.generate_html(df_news_final, "Fiche Contrôle - Nouveautés", OUTPUT_NOUVEAUTES, is_base_active=False)
        cg.generate_html(df_base_final, "Fiche Contrôle - Base Active", OUTPUT_BASE, is_base_active=True)
        print("   > ✅ Dashboard et Checklists mis à jour !")
    except Exception as e:
        import traceback
        print(f"   > ❌ Erreur mise à jour Dashboard : {e}")
        traceback.print_exc()

    print(">>> TERMINÉ <<<")
    mlflow.end_run()