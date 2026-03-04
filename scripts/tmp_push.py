import sqlite3
import pandas as pd
from src.utils.data_manager import DataManager
from datetime import datetime
import os

try:
    conn = sqlite3.connect('mlflow.db')
    query = '''
        SELECT r.start_time, r.name, r.status, m.key, m.value 
        FROM runs r 
        LEFT JOIN metrics m ON r.run_uuid = m.run_uuid 
        WHERE r.status = 'FINISHED' 
        ORDER BY r.start_time DESC LIMIT 40
    '''
    df = pd.read_sql_query(query, conn)
    dm = DataManager()
    runs = df['name'].unique()[:5]

    for run in runs:
        run_data = df[df['name'] == run]
        
        time_val = run_data[run_data['key'] == 'duration_second']['value'].values
        txt_val = run_data[run_data['key'] == 'total_web_result']['value'].values
        new_val = run_data[run_data['key'] == 'nb_new_rows']['value'].values
        
        start_ts = run_data['start_time'].values[0]
        dt = datetime.fromtimestamp(start_ts / 1000.0).strftime('%d/%m/%Y %H:%M:%S')
        
        d = {
            'Date': dt, 
            'Modèle IA': 'Multiple (Historique existant)', 
            'Mode Recherche': 'N/A', 
            'Textes Scannés': int(txt_val[0]) if len(txt_val)>0 else 0, 
            'Nouveautés Ajoutées': int(new_val[0]) if len(new_val)>0 else 0, 
            'Durée (s)': float(time_val[0]) if len(time_val)>0 else 0
        }
        dm.save_historique(d)
except Exception as e:
    print(f"Erreur script : {e}")
