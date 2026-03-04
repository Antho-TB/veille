import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_mcp_client():
    # Définir le serveur : exécuter notre script Python mcp_legifrance.py
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["src/mcp/mcp_legifrance.py"]
        # L'environnement (clés) sera chargé automatiquement par le serveur (.env)
    )
    
    print("🤖 [IA Client] Allumage du Serveur LÉGIFRANCE (Sur-Mesure)...")
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            print("✅ [IA Client] Serveur allumé ! Phase d'initialisation...")
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("✅ [IA Client] Session MCP initialisée avec succès.\n")
                
                # 1. Demander au serveur quels outils il possède
                tools_response = await session.list_tools()
                print("🛠️  [IA Client] Découverte des outils disponibles :")
                for tool in tools_response.tools:
                    print(f" 👉 Nom de l'outil : {tool.name}")
                    print(f"    Description : {tool.description}")
                
                print("\n🔍 [IA Client] Je vais utiliser l'outil 'rechercher_loi_icpe' pour chercher le mot-clé 'Bruit'...")
                print("⏳ [IA Client] Attente de la réponse de Légifrance (via le Serveur MCP)...")
                
                # 2. Demander au serveur d'exécuter l'outil
                result = await session.call_tool("rechercher_loi_icpe", {"mot_cle": "Bruit"})
                
                print("\n✅ [IA Client] Résultat récupéré et traduit :\n")
                print("-" * 50)
                print(result.content[0].text)
                print("-" * 50)
                        
    except Exception as e:
        print(f"❌ [IA Client] Erreur de communication : {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_mcp_client())
