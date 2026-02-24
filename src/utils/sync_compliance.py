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
    Synchronise les données de l'onglet 'Justifications' (IA) 
    vers les onglets 'Base_Active' et 'Rapport_Veille_Auto'.
    """
    print("🔄 Démarrage de la synchronisation de la conformité...")
    # 1. Connexion (Création du pont)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(Config.SHEET_ID)
    
    # 2. Charger les Justifications IA (Lecture de la source)
    try:
        ws_justif = sheet.worksheet('Justifications')
        df_justif = pd.DataFrame(ws_justif.get_all_records())
    except:
        print("❌ Onglet 'Justifications' introuvable. Rien à synchroniser.")
        return

    # --- 3. Synchroniser avec Base_Active (Écriture dans la cible) ---
    print("📋 Mise à jour de 'Base_Active'...")
    ws_base = sheet.worksheet('Base_Active')
    df_base = pd.DataFrame(ws_base.get_all_records())
    
    # Normalisation des noms de colonnes (on enlève les espaces vides autour)
    df_base.columns = [c.strip() for c in df_base.columns]
    
    # On crée une liste avec tous les titres pour pouvoir chercher rapidement (comme un index de dictionnaire)
    base_titles = df_base['Intitulé'].str.strip().tolist()
    
    # Préparation des mises à jour globales (on envoie tout d'un coup à Google pour être plus rapide)
    # On cherche d'abord le numéro de la colonne 'Preuve de Conformité Attendue'
    try:
        header = ws_base.row_values(1)
        if 'Preuve de Conformité Attendue' not in header:
            print("➕ Ajout de la colonne 'Preuve de Conformité Attendue'...")
            ws_base.update_cell(1, len(header) + 1, 'Preuve de Conformité Attendue')
            header.append('Preuve de Conformité Attendue')
        
        preuve_col_idx = header.index('Preuve de Conformité Attendue') + 1
        
        updates = []
        for _, row_j in df_justif.iterrows():
            titre_j = str(row_j.get('Titre du texte', '')).strip()
            justif_ia = row_j.get('Justification Proposée (IA)', '')
            
            if titre_j in base_titles:
                row_idx = base_titles.index(titre_j) + 2 # +1 header, +1 0-index
                updates.append({
                    'range': gspread.utils.rowcol_to_a1(row_idx, preuve_col_idx),
                    'values': [[justif_ia]]
                })
        
        if updates:
            print(f"   > Envoi de {len(updates)} justifications vers Base_Active...")
            ws_base.batch_update(updates)
            
    except Exception as e:
        print(f"❌ Erreur lors du sync Base_Active : {e}")

    print("✅ Synchronisation terminée.")

if __name__ == "__main__":
    sync_compliance_data()
