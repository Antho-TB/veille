import sys
import os
import pandas as pd
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
import mlflow

# Configuration MLflow
mlflow.set_tracking_uri("http://127.0.0.1:5050")
mlflow.set_experiment("Semantic_Audit_CamemBERT")

# Simulation de l'extraction des données
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from utils.sync_server import get_spreadsheet, find_col, normalize_proof_label

def run_semantic_audit():
    with mlflow.start_run(run_name="CamemBERT_HITL_Audit"):
        print("🔍 Lancement de l'Audit Sémantique (CamemBERT / Sentence-Transformers)...")
        
        # 1. Chargement des données
        ss = get_spreadsheet()
        ws = ss.worksheet('Base_Active')
        vals = ws.get_all_values()
        head = vals[0]
        rows = vals[1:]
        
        col_idx = find_col(head, 'Preuve de Conformité Attendue') or 19
        raw_proofs = sorted(list(set([r[col_idx-1].strip() for r in rows if len(r) >= col_idx and r[col_idx-1].strip()])))
        
        print(f"📊 {len(raw_proofs)} preuves uniques à analyser.")
        mlflow.log_param("unique_proofs_count", len(raw_proofs))

        # 2. Chargement du modèle (Modèle multilingue optimisé pour le français)
        # On utilise paraphrase-multilingual car il est plus léger et performant pour la similarité sémantique pure
        model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
        print(f"🚀 Chargement du modèle {model_name}...")
        model = SentenceTransformer(model_name)
        mlflow.log_param("model_name", model_name)

        # 3. Génération des Embeddings
        print("🧠 Génération des vecteurs sémantiques...")
        embeddings = model.encode(raw_proofs, convert_to_tensor=True)
        
        # 4. Calcul de la similarité Cosinus
        cosine_scores = util.cos_sim(embeddings, embeddings)
        
        # 5. Extraction des paires à haute similarité (Audit)
        suggestions = []
        threshold = 0.85
        mlflow.log_param("similarity_threshold", threshold)

        for i in range(len(raw_proofs)):
            for j in range(i + 1, len(raw_proofs)):
                score = cosine_scores[i][j].item()
                if score >= threshold:
                    # On vérifie si notre heuristique actuelle les fusionne déjà
                    p1, p2 = raw_proofs[i], raw_proofs[j]
                    norm1 = normalize_proof_label(p1)
                    norm2 = normalize_proof_label(p2)
                    
                    already_merged = (norm1 == norm2)
                    
                    suggestions.append({
                        "proof_A": p1,
                        "proof_B": p2,
                        "similarity": round(score, 4),
                        "already_merged_by_heuristic": already_merged,
                        "suggested_canonical": norm1 if len(norm1) < len(norm2) else norm2
                    })

        df_suggestions = pd.DataFrame(suggestions).sort_values(by="similarity", ascending=False)
        
        # 6. Filtrage pour l'arbitrage humain (HITL)
        # On se concentre sur ce que l'heuristique n'a PAS vu
        hitl_candidates = df_suggestions[df_suggestions['already_merged_by_heuristic'] == False]
        
        print(f"💡 {len(hitl_candidates)} fusions potentielles détectées par l'Intelligence Artificielle.")
        mlflow.log_metric("new_fusions_suggested", len(hitl_candidates))

        # Export du rapport
        report_path = 'camembert_hits_for_arbitrage.csv'
        hitl_candidates.to_csv(report_path, index=False, encoding='utf-8-sig')
        mlflow.log_artifact(report_path)
        
        print(f"\n✅ Audit terminé. Rapport généré : {report_path}")
        print("👉 Veuillez consulter ce fichier pour valider les fusions suggérées.")

if __name__ == "__main__":
    run_semantic_audit()
