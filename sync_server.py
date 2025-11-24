# sync_server.py
# Serveur Flask pour synchroniser les observations des fiches HTML vers Google Sheets
# Auteur: Anthony Bezille, Service Data&IA

from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Permet les requêtes depuis les fichiers HTML locaux

# Configuration Google Sheets
SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
CREDENTIALS_FILE = "credentials.json"

def get_sheet_client():
    """Connexion à Google Sheets"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client

@app.route('/sync', methods=['POST'])
def sync_observations():
    """
    Endpoint pour synchroniser les observations vers Google Sheets
    Reçoit un JSON avec les modifications et met à jour le Sheet
    """
    try:
        data = request.json
        sheet_name = data.get('sheet_name')  # 'Rapport_Veille_Auto' ou 'Base_Active'
        observations = data.get('observations')  # Liste des observations
        
        if not sheet_name or not observations:
            return jsonify({'error': 'Données manquantes'}), 400
        
        # Connexion au Sheet
        client = get_sheet_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Mise à jour des observations
        updates_count = 0
        for obs in observations:
            row_number = obs.get('row')
            observation_text = obs.get('observation')
            status = obs.get('status')
            
            if not row_number:
                continue
            
            # Colonne "Commentaires" (colonne M = 13)
            if observation_text:
                worksheet.update_cell(row_number, 13, observation_text)
                updates_count += 1
            
            # Optionnel : Mettre à jour le statut dans une colonne dédiée
            # Si vous avez une colonne "Statut" dans votre Sheet
            
        return jsonify({
            'success': True,
            'message': f'{updates_count} observation(s) synchronisée(s)',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        print(f"❌ Erreur de synchronisation : {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint pour vérifier que le serveur fonctionne"""
    return jsonify({'status': 'ok', 'message': 'Serveur de synchronisation actif'})

if __name__ == '__main__':
    print("🚀 Serveur de synchronisation démarré sur http://localhost:5000")
    print("📝 Endpoint de synchronisation : http://localhost:5000/sync")
    print("💡 Laissez ce serveur tourner pendant que vous utilisez les fiches HTML")
    app.run(host='localhost', port=5000, debug=True)
