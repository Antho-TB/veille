import mlflow
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import pandas as pd
from datetime import datetime

# Configuration
SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "../config/credentials.json")
EXPERIMENTS = ["Veille_Historique_Profond", "Veille_QHSE_Production", "Veille_QHSE"]

def sync_mlflow():
    print("--- [SYNC] MLflow vers Google Sheets ---")
    
    # 1. Connexion MLflow (Tracking URI par défaut)
    mlflow.set_tracking_uri("http://127.0.0.1:5050" if os.getenv("MLFLOW_PORT") else None)
    
    all_runs = []
    for exp_name in EXPERIMENTS:
        exp = mlflow.get_experiment_by_name(exp_name)
        if not exp:
            print(f"   > ⚠️ Expérience {exp_name} introuvable.")
            continue
            
        print(f"   > Récupération des runs pour : {exp_name}")
        runs = mlflow.search_runs(experiment_ids=[exp.experiment_id])
        if not runs.empty:
            runs['experiment_name'] = exp_name
            all_runs.append(runs)
            
    if not all_runs:
        print("   > ❌ Aucun run trouvé.")
        return
        
    df_all = pd.concat(all_runs, ignore_index=True)
    
    # --- SÉLECTION RIGOUREUSE (AUDIT & MLE) ---
    whitelist = {
        'start_time': 'Date/Heure',
        'experiment_name': 'Type de Veille',
        'tags.mlflow.runName': 'Nom du Scan',
        'metrics.nb_new_rows': 'Nouveaux Textes',
        'metrics.total_web_result': 'Total Scanné',
        'params.search_period': 'Période',
        'params.full_audit': 'Audit Complet',
        'params.model_name': 'Moteur IA',
        'metrics.duration_second': 'Durée (s)'
    }
    
    # On ne garde que ce qui existe dans le DF
    cols_to_keep = [c for c in whitelist.keys() if c in df_all.columns]
    df_final = df_all[cols_to_keep].copy()
    
    # Renommer pour le Sheet
    df_final = df_final.rename(columns=whitelist)
    
    # Formatage propre
    df_final['Date/Heure'] = pd.to_datetime(df_final['Date/Heure']).dt.strftime('%d/%m/%Y %H:%M')
    df_final = df_final.fillna("-")

    # 2. Connexion Google Sheets
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        ss = client.open_by_key(SHEET_ID)
        
        try:
            ws = ss.worksheet("Historique")
        except:
            ws = ss.add_worksheet("Historique", 1000, 20)
            ws.append_row(df_final.columns.tolist())
            
        # On remplace l'intégralité ou on ajoute ? 
        # Pour une synchro propre, on va vider et réécrire (ou mettre à jour les lignes existantes)
        # Ici on va vider pour avoir l'historique complet et ordonné
        ws.clear()
        data = [df_final.columns.tolist()] + df_final.values.tolist()
        ws.update('A1', data)
        
        print(f"   > ✅ {len(df_final)} runs synchronisés dans l'onglet 'Historique'.")
        
    except Exception as e:
        print(f"   > ❌ Erreur synchro : {e}")

if __name__ == "__main__":
    sync_mlflow()
