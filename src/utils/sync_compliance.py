"""
=============================================================================
SYNCHRONISATION DE LA CONFORMITÉ (Sync Compliance) - VEILLE GDD
=============================================================================

Ce script est un "pont" de données. 
Il va lire l'onglet 'Justifications' (où l'IA, souvent CamemBERT, a écrit ses propositions)
et copie intelligemment ces justifications dans la colonne "Preuve de Conformité Attendue" 
de notre "Base_Active".

Conçu pour être lu et maintenu par un profil Junior Data / Python.
"""

import os
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import sys

# Ajouter le chemin racine pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from src.core.pipeline import Config

def sync_compliance_data():
    """
    NOTE : Cette fonction est devenue obsolète suite à la fusion de l'onglet 'Justifications'
    directement dans les colonnes des onglets 'Base_Active' et 'Rapport_Veille_Auto'.
    """
    print("ℹ️  Mode Fusionné détecté : La synchronisation est désormais native dans le pipeline.")
    print("   > Aucune action complémentaire requise.")
    return

if __name__ == "__main__":
    sync_compliance_data()

