"""
=============================================================================
GESTIONNAIRE D'UPLOAD GOOGLE DRIVE PRO - VEILLE GDD
=============================================================================

Ce script permet de téléverser le dashboard ET ses dépendances (dossier output)
sur Google Drive pour garantir un affichage correct partout.

"""

import os
import sys
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials

# Ajout de la racine du projet au path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.core.config_manager import Config

class DriveUploader:
    """Gère l'envoi de fichiers et dossiers vers Google Drive"""
    
    def __init__(self):
        self.scopes = ["https://www.googleapis.com/auth/drive"]
        self.creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, self.scopes)
        self.service = build('drive', 'v3', credentials=self.creds)

    def get_or_create_folder(self, folder_name, parent_id=None):
        """Récupère un dossier ou le crée s'il n'existe pas"""
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
            
        results = self.service.files().list(
            q=query, 
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        items = results.get('files', [])
        if items:
            return items[0]['id']
        
        # Création
        print(f"> Création du dossier '{folder_name}' sur Drive...")
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
            
        folder = self.service.files().create(
            body=file_metadata, 
            fields='id',
            supportsAllDrives=True
        ).execute()
        return folder.get('id')

    def upload_file(self, local_path, folder_id, content_type='text/html'):
        """Upload ou met à jour un fichier"""
        file_name = os.path.basename(local_path)
        media = MediaFileUpload(local_path, mimetype=content_type, resumable=True)

        query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
        results = self.service.files().list(
            q=query, 
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        items = results.get('files', [])

        try:
            if items:
                file_id = items[0]['id']
                self.service.files().update(
                    fileId=file_id,
                    media_body=media,
                    supportsAllDrives=True
                ).execute()
                print(f"   [OK] Mis à jour : {file_name}")
            else:
                file_metadata = {'name': file_name, 'parents': [folder_id]}
                self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id',
                    supportsAllDrives=True
                ).execute()
                print(f"   [OK] Créé : {file_name}")
        except Exception as e:
            print(f"   [!] Erreur sur {file_name} : {e}")

def run_upload():
    print("--- [Drive] Synchronisation Complète Environnement ---")
    uploader = DriveUploader()
    
    # ID du dossier racine partagé
    ROOT_FOLDER_ID = "0AHak66l91DTaUk9PVA"
    
    # 1. Upload du Dashboard principal
    dashboard_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../dashboard.html"))
    if os.path.exists(dashboard_path):
        print("> Synchronisation dashboard.html")
        uploader.upload_file(dashboard_path, ROOT_FOLDER_ID)
    
    # 2. Synchronisation du dossier output (ESSENTIEL POUR LES STATS ET CHECKLISTS)
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../output"))
    if os.path.exists(output_dir):
        print("> Synchronisation du contenu /output")
        drive_output_id = uploader.get_or_create_folder("output", ROOT_FOLDER_ID)
        
        for file_name in os.listdir(output_dir):
            file_path = os.path.join(output_dir, file_name)
            if os.path.isfile(file_path):
                # Détermination du type MIME
                ctype = 'text/html'
                if file_name.endswith('.js'): ctype = 'application/javascript'
                elif file_name.endswith('.json'): ctype = 'application/json'
                
                uploader.upload_file(file_path, drive_output_id, content_type=ctype)

    print("✅ Synchronisation Drive terminée.")

if __name__ == "__main__":
    run_upload()
