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
import datetime
import mlflow
# Standard MLflow tracking

# Charger les variables d'environnement (depuis config/.env)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../config/.env"))

# --- CONTEXTE ENTREPRISE (GDD) ---
CONTEXTE_ENTREPRISE = """
Fiche de synthèse 17 septembre – Veille Réglementaire QHSE de la Société Générale de Découpage (GDD)

ACTIVITÉ : Découpage, emboutissage (Code APE 25.50B). Sous-traitant industriel automobile, luxe, aéronautique.
SITE : La Monnerie-le-Montel (63).
PROCÉDÉS : Découpage haute vitesse, emboutissage, tribofinition, dégraissage, traitements thermiques.
ICPE :
- 2560 (Travail mécanique métaux) : Enregistrement
- 2561 (Traitements thermiques) : Déclaration
- 2564 (Dégraissage solvants) : Déclaration
- 2565 (Revêtement métallique - Tribofinition) : Déclaration

PRODUITS & MATIÈRES : Aciers, Inox, Plastiques, Cuivreux. Usage d'huiles de coupe, solvants, produits chimiques.
CERTIFICATIONS : ISO 9001 (Qualité), ISO 14001 (Environnement), FSC (Traçabilité bois/papier).

SANTÉ & SÉCURITÉ (SST) : 
- Exposition au bruit, TMS, risques machines.
- Gestion des fluides et vapeurs.
- Risques incendie et ATEX.

GESTION DES DÉCHETS :
- Tri à la source, traçabilité (Trackdéchets).
- Déchets dangereux (13 00 00*), Emballages pro (Loi AGEC / REP 2025).

GOUVERNANCE : RSE, Décret tertiaire, Sobriété énergétique.
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
        print("--- [1/4] Chargement données Sheets ---")
        try:
            if not self.client: self._connect()
            sheet = self.client.open_by_key(Config.SHEET_ID)
            ws = sheet.get_worksheet(0)
            data = ws.get_all_records()
            df = pd.DataFrame(data)
            
            # Nettoyage des colonnes (lowercase and strip)
            df.columns = [c.strip() for c in df.columns]
            
            # Mapping flexible
            mapping = {
                "Intitulé": "titre",
                "Intitulé ": "titre",
                "Lien Internet": "url",
                "Lien internet": "url",
                "Lien": "url",
                "URL": "url"
            }
            df = df.rename(columns=mapping)
            
            # Garantir les colonnes minimales
            for col in ['titre', 'url']:
                if col not in df.columns: df[col] = ""
            
            print(f"   > Colonnes chargées : {list(df.columns)}")

            try: df_conf = pd.DataFrame(sheet.worksheet('Config_IA').get_all_records())
            except: df_conf = pd.DataFrame({'keywords': [
                'Arrêté type 2560', 'ICPE 2564', 'Loi AGEC industrie', 
                'Déchets 130000', 'Rubrique 2565', 'Code de l\'environnement ICPE'
            ]})

            print(f"   > {len(df)} textes existants chargés pour déduplication.")
            return df, df_conf
        except Exception as e:
            print(f"❌ ERREUR CHARGEMENT : {e}")
            return pd.DataFrame(), pd.DataFrame()

    def save_report(self, df_report):
        print("--- [4/4] Sauvegarde Rapport ---")
        if df_report.empty: 
            print("   > Aucune donnée à sauvegarder.")
            return
        
        # Colonnes exactes de Base_Active
        cols = [
            'Mois', 'Sources', 'Type de texte', 'N°', 'Date', 'Intitulé ', 'Thème', 
            'Commentaires (ALSAPE, APORA…)', 'Lien Internet', 'Statut', 'Conformité', 
            "Délai d'application", 'Commentaires', 'date de la dernère évaluation', 
            'date de la prochaine évaluation', "Evaluation pour le site Pommier (date d'évaluation)",
            'Criticité', 'Preuve de Conformité Attendue', 'Preuves disponibles'
        ]
        
        # Mapping des données IA vers les colonnes Excel
        df_report['Mois'] = datetime.now().strftime("%B %Y")
        df_report['Sources'] = "Veille Auto"
        df_report['Intitulé '] = df_report.get('titre', '')
        df_report['Lien Internet'] = df_report.get('url', '')
        df_report['Type de texte'] = df_report.get('type_texte', 'Autre')
        df_report['Thème'] = df_report.get('theme', '')
        df_report['Date'] = df_report.get('date_texte', '')
        
        # Commentaires = Résumé + Action
        df_report['Commentaires'] = df_report.apply(lambda x: f"{x.get('resume', '')} (Action: {x.get('action', '')})", axis=1)
        df_report['Statut'] = "A traiter"
        df_report['Criticité'] = df_report.get('criticite', 'Basse')
        df_report['Preuve de Conformité Attendue'] = df_report.get('preuve_attendue', '')
        df_report['Preuves disponibles'] = "Non"

        for c in cols: 
            if c not in df_report.columns: df_report[c] = ""
        final = df_report[cols].fillna("").astype(str)
        
        try:
            if not self.client: self._connect()
            sheet = self.client.open_by_key(Config.SHEET_ID)
            try: ws = sheet.worksheet('Rapport_Veille_Auto')
            except: ws = sheet.add_worksheet('Rapport_Veille_Auto', 1000, 20)
            
            # NE PAS EFFACER (ws.clear) car l'utilisateur a mis son formatage
            # On ajoute simplement les nouvelles lignes à la suite
            ws.append_rows(final.values.tolist())
            
            print(f"   > {len(final)} nouvelles lignes ajoutées dans 'Rapport_Veille_Auto' !")
        except Exception as e: print(f"   > Erreur sauvegarde : {e}")
        return final

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
class Brain:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def audit_manquants(self, current_list):
        print("   > Audit de complétude (Gap Analysis par l'IA)...")
        titles = "\n".join(current_list[:800]) 
        prompt = f"""
        Auditeur QHSE Expert pour la société GDD (Découpage de précision).
        MISSION : Identifier TOUT texte réglementaire (Lois, Décrets, Arrêtés, Règlements UE) et LOCAL (Arrêtés préfectoraux du Puy-de-Dôme, SDAGE) applicable à GDD.
        
        CONTEXTE COMPLET GDD (À lire impérativement) :
        {CONTEXTE_ENTREPRISE}

        VOICI LES TITRES DÉJÀ PRÉSENTS :
        {titles}
        
        RÈGLES DE RECHERCHE :
        1. COUVERTURE TOTALE : Inclus Environnement, Santé & Sécurité (SST), REACH/RoHS, Qualité Produit, et Énergie (Décret Tertiaire, Sobriété).
        2. FOCUS LOCAL : Vérifie spécifiquement les arrêtés préfectoraux (63) et les règles du bassin Loire-Bretagne (Sécheresse, Rejets).
        3. PERTINENCE : Retiens tout texte ayant un impact opérationnel sur le site ou les procédés.
        4. SOURCE : Uniquement des textes officiels.
        
        QUELS TEXTES APPLICABLES MANQUENT ? (Sois exhaustif, cite jusqu'à 15 textes précis et fondamentaux).
        Réponds UNIQUEMENT en JSON : [{{ "titre": "...", "criticite": "Haute", "resume": "Explique pourquoi c'est applicable à GDD", "action": "Action concrète" }}]
        """
        try:
            resp = self.model.generate_content(prompt)
            return extract_json(resp.text)
        except Exception as e: 
            print(f"      [ERREUR IA AUDIT] {e}")
            return []

    def generate_keywords(self):
        print("   > Génération des mots-clés de veille par l'IA...")
        prompt = f"""
        Agis comme un Directeur QHSE de haut niveau. Analyse la "Fiche de synthèse" et génère 12 mots-clés Google extrêmement précis.
        Tu DOIS couvrir ces 4 piliers obligatoirement :
        1. ENVIRONNEMENT & LOCAL (ICPE, Déchets, Eau/Sécheresse 63, SDAGE Loire-Bretagne, Arrêté préfectoral Puy-de-Dôme).
        2. SANTÉ & SÉCURITÉ (SST, Machines, Chimique, Incendie, Pénibilité).
        3. PRODUITS & QUALITÉ (REACH, RoHS, FSC, Contact alimentaire, Marquage CE).
        4. ÉNERGIE & RSE (Décret tertiaire, Sobriété énergétique, Efficacité énergétique, Bilan GES).
        
        FICHE DE SYNTHÈSE GDD :
        {CONTEXTE_ENTREPRISE}
        
        Réponds UNIQUEMENT en JSON : ["Mot clé 1", "Mot clé 2", ...]
        """
        try:
            resp = self.model.generate_content(prompt)
            keywords = extract_json(resp.text)
            if isinstance(keywords, list): return keywords
            return []
        except Exception as e:
            print(f"      [ERREUR IA KEYWORDS] {e}")
            return []

    def search(self, q):
        # 1. ESSAYER TAVILY SI DISPONIBLE (Option 1)
        if Config.TAVILY_API_KEY:
            print(f"      [TAVILY] Recherche pour '{q}'...")
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": Config.TAVILY_API_KEY,
                "query": q,
                "search_depth": "basic",
                "max_results": 10
            }
            try:
                res = requests.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return [{"titre": r.get('title'), "snippet": r.get('content'), "url": r.get('url')} for r in data.get('results', [])]
                else:
                    print(f"      ⚠️ Tavily Error {res.status_code}: {res.text}")
            except Exception as e:
                print(f"      ⚠️ Tavily Exception: {e}")

        # 2. FALLBACK GOOGLE CUSTOM SEARCH (Option 2)
        url = "https://www.googleapis.com/customsearch/v1"
        params = {'q': q, 'key': Config.SEARCH_API_KEY, 'cx': Config.SEARCH_ENGINE_ID}
        if Config.SEARCH_PERIOD: params['dateRestrict'] = Config.SEARCH_PERIOD
        try:
            res = requests.get(url, params=params)
            data = res.json()
            
            if 'error' in data:
                err_msg = data['error'].get('message', 'Erreur inconnue')
                print(f"      ❌ ERREUR API GOOGLE : {err_msg}")
                if "access" in err_msg.lower() or "project" in err_msg.lower():
                    print(f"      [DEBUG FULL ERROR] {res.text}")
                return []
                
            items = data.get('items', [])
            print(f"      [DEBUG] Google a trouvé {len(items)} résultats (Top 10 max) pour '{q}'.")
            return [{"titre": i.get('title'), "snippet": i.get('snippet'), "url": i.get('link')} for i in items]
        except Exception as e: 
            print(f"      [ERREUR API WEB] {e}")
            return []

    def analyze_news(self, text):
        # Prompt QHSE Global sans focus restrictif ISO
        prompt = f"""
        Rôle : Directeur QHSE Expert en conformité industrielle.
        Mission : Évaluer l'applicabilité et l'impact d'un nouveau texte pour GDD (Générale de Découpage).

        CONTEXTE DE L'ENTREPRISE (Fiche de synthèse) :
        {CONTEXTE_ENTREPRISE}

        RÈGLES D'ANALYSE :
        1. APPLICABILITÉ GLOBALE : Vérifie si le texte concerne les procédés (découpage, thermique, dégraissage), les matériaux (acier, inox), le site (La Monnerie-le-Montel) ou les piliers QHSE (Environnement, SST, Qualité, RSE).
        2. FILTRE ANTI-BRUIT (CRITIQUE) : IGNORE TOUTE ACTUALITÉ COMMERCIALE OU PRODUIT GRAND PUBLIC. 
           - Si le texte parle d'un produit fini vendu au détail (ex: bois de chauffage, ustensiles, four à pizza) sans introduire une NOUVELLE RÈGLE de sécurité ou d'environnement pour l'USINE, réponds {{"criticite": "Non"}}.
           - Ne retiens pas les catalogues produits ou les offres promotionnelles.
        3. CRITÈRE : Extrais l'exigence précise (seuil, date limite, obligation documentaire).
        4. JUSTIFICATION (D-C-P) :
           - Donnée : Élément de la Fiche de Synthèse impacté (ex: FSC, Risque machines, Fluides de coupe).
           - Critère : La règle extraite du texte.
           - Preuve : Document physique à fournir (ex: Certificat FSC, PV de mesurage bruit, FDS).

        GRILLE DE CRITICITÉ :
        - HAUTE : Sanction immédiate, interdiction de substance, arrêt d'activité possible.
        - MOYENNE : Action de mise en conformité requise (investissement, nouveau registre, reporting).
        - BASSE : Information simple ou mise à jour documentaire mineure.

        TEXTE À ANALYSER : '{text}'
        
        Réponds UNIQUEMENT en JSON si le texte est un document officiel et pertinent pour GDD. Sinon, réponds {{"criticite": "Non"}}.

        CHAMPS JSON :
        - type_texte: (Loi, Décret, Arrêté, Règlement UE...)
        - theme: (EAU, DECHETS, AIR, ICPE, SSCT, QUALITE, PRODUIT, ENERGIE, RSE)
        - date_texte: (DD/MM/YYYY)
        - resume: (Résumé technique précis)
        - action: (Action précise pour GDD)
        - criticite: (Haute, Moyenne, Basse)
        - preuve_attendue: (Le document de preuve d'audit)
        
        Réponds UNIQUEMENT en JSON.
        """
        try:
            resp = self.model.generate_content(prompt)
            res = extract_json(resp.text)
            if not isinstance(res, dict): return {"criticite": "Non"}
            return res
        except: return {"criticite": "Non"}

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

    dm, ve, brain = DataManager(), VectorEngine(), Brain()
    df_base, conf = dm.load_data()
    
    # Indexation pour RAG (optionnel ici mais conservé)
    ve.index(df_base)
    
    # Création des sets pour déduplication rapide
    existing_urls = set(df_base['url'].astype(str).tolist())
    existing_titles = set(df_base['titre'].astype(str).tolist())
    
    report = []

    def log_synthesis_history():
        print("   > Historisation de la synthèse (MLflow + Sheets)...")
        # MLflow
        with mlflow.start_run(run_name="synthesis_run", nested=True):
            mlflow.log_param("search_period", Config.SEARCH_PERIOD)
            mlflow.log_param("run_full_audit", Config.RUN_FULL_AUDIT)
            
        # Google Sheets
        try:
            sheet = self.client.open_by_key(Config.SHEET_ID)
            try:
                ws = sheet.worksheet("Historique_Synthese")
            except:
                ws = sheet.add_worksheet(title="Historique_Synthese", rows="100", cols="5")
                ws.append_row(["Date", "Utilisateur", "Action", "Commentaire"])
            
            ws.append_row([
                datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Système (Auto)",
                "Scan QHSE",
                f"Période: {Config.SEARCH_PERIOD or 'Baseline'}"
            ])
        except Exception as e:
            print(f"      [ERREUR LOG SHEETS] {e}")
        
        print("   > Historisation terminée.")

    # 1. Historisation
    log_synthesis_history()
    
    # 2. Audit des manques (Gap Analysis)
    if Config.RUN_FULL_AUDIT:
        manquants = brain.audit_manquants(df_base['titre'].astype(str).tolist())
        for m in manquants:
            if m.get('titre') in existing_titles: continue  # Déjà présent
            m['type_texte'] = 'MANQUANT'
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
    
    for k in keywords:
        if not k: continue
        print(f"   > Scan: {k}")
        res = brain.search(k)
        for r in res:
            # DEDUPLICATION
            if r['url'] in existing_urls:
                continue
            if r['titre'] in existing_titles:
                continue
            
            # ANALYSE IA
            ana = brain.analyze_news(f"{r['titre']} {r['snippet']}")
            if ana.get('criticite') in ['Haute', 'Moyenne']:
                r.update(ana)
                report.append(r)
                print(f"      [+] Pertinent ({ana.get('type_texte')}): {r['titre'][:40]}...")
                
                # On ajoute aux sets pour éviter les doublons dans la même exécution
                existing_urls.add(r['url'])
            time.sleep(1)

    dm.save_report(pd.DataFrame(report))
    print(">>> TERMINÉ <<<")