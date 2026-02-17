class Brain:
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def audit_manquants(self, current_list):
        print("   > Audit de complétude (Gap Analysis par l'IA)...")
        titles = "\n".join(current_list[:800]) 
        prompt = f"""
        Auditeur QHSE Expert pour la société GDD (Découpage de précision).
        MISSION : Identifier TOUT texte réglementaire (Lois, Décrets, Arrêtés, Règlements UE) applicable à GDD, sans se limiter à l'ISO ou l'ICPE.
        
        CONTEXTE COMPLET GDD (À lire impérativement) :
        {CONTEXTE_ENTREPRISE}

        VOICI LES TITRES DÉJÀ PRÉSENTS :
        {titles}
        
        RÈGLES DE RECHERCHE :
        1. COUVERTURE TOTALE : Inclus Environnement, Santé & Sécurité (SST), Droit du Travail (Sécurité), REACH/RoHS, Exigences Qualité Produit (FSC, Contact alimentaire), et Énergie (Décret Tertiaire).
        2. PERTINENCE : Retiens tout texte ayant un impact opérationnel, même mineur, sur le site de La Monnerie-le-Montel ou les procédés de découpage/emboutissage.
        3. SOURCE : Uniquement des textes officiels (Légifrance, JOUE).
        
        QUELS TEXTES APPLICABLES MANQUENT ? (Cite 3 textes précis et récents max).
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
        Agis comme un Directeur QHSE de haut niveau. Analyse la "Fiche de synthèse" ci-dessous et génère une liste de 12 mots-clés de recherche Google extrêmement précis.
        Tu DOIS couvrir ces 4 piliers obligatoirement :
        1. ENVIRONNEMENT (ICPE, Déchets métaux/fluides, Eau, Air, Énergie).
        2. SANTÉ & SÉCURITÉ (SST, Sécurité machines, Risque chimique, Incendie, Pénibilité).
        3. PRODUITS & QUALITÉ (REACH, RoHS, FSC, Matériaux contact alimentaire, Marquage CE).
        4. RSE & GOUVERNANCE (Bilan GES, Décret tertiaire, Reporting extra-financier).
        
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
        params = {'q': q, 'key': Config.SEARCH_API_KEY, 'cx': Config.SEARCH_ENGINE_ID, 'dateRestrict': Config.SEARCH_PERIOD}
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
        2. CRITÈRE : Extrais l'exigence précise (seuil, date limite, obligation documentaire).
        3. JUSTIFICATION (D-C-P) :
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
