
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
- Déchets dangereux : Fluides de coupe (13 00 00*), Solvents.
- D3E : Collecte séparée.
- Emballages : Loi AGEC, REP emballages professionnels (2025).

ENJEUX RSE & ÉNERGIE :
- Décret tertiaire (-40% consommation).
- Bilan GES si seuils atteints.
- Réduction plastiques.
"""

# --- CONFIGURATION ---
class Config:
    # 1. CLÉ POUR L'INTELLIGENCE ARTIFICIELLE
    GEMINI_API_KEY = "AIzaSyC5HKLQIQq7k0nM-_fFbcs84j__qG1ot3I" 
    
    # 2. CLÉ POUR LA RECHERCHE WEB
    SEARCH_API_KEY = "AIzaSyALFplNyJTXDRU-jB5RRqkb7ML629lL_54" 
    
    SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
    CREDENTIALS_FILE = "credentials.json"
    EMAIL_SENDER = "anthony.bezille@gmail.com"
    
    SEARCH_ENGINE_ID = "351eb00bd97be4937"
    EMAIL_PASSWORD = "xdqz ptef dnts remb"
    SMTP_SERVER, SMTP_PORT = "smtp.gmail.com", 587
    
    # --- REGLAGES RECHERCHE ---
    RUN_FULL_AUDIT = False   # Désactivé temporairement pour économiser le quota API
    SEARCH_PERIOD = 'y2'     # 2 ans demandé par l'utilisateur

if "VOTRE_CLE" not in Config.GEMINI_API_KEY:
    genai.configure(api_key=Config.GEMINI_API_KEY)

# --- FONCTION UTILITAIRE JSON ---
def extract_json(text):
    try:
        match = re.search(r'(\[.*\]|\{.*\})', text.replace('\n', ' '), re.DOTALL)
        if match: return json.loads(match.group(1))
        return json.loads(text)
    except: return []

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
            # Chargement de Base_Active pour déduplication
            df = pd.DataFrame(sheet.get_worksheet(0).get_all_records())
            
            # Mapping précis pour la déduplication
            # On veut comparer avec 'Intitulé ' (titre) et 'Lien Internet' (url)
            mapping = { "Intitulé ": "titre", "Lien Internet": "url" }
            df = df.rename(columns=mapping)
            
            # Si colonnes manquantes, on initialise vide pour éviter erreurs
            if 'titre' not in df.columns: df['titre'] = ""
            if 'url' not in df.columns: df['url'] = ""

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
        url = "https://www.googleapis.com/customsearch/v1"
        params = {'q': q, 'key': Config.SEARCH_API_KEY, 'cx': Config.SEARCH_ENGINE_ID, 'dateRestrict': Config.SEARCH_PERIOD}
        try:
            res = requests.get(url, params=params)
            data = res.json()
            
            if 'error' in data:
                err_msg = data['error'].get('message', 'Erreur inconnue')
                print(f"      ❌ ERREUR API GOOGLE : {err_msg}")
                return []
                
            items = data.get('items', [])
            print(f"      [DEBUG] Google a trouvé {len(items)} résultats (Top 10 max) pour '{q}'.")
            return [{"titre": i.get('title'), "snippet": i.get('snippet'), "url": i.get('link')} for i in items]
        except Exception as e: 
            print(f"      [ERREUR API WEB] {e}")
            return []

    def analyze_news(self, text):
        # Prompt enrichi pour extraire Type, Thème, Date
        prompt = f"""
        Contexte GDD (ICPE Métaux, Déchets, Sécurité).
        Analyse cette news : '{text}'
        
        1. Est-ce pertinent pour la veille réglementaire HSE ? (Oui/Non)
        2. Si Oui, extrais :
           - type_texte: (Arrêté, Décret, Article, Avis...)
           - theme: (Déchets, Eau, Air, ICPE, Sécurité...)
           - date_texte:

 (Date du texte si mentionnée, sinon vide)
           - resume: (Synthèse courte en 1 phrase)
           - action: (Ce qu'il faut faire : Lire, Mettre à jour registre, Vérifier seuils...)
           - criticite: (Haute/Moyenne/Basse)

        Réponds UNIQUEMENT en JSON : {{ "criticite": "...", "type_texte": "...", "theme": "...", "date_texte": "...", "resume": "...", "action": "..." }}
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
            if m.get('titre') in existing_titles: continue # Déjà présent
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
                # print(f"      [Ignoré] Déjà dans Base_Active (URL)")
                continue
            if r['titre'] in existing_titles:
                # print(f"      [Ignoré] Déjà dans Base_Active (Titre)")
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