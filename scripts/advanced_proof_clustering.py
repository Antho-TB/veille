import sys
import os
import pandas as pd
import numpy as np
import mlflow
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

# Configuration MLflow
mlflow.set_tracking_uri("http://127.0.0.1:5050")
mlflow.set_experiment("Proof_Rationalization_DS")

# Simulation de l'extraction des données
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from utils.sync_server import get_spreadsheet, find_col

def run_clustering():
    with mlflow.start_run(run_name="Advanced_Clustering_TFIDF"):
        print("🚀 Démarrage du pipeline de Data Science avec Tracking MLflow...")
        
        ss = get_spreadsheet()
        ws = ss.worksheet('Base_Active')
        vals = ws.get_all_values()
        head = vals[0]
        rows = vals[1:]
        
        col = find_col(head, 'Preuve de Conformité Attendue') or 19
        raw_proofs = [r[col-1].strip() for r in rows if len(r) >= col and r[col-1].strip()]
        
        # 1. Nettoyage initial et dédoublonnage simple
        unique_raw = sorted(list(set(raw_proofs)))
        print(f"📊 Entrée : {len(unique_raw)} preuves uniques brutes.")
        mlflow.log_param("input_size", len(unique_raw))

        # 2. Vectorisation TF-IDF
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            stop_words=None,
            min_df=1
        )
        X = vectorizer.fit_transform(unique_raw)
        mlflow.log_param("ngram_range", (1, 3))

        # 3. Clustering Agglomératif
        dist_threshold = 0.5 
        mlflow.log_param("dist_threshold", dist_threshold)
        
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=dist_threshold,
            metric='cosine',
            linkage='average'
        )
        clusters = clustering.fit_predict(X.toarray())
        mlflow.log_metric("n_clusters", clustering.n_clusters_)
        mlflow.log_metric("reduction_rate", (1 - clustering.n_clusters_ / len(unique_raw)) * 100)

        # 4. Analyse des résultats
        df = pd.DataFrame({
            'raw': unique_raw,
            'cluster': clusters
        })

        summary = df.groupby('cluster')['raw'].apply(list).to_dict()
        
        # Suggestions de fusions majeures
        print("\n🧐 Analyse des clusters identifiés (log artifacts localement) :")
        fusions_count = 0
        for cid, members in summary.items():
            if len(members) > 1:
                fusions_count += 1
        
        mlflow.log_metric("fusions_detected", fusions_count)

        print(f"\n✅ Pipeline terminé.")
        print(f"📈 Potentiel de réduction : {len(unique_raw)} -> {clustering.n_clusters_} groupes.")
        
        # Export pour analyse par l'IA et MLflow
        artifact_path = 'proof_clusters_ds.csv'
        df.to_csv(artifact_path, index=False, encoding='utf-8-sig')
        mlflow.log_artifact(artifact_path)
        print(f"📦 Artefact loggé dans MLflow : {artifact_path}")

if __name__ == "__main__":
    run_clustering()
