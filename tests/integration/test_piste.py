import os
import requests
from dotenv import load_dotenv

# Charger les variables du fichier .env
env_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
load_dotenv(dotenv_path=env_path)

CLIENT_ID = os.environ.get("LEGIFRANCE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("LEGIFRANCE_CLIENT_SECRET", "").strip()

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Erreur : Les clés LEGIFRANCE sont introuvables dans le fichier .env.")
    exit(1)

# 1. Obtenir le token OAuth2 de Piste
token_url = "https://oauth.piste.gouv.fr/api/oauth/token"
data = {
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": "openid"
}

print("🔄 Demande de Jeton OAuth2 au portail SANDBOX Piste.gouv.fr...")
response = requests.post(token_url, data=data)

if response.status_code == 200:
    token = response.json().get("access_token")
    print("✅ Jeton Oauth2 obtenu avec succès !")
    
    # 2. Tester une recherche sur Légifrance
    api_url = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app/search"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Recherche simple sur le mot-clé ICPE
    payload = {
        "recherche": {
             "typePagination": "DEFAUT",
             "pageSize": 1,
             "sort": "SIGNATURE_DATE_DESC",
             "criteres": [
                 {"typeRecherche": "MOTS_CLES", "valeur": "ICPE", "operateur": "ET"}
             ]
        }
    }
    
    print("\n🔄 Lancement d'une vraie recherche juridique sur 'ICPE'...")
    api_response = requests.post(api_url, headers=headers, json=payload)
    
    if api_response.status_code == 200:
        print("✅ RECHERCHE LÉGIFRANCE RÉUSSIE !")
        data = api_response.json()
        total = data.get("results", {}).get("totalResults", "Inconnu")
        print(f"📄 Nombre de lois/textes trouvés au total : {total}")
    else:
        print(f"❌ Erreur API Légifrance (Code {api_response.status_code}): {api_response.text}")

else:
    print(f"❌ Échec de l'authentification Piste (Code {response.status_code}): {response.text}")
