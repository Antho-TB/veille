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
        """
        Analyse la completude de la base actuelle par rapport au contexte usine.
        Le modele compare ce qui est deja en base avec les obligations theoriques
        decoulant de la fiche d'identite GDD.
        """
        print(f"   > Audit Gap Analysis via {self.model_name}...")
        # On limite la liste pour eviter de depasser la fenetre de contexte du modele
        titles = "\n".join(current_list[:500]) 
        
        prompt = f"""
        Expert QHSE. MISSION : Identifier les textes reglementaires manquants pour l'usine GDD.
        CONTEXTE USINE (Fiche d'identite) : {self.context}
        BASE ACTUELLE : {titles}
        
        HISTORIQUE AUDIT ISO 14001 (A PRIORISER) :
        - Le dernier audit (DNV) a releve des faiblesses sur la consommation energetique (Manque de suivi du Decret Tertiaire, Groupes froids non evalues).
        - Cherche imperativement si des textes sur l'efficacite energetique et les F-Gas sont manquants dans la BASE ACTUELLE.
        
        CONSIGNES :
        1. Identifie 10 textes MAJEURS manquants (Lois, Decrets, Arretes). Focus sur l'Energie, ICPE 2560, REACH, Dechets.
        2. Pour chaque texte, identifie precisement :
           - 'titre' et 'numero' (ex: Decret n°2024-123).
           - 'date' : Date de publication.
           - 'criticite' : Selon la methode KPR (Haute, Moyenne, Basse).
           - 'action' : L'action concrete attendue (ex: "Realiser l'audit energetique").
           - 'preuve_attendue' : Le document TANGIBLE.
        
        Reponds uniquement en JSON : [{{"titre": "...", "numero": "...", "date": "...", "type_texte": "...", "criticite": "...", "resume": "...", "action": "...", "preuve_attendue": "..."}}]
        """
        try:
            resp = self.model.generate_content(prompt)
            return self._extract_json(resp.text)
        except Exception as e:
            print(f"      [!] Erreur Audit : {e}")
            return []

    def generate_keywords(self) -> List[str]:
        """
        Genere des mots-cles optimises pour la recherche Google.
        Les mots-cles sont bases sur le contexte specifique de GDD (ICPE, metaux).
        """
        prompt = f"""
        Directeur QHSE. Genere 12 mots-cles Google Strategiques pour la veille de GDD.
        Focus : Obligations globales de la norme ISO 14001, Environnement, Securite (SST), ICPE. (Par exemple et non exclusif : obligations APORA, CSRD, REACH, energie, dechets, bruit, rejets).
        CONTEXTE USINE : {self.context}
        Reponds au format JSON : ["mot-cle 1", "mot-clle 2", ...]
        """
        try:
            resp = self.model.generate_content(prompt)
            return self._extract_json(resp.text)
        except Exception:
            return ["ICPE 2560", "Decoupage metaux reglementation", "Dechets industriels metaux"]

    def analyze_news(self, text: str) -> Dict:
        """
        Evalue la pertinence et la criticite d'un texte trouve sur le web.
        Cette fonction decide si le texte doit etre en base 'Active', 'Informative' ou jete (Bruit).
        """
        prompt = f"""
        Role : Directeur QHSE Expert GDD.
        CONTEXTE USINE : {self.context}
        EVALUE CE TEXTE : "{text}"
        
        MISSION : Determiner l'applicabilite, la criticite et l'action requise pour le site industriel.
        
        HISTORIQUE AUDIT ISO 14001 :
        Garde une vision 360 degres et exhaustive sur **TOUTE la conformite reglementaire ISO 14001** exigee pour une entreprise industrielle. 
        A titre de simple exemple d'anciennes alertes (et non exhaustif) : une vigilance avait ete demandee anciennement sur l'Energie (Decret Tertiaire) et les Dechets.
        
        REGLE DE TRI :
        - SOIS EXHAUSTIF : Retiens un maximum de textes applicables de pres ou de loin a l'entreprise (ICPE, Energie, Securite...), classe-les plutot en 'Basse' ou 'Informatif' plutot que de les rejeter.
        - Ne mets en criticite 'Non' (Bruit) QUE si le texte est TOTALEMENT hors-sujet ou etranger au perimetre (ex: reglementation maritime nucleaire). Tous les autres textes industriels, environnementaux ou energetiques doivent etre gardes.
        
        CRITERES DE CRITICITE (KPR) :
        - Haute : Risque penal, arret d'activite ou modification majeure d'arrete ICPE.
        - Moyenne : Obligation de reporting technique, investissement modere ou risque de non-conformite majeure en audit.
        - Basse : Mise a jour administrative mineure ou piste d'amelioration.
        
        CONSIGNE TECHNIQUE (JSON) :
        - 'numero' : Extraire le N° officiel (ex: Decret 2026-23).
        - 'preuve_attendue' : Doit etre un document TANGIBLE (ex: Registre, Certificat, Audit energetique).
        - 'theme' : DOIT etre parmi ces categories APORA : [Air, Bruits et vibrations, Dechets, Eau, Fiscalite, ICPE, Management de l'Environnement, Risques, Sites et sols pollues, Management de l'Energie, Mecanismes economiques, Production d'Energie, Reglementation thermique, Utilisation de l'Energie, Securite].
        
        Reponds au format JSON : {{
            "numero": "...", "date": "...", "type_texte": "...", "theme": "...", 
            "resume": "...", "action": "...", "criticite": "...", "preuve_attendue": "...", "justification": "..."
        }}
        """
        try:
            resp = self.model.generate_content(prompt)
            data = self._extract_json(resp.text)
            # Si l'IA repond 'Non', on ignore le texte (Bruit)
            if data.get('criticite') == 'Non':
                return {"criticite": "Non"}
            return data if isinstance(data, dict) else {"criticite": "Non"}
        except:
            return {"criticite": "Non"}

    def search(self, q: str, num_results: int, search_api_key: str, search_engine_id: str, search_period: str, tavily_api_key: str = None) -> list:
        """
        Effectue une recherche sur le web via l'API Google Custom Search.
        """
        import requests
        from datetime import datetime
        print(f"      [Recherche Google] {q}")
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": search_api_key,
            "cx": search_engine_id,
            "q": q,
            "num": min(10, num_results)
        }
        
        if search_period == "m1":
            params["dateRestrict"] = "m[1]"
        elif search_period == "w1":
            params["dateRestrict"] = "w[1]"

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("items", []):
                results.append({
                    "titre": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "date": datetime.now().strftime("%d/%m/%Y")
                })
            return results
        except Exception as e:
            print(f"      [!] Erreur recherche Google Custom Search : {e}")
            return []
