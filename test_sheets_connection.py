# ---------------------------------------------------------------------------
# Test de Connexion - Google Sheets
# ---------------------------------------------------------------------------
# Ce script de diagnostic permet de :
# 1. Vérifier la validité du fichier credentials.json.
# 2. Tester l'accès en lecture/écriture au Google Sheet.
# 3. Confirmer que le compte de service a les bonnes permissions.
# ---------------------------------------------------------------------------

import gspread
from google.oauth2.service_account import Credentials
import sys

# --- CONFIGURATION ---
# Remplacez par l'ID de votre Sheet (celui que vous avez mis dans pipeline_veille.py)
SHEET_ID = "d/1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg" 

# Nom du fichier JSON téléchargé depuis Google Cloud Console (Service Account)
CREDENTIALS_FILE = "credentials.json"

def test_connection():
    print(f"--- Test de connexion au Google Sheet : {SHEET_ID} ---")

    # 1. Définition des permissions (Scopes)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    try:
        # 2. Authentification
        print(f"1. Tentative d'authentification avec '{CREDENTIALS_FILE}'...")
        credentials = Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=scopes
        )
        client = gspread.authorize(credentials)
        print("   -> Authentification réussie (Service Account).")

        # 3. Ouverture du fichier
        print("2. Tentative d'ouverture du Spreadsheet...")
        sh = client.open_by_key(SHEET_ID)
        print(f"   -> Spreadsheet trouvé : '{sh.title}'")

        # 4. Lecture de la première feuille
        worksheet = sh.get_worksheet(0) # Prend la première feuille (index 0)
        print(f"   -> Accès à la feuille : '{worksheet.title}'")

        # 5. Test d'écriture (Optionnel - décommentez pour tester l'écriture)
        # print("3. Test d'écriture dans la cellule A1...")
        # old_val = worksheet.acell('A1').value
        # worksheet.update('A1', 'Test Connexion OK')
        # print(f"   -> Écriture réussie. (Ancienne valeur : {old_val})")
        
        # 6. Lecture des données
        data = worksheet.get_all_records()
        print(f"3. Lecture des données : {len(data)} lignes trouvées.")
        if len(data) > 0:
            print("   -> Exemple de la première ligne :")
            print(f"      {data[0]}")
        else:
            print("   -> La feuille est vide, mais la connexion fonctionne.")

        print("\n>>> SUCCÈS : La connexion est opérationnelle ! <<<")

    except FileNotFoundError:
        print(f"\nERREUR : Le fichier '{CREDENTIALS_FILE}' est introuvable.")
        print("Assurez-vous d'avoir téléchargé la clé JSON de votre Service Account Google Cloud.")
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"\nERREUR : Le Spreadsheet avec l'ID '{SHEET_ID}' est introuvable.")
        print("SOLUTIONS :")
        print("1. Vérifiez que l'ID est correct.")
        print("2. Avez-vous PARTAGÉ le Sheet avec l'email du Service Account ?")
        print("   (Ouvrez credentials.json, copiez 'client_email' et ajoutez-le dans le bouton 'Partager' du Sheet).")
    except Exception as e:
        print(f"\nERREUR INCONNUE : {e}")

if __name__ == "__main__":
    test_connection()