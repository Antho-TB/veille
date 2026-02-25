"""
=============================================================================
GESTIONNAIRE D'UPLOAD AZURE STORAGE - VEILLE GDD
=============================================================================

Ce script permet de téléverser automatiquement le tableau de bord HTML 
(dashboard.html) vers le conteneur $web d'Azure Storage pour l'hébergement statique.

"""

import os
from azure.storage.blob import BlobServiceClient, ContentSettings
from src.core.config_manager import Config

class AzureUploader:
    """Gère l'envoi de fichiers vers Azure Blob Storage ($web)"""
    
    def __init__(self):
        # On récupère les infos depuis le Config (ou .env)
        # Junior Tip: La chaîne de connexion est stockée de manière sécurisée
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not self.connection_string:
            print("⚠️ Erreur : AZURE_STORAGE_CONNECTION_STRING non définie.")
            return

        self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
        self.container_name = "$web"

    def upload_dashboard(self, file_path):
        """Téléverse le dashboard vers Azure"""
        if not self.connection_string: return
        
        file_name = "dashboard.html"
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=file_name)

        print(f"> Téléchargement de {file_name} vers Azure Storage ($web)...")
        
        with open(file_path, "rb") as data:
            blob_client.upload_blob(
                data, 
                overwrite=True, 
                content_settings=ContentSettings(content_type='text/html')
            )
        
        print(f"✅ Dashboard disponible sur Azure : {self.blob_service_client.primary_endpoint}{self.container_name}/{file_name}")

def run_azure_upload():
    """Point d'entrée pour l'automatisation"""
    print("--- [Azure] Synchronisation du Dashboard ---")
    dashboard_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../dashboard.html"))
    
    if not os.path.exists(dashboard_path):
        print(f"❌ Erreur : Fichier {dashboard_path} introuvable.")
        return

    uploader = AzureUploader()
    uploader.upload_dashboard(dashboard_path)

if __name__ == "__main__":
    run_azure_upload()
