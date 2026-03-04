"""
=============================================================================
GESTIONNAIRE DE CONFIGURATION - VEILLE GDD
=============================================================================

Ce module centralise tous les paramètres de l'application. 
En tant que développeur "Junior", il est important de ne jamais écrire 
des mots de passe ou des clés API directement dans le code. 
On utilise donc un fichier caché nommé '.env' et la bibliothèque 'dotenv' 
pour charger ces secrets de manière sécurisée.

"""

import os
from dotenv import load_dotenv

# Junior Tip : Charger les variables d'environnement dès le début
# On cherche le fichier .env dans le dossier 'config' à la racine du projet
ENV_PATH = os.path.join(os.path.dirname(__file__), "../../config/.env")
load_dotenv(dotenv_path=ENV_PATH)

class Config:
    """
    Objet de configuration centralisé.
    Utilisé partout dans l'application pour accéder aux clés et réglages.
    """
    
    # --- SECRETS (Clés API) ---
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "VOTRE_CLE_GEMINI")
    SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "VOTRE_CLE_SEARCH")
    SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID", "VOTRE_CX")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    
    # --- GOOGLE SHEETS & DRIVE ---
    SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
    # Junior Tip : Utiliser des chemins absolus calculés pour éviter les erreurs de dossier
    CREDENTIALS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/credentials.json"))
    
    # --- PARAMÈTRES RÉSEAU ---
    EMAIL_SENDER = "a.bezille@tb-groupe.fr"
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    
    # --- RÉGLAGES MÉTIER (VEILLE) ---
    RUN_FULL_AUDIT = True    
    SEARCH_PERIOD = 'm1' # 'm1' = 1 mois, 'w1' = 1 semaine
    SEARCH_MAX_RESULTS = 10
    
    # --- IA & MODÈLES ---
    # Senior Tip : On utilise des constantes pour les noms de modèles
    MODEL_NAME = "models/gemini-2.5-flash" # Modèle de pointe
    MLFLOW_TRACKING = True
    
    # --- CONTEXTE DYNAMIQUE ---
    # ID du Google Doc contenant la Fiche Descriptive Detaillee (Identite GDD)
    CONTEXT_DOC_ID = "1N23617Z17RR8UUZ7qg_dnVWR9Uevl8ks6n3J-Bt28uw"

def check_config():
    """Vérification basique de la présence des fichiers essentiels"""
    if not os.path.exists(Config.CREDENTIALS_FILE):
        print(f"⚠️ ATTENTION : Le fichier credentials.json est introuvable à {Config.CREDENTIALS_FILE}")
        return False
    return True

if __name__ == "__main__":
    # Test local
    print("--- Test de Configuration ---")
    if check_config():
        print(f"✅ Configuration OK. Modèle utilisé : {Config.MODEL_NAME}")
    else:
        print("❌ Erreur de configuration.")
