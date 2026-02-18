import os
import sys
import pandas as pd
import gspread
import time
import re
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

def move_informative_rows(ss, ws_source_name='Base_Active'):
    """Déplace les lignes 'Basse' ou 'Informatif' d'un onglet source vers 'Informative'"""
    try:
        ws_source = ss.worksheet(ws_source_name)
        data = ws_source.get_all_records()
        if not data: return
        
        header = ws_source.row_values(1)
        col_crit = find_col(header, 'Criticité') or 18
        crit_name = header[col_crit-1]
        
        try:
            ws_info = ss.worksheet('Informative')
        except:
            ws_info = ss.add_worksheet('Informative', 1000, len(header))
            ws_info.append_row(header)
            
        rows_to_move = []
        indices_to_delete = []
        
        for i, row in enumerate(data):
            crit = str(row.get(crit_name, '')).strip().lower()
            if crit in ['informatif', 'non', 'info']:
                rows_to_move.append(list(row.values()))
                indices_to_delete.append(i + 2)
        
        if rows_to_move:
            print(f"   > [{ws_source_name}] Déplacement de {len(rows_to_move)} lignes vers 'Informative'...")
            ws_info.append_rows(rows_to_move)
            for idx in reversed(indices_to_delete):
                ws_source.delete_rows(idx)
            print(f"   ✅ [{ws_source_name}] Déplacement terminé.")
        else:
            print(f"   ✅ [{ws_source_name}] Aucune ligne informative à déplacer.")
            
    except Exception as e:
        print(f"   ⚠️ Erreur lors du déplacement : {e}")

# Ajouter la racine du projet au path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.core.pipeline import Config, Brain, extract_json

def find_col(header, name):
    """Trouve l'index d'une colonne (1-based) de façon robuste"""
    try:
        # Match exact
        if name in header: return header.index(name) + 1
        # Match case-insensitive et sans espaces
        n = name.lower().strip()
        for i, h in enumerate(header):
            if h.lower().strip() == n: return i + 1
        return None
    except: return None

def repair_sheets():
    print("--- [REPAIR] Enrichissement des métadonnées et preuves d'audit ---")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(Config.SHEET_ID)
        print(f"✅ Connecté au Sheet: {sheet.title}")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return

    brain = Brain(model_name=Config.MODEL_NAME)

    for ws_name in ['Base_Active', 'Rapport_Veille_Auto']:
        print(f"\n> Analyse de l'onglet: {ws_name}")
        ws = sheet.worksheet(ws_name)
        all_values = ws.get_all_values()
        if len(all_values) <= 1: continue
        
        header = all_values[0]
        rows = all_values[1:]
        
        # Localisation des colonnes critiques
        col_type = find_col(header, 'Type de texte') or 3
        col_date = find_col(header, 'Date') or 5
        col_preuve = find_col(header, 'Preuve de Conformité Attendue') or 19
        col_titre = find_col(header, 'Intitulé ') or 6
        col_crit = find_col(header, 'Criticité') or 18
        col_statut = find_col(header, 'Statut') or 11
        col_grand = find_col(header, 'Grand thème') or 8

        # On prépare une liste de lignes à traiter (basée sur le mask précédent)
        to_repair_indices = [] # liste de (row_idx_dans_la_feuille, data_row)
        
        for i, row in enumerate(rows):
            row_num = i + 2
            # Accès indexé (0-based pour la liste row)
            val_type = row[col_type-1] if len(row) >= col_type else ""
            val_date = row[col_date-1] if len(row) >= col_date else ""
            val_preuve = row[col_preuve-1] if len(row) >= col_preuve else ""
            val_crit = row[col_crit-1] if len(row) >= col_crit else ""
            
            is_type_manquant = "MANQUANT" in val_type.upper()
            is_date_manquante = val_date in ['Inconnue', 'Non disponible', 'NA', 'N/A', '', 'Non précisée', 'Inconnu', 'Non identifiable']
            is_preuve_manquante = len(val_preuve.strip()) < 5
            is_crit_manquante = val_crit.strip() in ['', 'Non spécifiée', 'Basse', 'MISSING']
            
            if is_type_manquant or is_date_manquante or is_preuve_manquante or is_crit_manquante:
                to_repair_indices.append((row_num, row))
        
        print(f"   - {len(to_repair_indices)} lignes nécessitent une réparation.")
        
        if not to_repair_indices: continue

        # Traitement par lot de 150
        batch_to_process = to_repair_indices[:150]
        
        cells_to_update = []
        for row_num, row_data in batch_to_process:
            title = row_data[col_titre-1] if len(row_data) >= col_titre else "Sans titre"
            print(f"   [IA] Réparation de : {title[:50]}...")
            
            prompt = f"""
            Expert QHSE. Répare les métadonnées de ce texte réglementaire.
            TITRE : {title}
            
            CONSIGNES :
            1. DATE : Trouve la date réelle de publication/signature (JJ/MM/AAAA). 
            2. TYPE : Loi, Décret, Arrêté, Règlement UE, Directive, ou Guide.
            3. PREUVE PHYSIQUE : Donne un exemple PRÉCIS de document de preuve (ex: 'Justificatif de contrôle des extincteurs').
            4. CRITICITÉ : Haute / Moyenne / Basse. Base-toi sur l'impact potentiel pour une usine de découpage métaux GDD.
            5. STATUT : 'Mise en place' (si c'est un nouveau texte ou une obligation majeure) ou 'Réévaluation' (si c'est un texte récurrent).
            
            RÉPONSE JSON :
            {{
                "date": "...",
                "type_texte": "...",
                "preuve_attendue": "...",
                "criticite": "...",
                "statut": "...",
                "grand_theme": "ENVIRONNEMENT, GOUVERNANCE ou RESSOURCES"
            }}
            """
            
            try:
                resp = brain.model.generate_content(prompt)
                rep = extract_json(resp.text)
                
                if rep:
                    if rep.get('type_texte'):
                        cells_to_update.append(gspread.Cell(row=row_num, col=col_type, value=rep['type_texte']))
                    
                    if rep.get('date'):
                        cells_to_update.append(gspread.Cell(row=row_num, col=col_date, value=rep['date']))
                        
                    if rep.get('preuve_attendue'):
                        cells_to_update.append(gspread.Cell(row=row_num, col=col_preuve, value=rep['preuve_attendue']))

                    if rep.get('criticite'):
                        cells_to_update.append(gspread.Cell(row=row_num, col=col_crit, value=rep['criticite']))
                    
                    if rep.get('statut'):
                        cells_to_update.append(gspread.Cell(row=row_num, col=col_statut, value=rep['statut']))
                    
                    if rep.get('grand_theme'):
                        cells_to_update.append(gspread.Cell(row=row_num, col=col_grand, value=rep['grand_theme']))

                    print(f"      ✅ IA OK (Ligne {row_num}) - Crit: {rep.get('criticite')}, Statut: {rep.get('statut')}")
                
                time.sleep(2) # Anti-quota AI
            except Exception as e:
                print(f"      ⚠️ Erreur IA ligne {row_num}: {e}")

        if cells_to_update:
            print(f"   > Envoi de {len(cells_to_update)} mises à jour IA pour {ws_name}...")
            ws.update_cells(cells_to_update, value_input_option='USER_ENTERED')
            print(f"   ✅ {ws_name} enrichi.")
        else:
            print(f"   ✅ {ws_name}: Aucune mise à jour IA effectuée.")

    # --- POST-REPAIR : ROUTAGE INTELLIGENT ---
    # Déplace automatiquement les textes "Informatifs" depuis les deux onglets principaux
    for name in ['Base_Active', 'Rapport_Veille_Auto']:
        move_informative_rows(sheet, name)

    print("\n--- Réparation terminée ---")

if __name__ == "__main__":
    repair_sheets()
