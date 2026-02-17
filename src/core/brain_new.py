import os
import json
import re
import requests
import google.generativeai as genai

class Brain:
    def __init__(self, context="", model_name='gemini-1.5-pro'):
        self.context = (context or "").strip()
        # Fallback intelligent des modèles
        self.model_name = model_name
        try:
            self.model = genai.GenerativeModel(model_name)
            # Test rapide
            self.model.generate_content("test", generation_config={"max_output_tokens": 10})
        except:
            print(f"      [!] Modèle {model_name} non disponible (404), repli sur gemini-2.0-flash.")
            try:
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                self.model_name = "gemini-2.0-flash"
            except:
                self.model = genai.GenerativeModel('gemini-pro')
                self.model_name = "gemini-pro"

    def audit_manquants(self, current_list):
        print(f"   > Audit de complétude exhaustif (Gap Analysis via {self.model_name})...")
        titles = "\n".join(current_list[:1500])  # Plus de titres
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
        
        QUELS TEXTES APPLICABLES DOIVENT ÊTRE AJOUTÉS POUR UNE CONFORMITÉ TOTALE ?
        Réponds UNIQUEMENT en JSON : [{{"titre": "...", "criticite": "Haute", "resume": "Justification complète dédiée à GDD", "action": "Action à mener"}}]
        """
        try:
            resp = self.model.generate_content(prompt)
            return self._extract_json(resp.text)
        except Exception as e: 
            print(f"      [ERREUR IA AUDIT] {e}")
            return []

    def generate_keywords(self):
        print(f"   > Génération des mots-clés de veille via {self.model_name}...")
        prompt = f"""
        Directeur QHSE Expert. Génère 12 mots-clés Google précis pour la veille de GDD.
        Couvre : Environnement, SST, Produits/Qualité, RSE.
        
        CONTEXTE :
        {self.context}
        
        Réponds UNIQUEMENT en JSON : ["Mot clé 1", "Mot clé 2", ...]
        """
        try:
            resp = self.model.generate_content(prompt)
            keywords = self._extract_json(resp.text)
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
                'dateRestrict': search_period, 'start': start_idx
            }
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
        Rôle : Directeur QHSE. Évalue l'impact de ce texte pour GDD.
        CONTEXTE GDD : {self.context}
        TEXTE : '{text}'
        Réponds UNIQUEMENT en JSON (type_texte, theme, date_texte, resume, action, criticite, preuve_attendue).
        Si non pertinent, criticite: "Non".
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
