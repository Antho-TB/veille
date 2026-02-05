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

# Charger les variables d'environnement (.env)
load_dotenv()

# --- CONTEXTE ENTREPRISE (GDD) ---
CONTEXTE_ENTREPRISE = """
Fiche Descriptive Détaillée – Veille Réglementaire Environnementale de la Société Générale de Découpage (GDD)

ACTIVITÉ : Découpage, emboutissage (Code APE 25.50B). Sous-traitant industriel travail des métaux.
SITE : La Monnerie-le-Montel (63).
ICPE :
- 2560 (Travail mécanique métaux) : Enregistrement
- 2561 (Traitements thermiques) : Déclaration
- 2564 (Dégraissage solvants) : Déclaration
- 2565 (Revêtement métallique - Tribofinition) : Déclaration

PRODUITS : Aciers, Inox, Plastiques.
CERTIFICATIONS : ISO 9001, ISO 14001, FSC.

GESTION DES DÉCHETS :
- Tri à la source, traçabilité, registres.
- Déchets dangereux : Fluides de coupe (13 00 00*), Solvants.
- D3E : Collecte séparée.
- Emballages : Loi AGEC, REP emballages professionnels (2025).

ENJEUX RSE & ÉNERGIE :
- Décret tertiaire (-40% consommation).
- Bilan GES si seuils atteints.
- Réduction plastiques.
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
    CREDENTIALS_FILE = "credentials.json"
    EMAIL_SENDER = "a.bezille@tb-groupe.fr"
    SMTP_SERVER, SMTP_PORT = "smtp.gmail.com", 587
    
    # --- REGLAGES RECHERCHE ---
    RUN_FULL_AUDIT = True    # Activé pour valider le fonctionnement de Gemini 2.0 Flash
    SEARCH_PERIOD = 'd7'   
    
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
            'date de la prochaine évaluation', "Evaluation pour le site Pommier (date d'évaluation)"
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
        Auditeur HSE pour GDD (Découpage Métaux, ICPE 2560, 2564).
        VOICI CE QUE J'AI DÉJÀ :
        {titles}
        Fais ta recherche pour identifier les nouvelles réglementations, lois, décrets, normes ou projets de loi publiés
        STRICTS : 
        1. Ne retiens QUE les textes qui ont un impact DIRECT et CRITIQUE ou MOYEN sur les activités de fabrication de précision, les procédés de découpage-emboutissage, les substances (acier, matériaux spécifiques comme EVERCUT®), les sites (ICPE ou autres), ou les certifications (ISO 9001, etc.). 
        2. Ne retiens EXCLUSIVEMENT que des textes officiels (Lois, Décrets, Arrêtés, Règlements, Directives, Décisions). Exclut formellement tout article de presse, blog, guide, ou analyse secondaire.
        3. Si ce n'est pas un texte de loi officiel, ne l'inclus pas.
        4. Exclut tout ce qui a une critique "Faible" ou sans lien direct avec les opérations. 
        QUELS TEXTES OBLIGATOIRES MANQUENT ? (Cite 3 textes précis max).
        Réponds UNIQUEMENT en JSON : [{{ "titre": "...", "criticite": "Haute", "resume": "Manque arrêté...", "action": "Ajouter" }}]
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
        Agis comme un expert QHSE. Analyse le contexte de l'entreprise ci-dessous et génère une liste de 10 mots-clés de recherche Google précis pour la veille réglementaire.
        Concentre-toi sur les rubriques ICPE, les déchets spécifiques (métaux, fluides), et les nouvelles lois (AGEC, REP).
        
        CONTEXTE :
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
        params = {'q': q, 'key': Config.SEARCH_API_KEY, 'cx': Config.SEARCH_ENGINE_ID, 'dateRestrict': Config.SEARCH_PERIOD}
        try:
            res = requests.get(url, params=params)
            data = res.json()
            
            if 'error' in data:
                err_msg = data['error'].get('message', 'Erreur inconnue')
                print(f"      ❌ ERREUR API GOOGLE : {err_msg}")
                # Log détaillé pour débugger l'accès
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
        # Prompt enrichi pour extraire Type, Thème, Date + Few-Shot pour la précision
        prompt = f"""
        Rôle : Expert QHSE spécialisé en droit de l'environnement industriel (ICPE).
        
        Objectif : Analyser le texte suivant pour déterminer s'il s'agit d'un TEXTE RÉGLEMENTAIRE OFFICIEL impactant GDD.
        
        CRITÈRES DE SÉLECTION STRICTS :
        - OUI uniquement si c'est : Loi, Décret, Arrêté, Directive Européenne, Règlement Européen, Ordonnance, Avis au JO.
        - NON systématique si c'est : Article de presse (Actu-Environnement, etc.), Guide pratique, Newsletter, Post LinkedIn, Analyse d'expert, Communiqué de presse.
        
        EXEMPLES :
        1. "Arrêté du 2 février 1998 relatif aux prélèvements et à la consommation d'eau" -> OUI (Arrêté)
        2. "Comment réussir sa transition ISO 14001 : les conseils d'Afnor" -> NON (Guide/Conseil)
        3. "Décret n° 2024-123 portant modification du code de l'environnement" -> OUI (Décret)
        4. "Le gouvernement annonce une simplification des ICPE" -> NON (News/Annonce)
        
        TEXTE À ANALYSER : '{text}'
        
        Si OUI, extrais les informations suivantes en JSON.
        Si NON, réponds avec {{"criticite": "Non"}}.

        Champs JSON si OUI :
        - type_texte: (Arrêté, Décret, Loi, Règlement, Directive, Ordonnance, Avis)
        - theme: (Déchets, Eau, Air, ICPE, Sécurité, RSE, Énergie)
        - date_texte: (Format DD/MM/YYYY si présente)
        - resume: (Résumé technique court en 1 phrase)
        - action: (Action concrète pour GDD)
        - criticite: (Haute/Moyenne/Basse)

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

    # 1. AUDIT (Gap Analysis)
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