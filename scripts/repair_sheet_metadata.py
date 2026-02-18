import os
import sys
import pandas as pd
import gspread
import time
import re
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

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
        data = ws.get_all_records()
        if not data: continue
        
        df = pd.DataFrame(data)
        header = ws.row_values(1)
        
        # Localisation des colonnes critiques
        col_type = find_col(header, 'Type de texte') or 3
        col_date = find_col(header, 'Date') or 5
        col_preuve = find_col(header, 'Preuve de Conformité Attendue') or 19
        col_titre = find_col(header, 'Intitulé ') or 6
        col_crit = find_col(header, 'Criticité') or 18
        col_statut = find_col(header, 'Statut') or 11

        # Filtre : lignes à réparer
        # On utilise les noms de colonnes réels trouvés
        type_name = header[col_type-1]
        date_name = header[col_date-1]
        preuve_name = header[col_preuve-1]
        titre_name = header[col_titre-1]
        crit_name = header[col_crit-1] if col_crit <= len(header) else 'Criticité'
        statut_name = header[col_statut-1] if col_statut <= len(header) else 'Statut'

        mask = (
            (df[type_name].astype(str).str.contains('MANQUANT', case=False)) |
            (df[date_name].astype(str).isin(['Inconnue', 'Non disponible', 'NA', 'N/A', '', 'Non précisée', 'Inconnu', 'Non identifiable'])) |
            (df[preuve_name].astype(str).str.len() < 5) |
            (df[crit_name].astype(str).isin(['', 'Non spécifiée', 'Basse', 'MISSING']))
        )
        
        to_repair = df[mask].copy()
        print(f"   - {len(to_repair)} lignes nécessitent une réparation.")
        
        if to_repair.empty: continue

        # On limite pour éviter les timeouts IA/Quota
        to_repair = to_repair.head(50)
        
        for idx, row in to_repair.iterrows():
            title = row.get(titre_name, '')
            print(f"   [IA] Réparation de : {title[:50]}...")
            
            # ... (prompt reste identique) ...
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
                "statut": "..."
            }}
            """
            
            try:
                resp = brain.model.generate_content(prompt)
                rep = extract_json(resp.text)
                
                if rep:
                    row_idx = idx + 2
                    
                    if rep.get('type_texte'):
                        ws.update_cell(row_idx, col_type, rep['type_texte'])
                    
                    if rep.get('date'):
                        ws.update_cell(row_idx, col_date, rep['date'])
                        
                    if rep.get('preuve_attendue'):
                        ws.update_cell(row_idx, col_preuve, rep['preuve_attendue'])

                    if rep.get('criticite'):
                        ws.update_cell(row_idx, col_crit, rep['criticite'])
                    
                    if rep.get('statut'):
                        ws.update_cell(row_idx, col_statut, rep['statut'])
                    
                    print(f"      ✅ Mis à jour (Ligne {row_idx}) - Crit: {rep.get('criticite')}, Statut: {rep.get('statut')}")
                
                time.sleep(2) # Anti-quota
            except Exception as e:
                print(f"      ⚠️ Erreur ligne {idx}: {e}")

    print("\n--- Réparation terminée ---")

if __name__ == "__main__":
    repair_sheets()
