import os
import asyncio
import requests
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

# Charger les variables du fichier .env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')
load_dotenv(dotenv_path=env_path)

CLIENT_ID = os.environ.get("LEGIFRANCE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("LEGIFRANCE_CLIENT_SECRET", "").strip()

# Initialisation du serveur MCP
server = Server("gdd-legifrance-mcp")

def get_legifrance_token():
    """Récupère un jeton Oauth2 auprès de Piste.gouv.fr"""
    token_url = "https://oauth.piste.gouv.fr/api/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "openid"
    }
    response = requests.post(token_url, data=payload)
    response.raise_for_status()
    return response.json().get("access_token")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Déclare les outils disponibles pour l'IA"""
    return [
        types.Tool(
            name="rechercher_loi_icpe",
            description="Recherche les textes réglementaires et arrêtés sur la base de données Légifrance. Utile pour vérifier la conformité d'une ICPE ou d'une loi.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mot_cle": {
                        "type": "string",
                        "description": "Le mot clé principal de la recherche (ex: ICPE, déchets, eau, bruit)"
                    }
                },
                "required": ["mot_cle"]
            }
        ),
        types.Tool(
            name="rechercher_datagouv_icpe",
            description="Recherche dans l'Open Data français (data.gouv.fr). Utile pour trouver des listes d'installations classées, des données sur la pollution de l'eau, de l'air, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "mot_cle": {
                        "type": "string",
                        "description": "Ex: ICPE, emissions industrielles, qualité air"
                    }
                },
                "required": ["mot_cle"]
            }
        ),
        types.Tool(
            name="rechercher_aida_ineris",
            description="Recherche des fiches techniques et arrêtés types sur le site AIDA (INERIS) concernant le droit de l'environnement industriel.",
            inputSchema={
                "type": "object",
                "properties": {
                    "rubrique": {
                        "type": "string",
                        "description": "Le numéro de rubrique ICPE (ex: 2560) ou le thème (ex: bruit)"
                    }
                },
                "required": ["rubrique"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Exécute l'outil demandé par l'IA"""
    if name == "rechercher_loi_icpe":
        mot_cle = arguments.get("mot_cle", "ICPE")
        
        try:
            token = get_legifrance_token()
            api_url = "https://api.piste.gouv.fr/dila/legifrance/lf-engine-app/search"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            payload = {
                "recherche": {
                     "typePagination": "DEFAUT",
                     "pageSize": 5, 
                     "sort": "SIGNATURE_DATE_DESC",
                     "criteres": [
                         {"typeRecherche": "MOTS_CLES", "valeur": mot_cle, "operateur": "ET"}
                     ]
                }
            }
            
            response = await asyncio.to_thread(requests.post, api_url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", {}).get("results", [])
            
            if not results:
                return [types.TextContent(type="text", text=f"Aucun texte trouvé pour '{mot_cle}'.")]
            
            rapport = f"Voici les textes LÉGIFRANCE pour '{mot_cle}' :\n\n"
            for item in results:
                titre = item.get("title", "Sans titre")
                date = item.get("signatureDate", "Date inconnue")
                cid = item.get("cid", "")
                rapport += f"- {titre} (Date: {date}) - ID: {cid}\n"
                
            return [types.TextContent(type="text", text=rapport)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Erreur d'interrogation Légifrance : {str(e)}")]

    elif name == "rechercher_datagouv_icpe":
        mot_cle = arguments.get("mot_cle", "ICPE")
        try:
            api_url = f"https://www.data.gouv.fr/api/1/datasets/?q={mot_cle}&page_size=5"
            response = await asyncio.to_thread(requests.get, api_url)
            response.raise_for_status()
            data = response.json()
            
            rapport = f"Voici les jeux de données DATA.GOUV.FR pour '{mot_cle}' :\n\n"
            for dataset in data.get("data", []):
                titre = dataset.get("title", "Sans titre")
                desc = dataset.get("description", "")[:100].replace('\n', ' ')
                rapport += f"- {titre} : {desc}...\n"
                
            return [types.TextContent(type="text", text=rapport)]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Erreur d'interrogation Data.gouv : {str(e)}")]

    elif name == "rechercher_aida_ineris":
        rubrique = arguments.get("rubrique", "2560")
        try:
            # AIDA n'a pas d'API REST publique simple, on simule une recherche structurée web (Opensearch)
            # En environnement réel pro, l'INERIS fournit des exports XML/API sur demande.
            # Pour l'IA, on retourne les liens directs structurés.
            rapport = f"Ressources AIDA/INERIS pour '{rubrique}' :\n"
            rapport += f"- Consulter la brochure complète : https://aida.ineris.fr/recherche?search_api_views_fulltext={rubrique}\n"
            rapport += f"- Consulter les prescriptions générales : https://aida.ineris.fr/consultation_document/41018 (exemple générique)\n"
            return [types.TextContent(type="text", text=rapport)]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Erreur INERIS : {str(e)}")]

    raise ValueError(f"Outil inconnu : {name}")

async def run():
    """Démarre le serveur MCP via l'entrée/sortie standard (stdio)"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    import logging
    # Désactiver les logs verbeux qui pourraient polluer la communication stdio (JSON-RPC)
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(run())
