import os
import json
import re
import requests
import google.generativeai as genai

class Brain:
    """
    Classe regroupant toute l'intelligence artificielle (IA) et la recherche web.
    C'est le 'Cerveau' du projet qui va lire les textes, chercher sur internet, etc.
    """
    def __init__(self, context="", model_name='gemini-3-flash-preview'):
        """
        Initialisation du cerveau.
        
        Args:
            context (str): Les informations sur l'entreprise (ex: ses activités, ses certifications).
            model_name (str): Le nom du modèle d'Intelligence Artificielle de Google à utiliser.
        """
        # On sauvegarde le contexte (en enlevant les espaces vides au début et à la fin avec .strip())
        self.context = (context or "").strip()
        
        # Ce bloc 'try...except' permet de gérer les erreurs : 
        # Si le modèle demandé n'est pas disponible, on a un plan B (un modèle de secours).
        self.model_name = model_name
        try:
            # On s'assure que le nom commence bien par 'models/' comme l'exige Google
            full_model_name = model_name if model_name.startswith("models/") else f"models/{model_name}"
            # On charge le modèle d'IA !
            self.model = genai.GenerativeModel(full_model_name)
            self.model_name = full_model_name
            
            # Message pour dire que tout va bien
            print(f"      [OK] Modèle {self.model_name} initialisé.")
        except Exception as e:
            print(f"      [!] Modèle {model_name} non disponible ({e}), repli sur models/gemini-2.0-flash.")
            self.model = genai.GenerativeModel('models/gemini-2.0-flash')
            self.model_name = "models/gemini-2.0-flash"

    def audit_manquants(self, current_list):
        """
        Demande à l'IA d'analyser la liste actuelle des textes et de trouver ce qu'il manque.
        
        Args:
            current_list (list): La liste des textes que l'usine suit déjà.
            
        Returns:
            list: Une liste de dictionnaires (JSON) contenant les textes manquants proposés par l'IA.
        """
        print(f"   > Audit de complétude exhaustif (Gap Analysis via {self.model_name})...")
        # On regroupe tous les titres actuels en un seul grand texte pour l'envoyer à l'IA
        titles = "\n".join(current_list[:1500])  # Plus de titres
        
        # Le 'prompt' est la consigne que l'on donne à l'IA. 
        # C'est comme donner des instructions précises à un stagiaire très intelligent.
        prompt = f"""
        Auditeur QHSE Expert.
        MISSION : Identifier TOUT texte réglementaire (Lois, Décrets, Arrêtés, Règlements UE) applicable à GDD.
        
        CONTEXTE STRATÉGIQUE COMPLET (À utiliser à 100%) :
        {self.context}

        VOICI LES TEXTES DÉJÀ PRÉVUS :
        {titles}
        
        RÈGLES D'OR :
        1. SOIS EXHAUSTIF : Ne te limite pas au top 3. Cite jusqu'à 15 textes fondamentaux manquants.
        2. COUVERTURE : Environnement, SST, REACH/RoHS, Exigences Qualité, Énergie, Transport (ADR), Déchets.
        3. DISTINCTION CRITIQUE : 
           - 'action' : Décrit CE QUE GDD DOIT FAIRE concrètement (ex: 'Mettre en place un bac de rétention').
           - 'preuve_attendue' : Est un DOCUMENT PHYSIQUE pour l'auditeur (ex: 'Certificat de conformité du bac' ou 'Photo de l'installation'). Ne pas répéter l'action ici.
        
        QUELS TEXTES APPLICABLES DOIVENT ÊTRE AJOUTÉS POUR UNE CONFORMITÉ TOTALE ?
        Réponds UNIQUEMENT en JSON : 
        [{{
            "titre": "...", 
            "date": "JJ/MM/AAAA (Format obligatoire)", 
            "type_texte": "Loi / Décret / Arrêté / Règlement UE",
            "criticite": "Haute / Moyenne / Basse", 
            "resume": "Justification complète dédiée à GDD", 
            "action": "L'action opérationnelle spécifique",
            "preuve_attendue": "Le document de preuve précis (ex: Facture, Registre, PV, BSD, Plan, etc.)"
        }}]
        """
        try:
            # On envoie la consigne à l'IA et on attend sa réponse
            resp = self.model.generate_content(prompt)
            # On transforme le texte renvoyé par l'IA en une vraie 'liste' Python utilisable par notre code
            return self._extract_json(resp.text)
        except Exception as e: 
            # Si Gemini plante (ex: problème de connexion), on affiche l'erreur et on renvoie une liste vide
            print(f"      [ERREUR IA AUDIT] {e}")
            return []

    def generate_keywords(self):
        """
        Demande à l'IA de générer des mots-clés pertinents pour faire des recherches sur Google.
        
        Returns:
            list: Une liste de mots-clés (ex: ["Déchets dangereux", "ICPE 2560"]).
        """
        print(f"   > Génération des mots-clés de veille via {self.model_name}...")
        prompt = f"""
        Directeur QHSE Expert. Génère 12 mots-clés Google précis pour la veille de GDD.
        Couvre : Environnement, SST, Produits/Qualité, RSE.
        
        CONTEXTE :
        {self.context}
        
        Réponds UNIQUEMENT en JSON : ["Mot clé 1", "Mot clé 2", ...]
        """
        try:
            # On envoie la consigne
            resp = self.model.generate_content(prompt)
            # On extrait la liste
            keywords = self._extract_json(resp.text)
            # On vérifie que c'est bien une liste avant de la renvoyer
            if isinstance(keywords, list): return keywords
            return []
        except Exception as e:
            print(f"      [ERREUR IA KEYWORDS] {e}")
            return []

    def search(self, q, num_results=10, search_api_key="", search_engine_id="", search_period='m1', tavily_api_key=""):
        # 1. TAVILY
        if tavily_api_key:
            print(f"      [TAVILY] Recherche pour '{q}' ({num_results} rêsults)...")
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": tavily_api_key,
                "query": q,
                "search_depth": "deep" if num_results > 10 else "basic",
                "max_results": num_results
            }
            try:
                res = requests.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    return [{"titre": r.get('title'), "snippet": r.get('content'), "url": r.get('url')} for r in data.get('results', [])]
            except: pass

        # 2. GOOGLE
        if not search_api_key: return []
        url = "https://www.googleapis.com/customsearch/v1"
        all_results = []
        for start_idx in range(1, num_results + 1, 10):
            params = {
                'q': q, 'key': search_api_key, 'cx': search_engine_id, 
                'start': start_idx
            }
            if search_period:
                params['dateRestrict'] = search_period
                
            try:
                res = requests.get(url, params=params)
                data = res.json()
                items = data.get('items', [])
                for i in items:
                    all_results.append({"titre": i.get('title'), "snippet": i.get('snippet'), "url": i.get('link')})
                if len(items) < 10: break
            except: break
        return all_results[:num_results]

    def analyze_news(self, text):
        prompt = f"""
        Rôle : Directeur QHSE Expert pour GDD.
        CONTEXTE STRATÉGIQUE : {self.context}
        
        MISSION : Évaluer si le TEXTE ci-dessous est PERTINENT pour la conformité de GDD.
        
        RÈGLES D'OR :
        - 'action' : Ce que l'usine doit CHANGER ou FAIRE.
        - 'preuve_attendue' : Ce que l'auditeur doit VOIR pour valider (Le document tangible).
        
        TEXTE : '{text}'
        
        RÉPONSE JSON UNIQUEMENT :
        {{
            "date": "JJ/MM/AAAA (Format obligatoire)",
            "type_texte": "Loi / Décret / Arrêté / Guide technique / Règlement UE",
            "theme": "...",
            "resume": "Pourquoi c'est important pour GDD",
            "action": "Action opérationnelle terrain précise",
            "criticite": "Haute / Moyenne / Basse / Non",
            "preuve_attendue": "DOCUMENT physique de preuve (ex: 'Registre incendie', 'Contrat prestataire', 'BSD n°...') "
        }}
        """
        try:
            resp = self.model.generate_content(prompt)
            res = self._extract_json(resp.text)
            if not isinstance(res, dict): return {"criticite": "Non"}
            return res
        except: return {"criticite": "Non"}

    def _extract_json(self, text):
        try:
            match = re.search(r'(\[.*\]|\{.*\})', text.replace('\n', ' '), re.DOTALL)
            if match: return json.loads(match.group(1))
            return json.loads(text)
        except: return []
