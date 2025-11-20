from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import os

CREDENTIALS_FILE = "credentials.json"
SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"

print(">>> INSPECTION FORMATAGE (VIA GOOGLE API CLIENT) <<<")

if not os.path.exists(CREDENTIALS_FILE):
    print("❌ Credentials file not found.")
    exit()

try:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = service_account.Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)

    # Request formatting for the first row of the first sheet (Base_Active)
    # We assume Base_Active is the first sheet or named 'Base_Active'
    
    # First get sheet ID for 'Base_Active'
    spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    sheet_id = 0
    for s in spreadsheet['sheets']:
        if s['properties']['title'] == 'Base_Active':
            sheet_id = s['properties']['sheetId']
            break
            
    print(f"Sheet ID for Base_Active: {sheet_id}")

    # Get the formatting of the first row
    ranges = [f"Base_Active!A1:Z1"]
    params = {
        'spreadsheetId': SHEET_ID,
        'ranges': ranges,
        'fields': 'sheets(data(rowData(values(userEnteredFormat))))'
    }
    
    result = service.spreadsheets().get(**params).execute()
    
    if 'sheets' in result and len(result['sheets']) > 0:
        row_data = result['sheets'][0]['data'][0]['rowData']
        if row_data:
            # Get format of the first cell
            first_cell_format = row_data[0]['values'][0].get('userEnteredFormat', {})
            print("Format de la première cellule (A1) :")
            print(json.dumps(first_cell_format, indent=2))
            
            # Also print specific interesting values
            bg = first_cell_format.get('backgroundColor', {})
            text = first_cell_format.get('textFormat', {})
            print("\n--- RESUME ---")
            print(f"Background: {bg}")
            print(f"Text: {text}")
        else:
            print("Pas de données de format trouvées.")
    else:
        print("Structure de réponse inattendue.")

except Exception as e:
    print(f"❌ Erreur: {e}")
