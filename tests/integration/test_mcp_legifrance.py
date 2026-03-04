import asyncio
import os
import sys
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Charger les variables du fichier .env
env_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
load_dotenv(dotenv_path=env_path)

CLIENT_ID = os.environ.get("LEGIFRANCE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("LEGIFRANCE_CLIENT_SECRET", "").strip()

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ Erreur : Les clés LEGIFRANCE sont introuvables dans config/.env.")
    exit(1)

async def run_legifrance_mcp():
    # Définir le serveur (qui a été installé via pip, donc disponible dans le PATH)
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "server"],
        env={
            **os.environ,
            "LEGIFRANCE_CLIENT_ID": CLIENT_ID,
            "LEGIFRANCE_CLIENT_SECRET": CLIENT_SECRET
        }
    )
    
    print("🔗 Démarrage du Serveur MCP Légifrance Local...")
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("✅ Serveur démarré ! Initialisation de la session MCP...")
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("✅ Session MCP Légifrance initialisée avec succès.\n")
                
                # Lister les outils
                tools_response = await session.list_tools()
                print("🛠️ OUTILS DISPONIBLES SUR LE SERVEUR LÉGIFRANCE :")
                for tool in tools_response.tools:
                    print(f" 👉 Nom: {tool.name}")
                    print(f"    Description: {tool.description[:100]}...")
                    print("---")
                    
                # Tester l'outil de recherche (si search_legifrance existe)
                for tool in tools_response.tools:
                    if "search" in tool.name.lower() or "recherche" in tool.name.lower():
                        print(f"\n🔍 Exécution d'un test avec l'outil {tool.name} (mot d'ordre: 'ICPE')")
                        try:
                            # Tentative d'appel générique
                            result = await session.call_tool(tool.name, {"query": "ICPE"})
                            print("✅ Succès de l'appel ! Extrait du résultat :")
                            print(str(result.content)[:500])
                        except Exception as e:
                            print(f"⚠️ Appel de l'outil échoué (les arguments diffèrent peut-être) : {e}")
                        break
                        
    except Exception as e:
        print(f"❌ Erreur critique MCP : {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_legifrance_mcp())
