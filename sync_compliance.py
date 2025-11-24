# ---------------------------------------------------------------------------
# Synchronisation de la Conformité - Veille Réglementaire
# ---------------------------------------------------------------------------
# Ce script automatise le flux de travail :
# 1. Détecte les lignes évaluées dans le Rapport de Veille.
# 2. Les déplace vers la Base Active.
# ---------------------------------------------------------------------------

import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
from pipeline_veille import Config
import os

# --- CONFIGURATION ---
SOURCE_SHEET = "Rapport_Veille_Auto"
TARGET_SHEET = "Base_Active"

class ComplianceSync:
    def __init__(self):
        self.client = None
        self.sheet = None

    def connect(self):
        if not os.path.exists(Config.CREDENTIALS_FILE):
            raise FileNotFoundError("Manque credentials.json")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope))
        self.sheet = self.client.open_by_key(Config.SHEET_ID)

    def sync(self):
        print("--- Synchronisation de la conformité ---")
        if not self.client: self.connect()
        
        try:
            ws_source = self.sheet.worksheet(SOURCE_SHEET)
            ws_target = self.sheet.worksheet(TARGET_SHEET)
        except Exception as e:
            print(f"Erreur d'accès aux onglets : {e}")
            return

        # Récupération des données
        records_source = ws_source.get_all_records()
        if not records_source:
            print("Aucune donnée dans le rapport.")
            return
            
        df_source = pd.DataFrame(records_source)
        
        # Colonnes clés
        col_last_eval = "date de la dernère évaluation"
        
        # Vérification existence colonnes
        if col_last_eval not in df_source.columns:
            print(f"Colonne '{col_last_eval}' introuvable dans la source.")
            return

        # Lignes à déplacer (celles qui ont une date d'évaluation remplie)
        # On filtre les dates non vides
        to_move_mask = df_source[col_last_eval].astype(str).str.strip() != ""
        rows_to_move = df_source[to_move_mask].copy()
        
        if rows_to_move.empty:
            print("Aucune ligne évaluée à déplacer.")
            return

        print(f"   > {len(rows_to_move)} lignes identifiées comme évaluées.")

        # Préparation des données pour la cible
        # On s'assure que les colonnes correspondent à Base_Active
        
        # On récupère les headers de la cible pour l'ordre
        target_headers = ws_target.row_values(1)
        
        # On prépare la liste de listes à ajouter
        data_to_append = []
        for _, row in rows_to_move.iterrows():
            new_row = []
            for header in target_headers:
                val = row.get(header, "")
                # Conversion en string pour éviter erreurs JSON
                new_row.append(str(val))
            data_to_append.append(new_row)

        # Ajout dans Base_Active
        if data_to_append:
            ws_target.append_rows(data_to_append)
            print(f"   > {len(data_to_append)} lignes ajoutées à {TARGET_SHEET}.")

            # Suppression des lignes dans la source
            # Attention : supprimer des lignes en itérant peut décaler les index.
            # Il vaut mieux supprimer du bas vers le haut ou re-uploader le dataframe filtré.
            # Option sûre : Re-uploader le dataframe SANS les lignes déplacées.
            
            df_remaining = df_source[~to_move_mask]
            
            # On efface tout le contenu (sauf header) et on réécrit
            ws_source.clear()
            # On remet les headers
            ws_source.append_row(df_source.columns.tolist())
            # On remet les données restantes
            if not df_remaining.empty:
                ws_source.append_rows(df_remaining.astype(str).values.tolist())
            
            print(f"   > {SOURCE_SHEET} mis à jour (lignes déplacées supprimées).")

if __name__ == "__main__":
    syncer = ComplianceSync()
    syncer.sync()
