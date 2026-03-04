import sys
import os
import json
import traceback

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.brain_new import Brain
from src.core.config_manager import Config
from src.core.pipeline import fetch_dynamic_context

def main():
    print("--- Démarrage du Filtrage Strict APORA (Sans Informatif) ---")
    
    # Récupérer le contexte GDD
    dyn_context = fetch_dynamic_context(Config.CONTEXT_DOC_ID)
    contexte_final = dyn_context if dyn_context else "Contexte par défaut"
    
    brain = Brain(context=contexte_final, model_name=Config.MODEL_NAME)
    
    # Données brutes issues du web scraping APORA exhaustif
    apora_texts = [
        "Règlement (UE) 2025/2083 (13 Fév 2026) - Renforcement du mécanisme d’ajustement carbone aux frontières (MACF).",
        "Règlement d’exécution (UE) 2025/1893 (06 Fév 2026) - Attestations de formation pour les gaz fluorés.",
        "Arrêté du 23 décembre 2025 (30 Jan 2026) - Frais de tenue de compte des quotas (SEQE).",
        "Décret n° 2024-1052 (29 Avr 2025) - Restauration de la biodiversité.",
        "Règlement (UE) 2024/1834 (06 Déc 2024) - Écoconception des ventilateurs.",
        "Règlement (UE) 2024/2462 (08 Nov 2024) - Restriction REACH sur le PFHxA.",
        "Arrêtés du 2 décembre 2025 (03 Mar 2026) - Cahier des charges REP emballages professionnels.",
        "Arrêtés du 13 août 2025 et suiv. (13 Fév 2026) - Modification de la filière REP TLC (textiles).",
        "Règlement (UE) 2025/2365 (16 Jan 2026) - Prévention des pertes de granulés plastiques (microplastiques).",
        "Décret n°2026-23 (23 Fév 2026) - Trajectoire de réchauffement de référence pour l'adaptation.",
        "Décret n° 2025-1376 (30 Jan 2026) - Prévention des risques liés à l'exposition aux PFAS.",
        "Décret n° 2025-1287 (23 Fév 2026) - Sécurité sanitaire des Eaux Destinées à la Consommation Humaine (EDCH).",
        "Arrêté du 17 décembre 2025 (13 Fév 2026) - Liste des substances pour la redevance pollutions diffuses.",
        "Décret n° 2025-884 (24 Nov 2025) - Travaux de sondage ou forage non domestiques.",
        "Décret n° 2026-45 (03 Mar 2026) - Procédures relatives aux installations temporaires ICPE.",
        "Instruction du 23 décembre 2025 (30 Jan 2026) - Actions nationales 2026 de l’inspection ICPE.",
        "Règlement (UE) 2025/1988 (16 Jan 2026) - Restriction des PFAS dans les mousses anti-incendie.",
        "Décret n° 2025-1382 (23 Fév 2026) - Transposition de la directive efficacité énergétique (2023/1791).",
        "Arrêté du 10 juillet 2025 (05 Nov 2025) - Modalités de réalisation de l’audit énergétique en entreprise.",
        "Arrêté du 19 juin 2025 (03 Mar 2026) - Modification des programmes de Certificats d’Économies d’Énergie (CEE).",
        "Arrêté du 28 novembre 2023 (02 Fév 2024) - Actions de réduction de consommation (Décret Tertiaire)."
    ]
    
    results_retenus = []
    
    for i, text in enumerate(apora_texts):
        print(f"\n[{i+1}/{len(apora_texts)}] Analyse de : {text[:60]}...")
        try:
            res = brain.analyze_news(text)
            crit = res.get('criticite', 'Non')
            
            # FILTRAGE STRICT GDD (Ni Non, Ni Informatif)
            if crit not in ["Non", "Informatif"]:
                print(f"   => ✅ RETENU (Criticité: {crit}) | Action: {res.get('action')}")
                results_retenus.append({
                    "texte_original": text,
                    "analyse": res
                })
            else:
                print(f"   => ❌ REJETÉ (Criticité: {crit})")
        except Exception as e:
            print(f"   => ⚠️ Erreur: {e}")
            traceback.print_exc()

    print(f"\n--- BILAN GDD ---")
    print(f"Textes initiaux (fournis par APORA) : {len(apora_texts)}")
    print(f"Textes applicables pour l'usine GDD : {len(results_retenus)}")
    
    with open("output/apora_filtered.json", "w", encoding="utf-8") as f:
        json.dump(results_retenus, f, indent=4, ensure_ascii=False)
    
    print("\nResultats sauvegardes dans 'output/apora_filtered.json'")

if __name__ == "__main__":
    main()
