import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def _run_mcp_queries(keywords):
    """
    Exécute les outils du MCP Serveur (Légifrance, Data.gouv, INERIS) 
    pour une liste de mots-clés de manière asynchrone.
    """
    # Le chemin du serveur doit être absolu ou relatif depuis la racine du projet
    server_script = os.path.join(os.path.dirname(__file__), "mcp_legifrance.py")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script]
    )
    
    results = []
    
    try:
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                for k in keywords:
                    if not k: continue
                    print(f"      > Interrogation MCP pour : {k}")
                    
                    # 1. Légifrance (Textes de loi)
                    try:
                        res_legi = await session.call_tool("rechercher_loi_icpe", {"mot_cle": k})
                        if res_legi.content and "Erreur" not in res_legi.content[0].text:
                            # On convertit le résultat en format "news Google" pour le pipeline
                            results.append({
                                "titre": f"Légifrance [Officiel] - {k}", 
                                "snippet": res_legi.content[0].text[:1000], # Garder un résumé pour l'IA
                                "url": "https://legifrance.gouv.fr",
                                "source_type": "Institutionnel"
                            })
                    except Exception as e:
                        pass
                        
                    # 2. Data.gouv (Données publiques)
                    try:
                        res_dg = await session.call_tool("rechercher_datagouv_icpe", {"mot_cle": k})
                        if res_dg.content and "Erreur" not in res_dg.content[0].text:
                            results.append({
                                "titre": f"Data.gouv [Officiel] - {k}", 
                                "snippet": res_dg.content[0].text[:1000], 
                                "url": "https://data.gouv.fr",
                                "source_type": "Institutionnel"
                            })
                    except Exception as e:
                        pass
                        
                    # 3. AIDA INERIS (Fiches techniques expertes)
                    try:
                        res_aida = await session.call_tool("rechercher_aida_ineris", {"rubrique": k})
                        if res_aida.content and "Erreur" not in res_aida.content[0].text:
                            results.append({
                                "titre": f"AIDA INERIS [Officiel] - {k}", 
                                "snippet": res_aida.content[0].text[:1000], 
                                "url": "https://aida.ineris.fr",
                                "source_type": "Expertise"
                            })
                    except Exception as e:
                        pass
                        
    except Exception as e:
        print(f"      [!] Erreur interne Client MCP : {str(e)}")
        
    return results

def get_mcp_results(keywords):
    """Point d'entrée synchrone pour le Pipeline principal"""
    return asyncio.run(_run_mcp_queries(keywords))
