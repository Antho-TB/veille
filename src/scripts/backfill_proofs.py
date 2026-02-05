
import os
import sys
import time
from datetime import datetime
import pandas as pd

# Ajout du chemin src au python path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from core.pipeline import Brain, Config
from core.checklists import ChecklistGenerator

def backfill_proofs():
    print("--- 🚀 Démarrage du Backfill des Preuves (Nouveautés) ---")
    cg = ChecklistGenerator()
    brain = Brain()
    
    # 1. Récupération des données
    df = cg.get_data('Rapport_Veille_Auto')
    if df.empty:
        print("❌ Aucune donnée trouvée.")
        return

    # Normalisation des colonnes
    df.columns = [c.strip() for c in df.columns]
    col_name = 'Preuve de Conformité Attendue'
    
    if col_name not in df.columns:
        print(f"❌ Colonne '{col_name}' manquante dans le sheet.")
        return

    # Connexion directe à gspread pour les updates
    if not cg.client: cg.connect()
    sheet = cg.client.open_by_key(Config.SHEET_ID)
    ws = sheet.worksheet('Rapport_Veille_Auto')
    
    # Trouver l'index de la colonne (1-indexed pour gspread)
    headers = ws.row_values(1)
    try:
        col_idx = headers.index(col_name) + 1
    except ValueError:
        # Fallback si header non trouvé par string exacte
        col_idx = 18 
        print(f"⚠️ Colonne non trouvée par nom, utilisation index par défaut: {col_idx}")

    # 2. Filtrage des lignes sans preuves
    # On itère sur les lignes (index + 2 car header=1 et index=0)
    count = 0
    for idx, row in df.iterrows():
        current_proof = str(row.get(col_name, "")).strip()
        if not current_proof or current_proof.lower() in ['nan', 'none', '']:
            titre = row.get('Intitulé', row.get('Intitulé ', ''))
            action = row.get('Commentaires', '')
            
            print(f"   [Processing {idx+1}/{len(df)}] {titre[:50]}...")
            
            # Appel IA pour obtenir la preuve
            try:
                # On utilise analyze_news mais on ne s'intéresse qu'à la preuve
                # Pour gagner du temps, on peut faire un prompt plus léger ou réutiliser le existant
                res = brain.analyze_news(f"{titre} {action}")
                preuve_generee = res.get('preuve_attendue', "Non spécifiée (Analyse requise)")
                
                if preuve_generee and preuve_generee != "Non spécifiée":
                    # Mise à jour dans le Google Sheet
                    ws.update_cell(idx + 2, col_idx, preuve_generee)
                    print(f"      ✅ Preuve ajoutée: {preuve_generee[:60]}...")
                    count += 1
                else:
                    print("      ⚠️ IA n'a pas généré de preuve spécifique.")
                
                time.sleep(1) # Respecter les quotas API
            except Exception as e:
                print(f"      ❌ Erreur IA: {e}")
                
    print(f"--- ✨ Terminé ! {count} preuves ont été générées et ajoutées. ---")

if __name__ == "__main__":
    backfill_proofs()
