"""
=============================================================================
LE CERVEAU (IA) - VEILLE GDD
=============================================================================

Ce module contient toute la logique liée à l'Intelligence Artificielle. 
Il utilise les modèles de Google (Gemini) pour comprendre les textes 
réglementaires et juger s'ils sont applicables à l'usine.

En tant que développeur MLE, nous utilisons des "Prompts" (consignes) 
très précises pour guider l'IA vers les bonnes réponses.

"""

import os
import json
import re
import time
import requests
from typing import List, Dict, Any, Optional # Senior Tip : Utiliser des Type Hints
import google.generativeai as genai
from src.core.config_manager import Config

class Brain:
    """
    Classe regroupant toute l'intelligence artificielle et la recherche web.
    """
    def __init__(self, context: str = "", model_name: str = Config.MODEL_NAME):
        """
        Initialisation du cerveau avec le contexte métier de l'usine.
        """
        self.context = context.strip()
        self.model_name = model_name
        
        # Initialisation de l'API Google
        if Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)
        
        try:
            # On s'assure que le nom commence par 'models/'
            full_name = model_name if model_name.startswith("models/") else f"models/{model_name}"
            self.model = genai.GenerativeModel(full_name)
            print(f"      [Brain] Modèle {full_name} activé.")
        except Exception as e:
            print(f"      [!] Erreur modèle {model_name} : {e}. Revers vers gemini-pro.")
            self.model = genai.GenerativeModel('models/gemini-pro')

    def _extract_json(self, text: str) -> Any:
        """Helper pour extraire proprement du JSON d'une réponse de l'IA"""
        try:
            # On cherche le premier bloc [ ] ou { }
            match = re.search(r'(\[.*\]|\{.*\})', text.replace('\n', ' '), re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return json.loads(text)
        except Exception:
            return {}

    def audit_manquants(self, current_list: List[str]) -> List[Dict]:
        """Analyse la complétude de la base actuelle"""
        print(f"   > Audit Gap Analysis via {self.model_name}...")
        titles = "\n".join(current_list[:500]) # On limite pour ne pas saturer le contexte
        
        prompt = f"""
        Expert QHSE. MISSION : Identifier les textes réglementaires manquants pour l'usine GDD.
        CONTEXTE USINE : {self.context}
        BASE ACTUELLE : {titles}
        
        CONSIGNES :
        1. Identifie 10 textes MAJEURS manquants (Lois, Décrets, Arrêtés).
        2. Focus sur : Découpage métaux, ICPE 2560, REACH, Déchets, SST.
        3. Pour 'action', décris ce que l'usine doit FAIRE.
        4. Pour 'preuve_attendue', décris le DOCUMENT à montrer à l'auditeur.
        
        Réponds uniquement en JSON : [{{"titre": "...", "date": "...", "type_texte": "...", "criticite": "...", "resume": "...", "action": "...", "preuve_attendue": "..."}}]
        """
        try:
            resp = self.model.generate_content(prompt)
            return self._extract_json(resp.text)
        except Exception as e:
            print(f"      [!] Erreur Audit : {e}")
            return []

    def generate_keywords(self) -> List[str]:
        """Génère des mots-clés optimisés pour la recherche Google"""
        prompt = f"""
        Directeur QHSE. Génère 12 mots-clés Google pour la veille de GDD.
        Focus : Nouvelles lois Environnement, SST, ICPE métaux.
        CONTEXTE : {self.context}
        Réponds au format JSON : ["mot-clé 1", "mot-clé 2", ...]
        """
        try:
            resp = self.model.generate_content(prompt)
            return self._extract_json(resp.text)
        except Exception:
            return ["ICPE 2560", "Déchets industriels métaux"]

    def search(self, q: str, num_results: int = 10, **kwargs) -> List[Dict]:
        """Effectue une recherche Web via Tavily ou Google Custom Search"""
        # --- Priorité TAVILY (Plus performant pour l'IA) ---
        t_key = kwargs.get('tavily_api_key', Config.TAVILY_API_KEY)
        if t_key:
            url = "https://api.tavily.com/search"
            payload = {"api_key": t_key, "query": q, "search_depth": "basic", "max_results": num_results}
            try:
                res = requests.post(url, json=payload, timeout=10)
                if res.status_code == 200:
                    return [{"titre": r['title'], "snippet": r['content'], "url": r['url']} for r in res.json().get('results', [])]
            except: pass

        # --- Fallback GOOGLE (Plus stable) ---
        g_key = kwargs.get('search_api_key', Config.SEARCH_API_KEY)
        g_cx = kwargs.get('search_engine_id', Config.SEARCH_ENGINE_ID)
        if not g_key or not g_cx: return []

        url = "https://www.googleapis.com/customsearch/v1"
        try:
            params = {'q': q, 'key': g_key, 'cx': g_cx, 'num': num_results}
            if kwargs.get('search_period'): params['dateRestrict'] = kwargs['search_period']
            res = requests.get(url, params=params, timeout=10)
            items = res.json().get('items', [])
            return [{"titre": i['title'], "snippet": i['snippet'], "url": i['link']} for i in items]
        except: return []

    def analyze_news(self, text: str) -> Dict:
        """Évalue la pertinence d'un texte trouvé pour l'usine GDD"""
        prompt = f"""
        Rôle : Directeur QHSE Expert.
        CONTEXTE USINE : {self.context}
        ÉVALUE CE TEXTE : "{text}"
        
        MISSION : Déterminer la criticité (Haute, Moyenne, Basse, Non) et l'action requise.
        CONSIGNE CRITIQUE : 'preuve_attendue' doit être un document TANGIBLE (ex: Registre, Certificat).
        
        Réponds au format JSON : {{
            "date": "...", "type_texte": "...", "theme": "...", "resume": "...", 
            "action": "...", "criticite": "...", "preuve_attendue": "..."
        }}
        """
        try:
            resp = self.model.generate_content(prompt)
            data = self._extract_json(resp.text)
            return data if isinstance(data, dict) else {"criticite": "Non"}
        except:
            return {"criticite": "Non"}
