from pipeline_veille import DataManager, Config
import pandas as pd

print(">>> INSPECTION DES COLONNES <<<")
dm = DataManager()
try:
    dm._connect()
    sheet = dm.client.open_by_key(Config.SHEET_ID)
    ws = sheet.get_worksheet(0) # Base_Active
    records = ws.get_all_records()
    if records:
        df = pd.DataFrame(records)
        print(f"Colonnes dans Base_Active ({len(df.columns)}):")
        print(list(df.columns))
    else:
        print("Base_Active est vide ou illisible.")
except Exception as e:
    print(f"Erreur: {e}")
