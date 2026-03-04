import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def run_mcp_test():
    server_url = "https://mcp.data.gouv.fr/mcp"
    print(f"🔗 Connexion au serveur MCP Data.gouv.fr : {server_url}")
    
    try:
        # Configuration des streams SSE
        async with sse_client(server_url) as (read_stream, write_stream):
            print("✅ Connexion SSE établie. Initialisation de la session MCP...")
            
            async with ClientSession(read_stream, write_stream) as session:
                # Initialisation du protocole
                await session.initialize()
                print("✅ Session MCP initialisée avec succès.\n")
                
                # Lister les outils disponibles
                tools_response = await session.list_tools()
                print("🛠️ OUTILS DISPONIBLES SUR LE SERVEUR :")
                for tool in tools_response.tools:
                    print(f" 👉 Nom: {tool.name}")
                    print(f"    Description: {tool.description}")
                    print(f"    Arguments attendus: {tool.inputSchema.get('properties', {})}")
                    print("---")
                    
    except Exception as e:
        print(f"❌ Erreur lors de la connexion MCP : {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_mcp_test())
