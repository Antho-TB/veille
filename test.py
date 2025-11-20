import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- VOTRE CONFIGURATION ---
SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg" 
CREDENTIALS_FILE = "credentials.json"

def diag():
    print("=== DIAGNOSTIC DE PANNES V2 ===")
    
    # 1. Check Fichier
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ ECHEC : Fichier '{CREDENTIALS_FILE}' absent.")
        return
    
    # 2. Check Email
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            creds = json.load(f)
        email = creds.get('client_email')
        print(f"ℹ️  Email du Robot : {email}")
    except:
        print("❌ ECHEC : JSON invalide.")
        return

    # 3. Connexion
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_obj = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds_obj)
        print("✅ Authentification OK.")
    except Exception as e:
        print(f"❌ Erreur Auth : {e}")
        return

    # 4. Ouverture Sheet (Avec détail erreur)
    print(f"🔍 Tentative d'ouverture du Sheet : {SHEET_ID}")
    try:
        sheet = client.open_by_key(SHEET_ID)
        print(f"✅ SUCCÈS TOTAL ! Accès au document : '{sheet.title}'")
    except Exception as e:
        print("\n❌ ECHEC DE L'OUVERTURE")
        print(f"TYPE D'ERREUR : {type(e).__name__}")
        print(f"MESSAGE DÉTAILLÉ : {e}")
        print("-" * 30)
        if "403" in str(e):
            if "Sheets API has not been used" in str(e):
                print("👉 SOLUTION : Vous n'avez pas activé l'API Google Sheets.")
                print("   Lien : https://console.cloud.google.com/apis/library/sheets.googleapis.com")
            else:
                print("👉 SOLUTION : Problème de partage.")
                print(f"   Ajoutez '{email}' en Éditeur dans le Sheet.")
        elif "404" in str(e):
             print("👉 SOLUTION : L'ID du Sheet est incorrect ou le fichier n'existe pas.")

if __name__ == "__main__":
    diag()