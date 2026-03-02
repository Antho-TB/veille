"""
=============================================================================
MOTEUR DE RECHERCHE VECTORIELLE (MOCK) - VEILLE GDD
=============================================================================
Version de secours sans chromadb pour compatibilité Azure Functions.
"""

import pandas as pd
from typing import List, Optional

class VectorEngine:
    """
    Mock de VectorEngine pour éviter la dépendance chromadb sur Azure.
    """
    def __init__(self, collection_name="veille_db"):
        print("--- [VectorEngine] Mode MOCK activé (SANS CHROMADB) ---")

    def index(self, df: pd.DataFrame):
        print("--- [VectorEngine] Indexation (Passée en mode MOCK) ---")
        pass

    def is_duplicate(self, text: str, threshold: float = 0.85) -> bool:
        # Toujours considérer comme non-doublon en mode dégradé
        return False
