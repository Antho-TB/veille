"""
=============================================================================
MOTEUR DE RECHERCHE VECTORIELLE (RAG) - VEILLE GDD
=============================================================================

Version optimisée pour l'IA : indexe également les résumés (snippets) 
pour une recherche sémantique plus puissante.

"""

import chromadb
import pandas as pd
from typing import List, Optional

class VectorEngine:
    """
    Gère le stockage et la recherche de textes par similarité sémantique.
    """
    def __init__(self, collection_name="veille_db"):
        # On utilise une base de données éphémère pour cet exemple, 
        # mais on pourrait la rendre persistante.
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(collection_name)

    def index(self, df: pd.DataFrame):
        """
        Indexation hybride : Titre + Résumé pour une meilleure précision.
        """
        if df.empty: return
        
        # Nettoyage
        df = df[df['titre'].notna() & (df['titre'] != "")]
        
        if self.collection.count() >= len(df): return 
        
        print(f"--- [VectorEngine] Indexation sémantique ({len(df)} docs) ---")
        
        # Senior Tip : On concatène le titre et le résumé pour "donner plus de contexte" à l'IA
        # On gère le fait que 'resume' ou 'snippet' n'existent pas forcément dans df_base
        texts_to_index = []
        for _, row in df.iterrows():
            content = f"{row['titre']}"
            if 'resume' in df.columns and str(row['resume']) != 'nan':
                 content += f" | {row['resume']}"
            elif 'snippet' in df.columns and str(row['snippet']) != 'nan':
                 content += f" | {row['snippet']}"
            texts_to_index.append(content)

        ids = [f"doc_{i}" for i in range(len(df))]
        metadatas = [{"url": str(row.get('url', ''))} for _, row in df.iterrows()]
        
        try:
            self.collection.upsert(
                documents=texts_to_index,
                metadatas=metadatas,
                ids=ids
            )
            print(f"      [OK] Base vectorielle à jour.")
        except Exception as e:
            print(f"      [!] Erreur ChromaDB : {e}")

    def is_duplicate(self, text: str, threshold: float = 0.85) -> bool:
        """
        Détecte si un texte est déjà présent sémantiquement dans la base.
        """
        if self.collection.count() == 0: return False
        
        try:
            results = self.collection.query(
                query_texts=[text],
                n_results=1
            )
            # Junior Tip : Plus la distance est petite, plus les textes sont proches.
            # Avec certain modèles, on utilise la 'distance' d'Euclide ou de Cosinus.
            if results['distances'] and results['distances'][0][0] < (1 - threshold):
                return True
            return False
        except:
            return False
