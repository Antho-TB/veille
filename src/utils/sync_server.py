
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Ajouter la racine du projet au path pour importer Config
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from src.core.pipeline import Config

app = Flask(__name__)
CORS(app)

def get_spreadsheet():
    """Connexion à Google Sheets"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(Config.SHEET_ID)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "GDD Sync Server is running"})

@app.route('/sync-observation', methods=['POST'])
def sync_observation():
    """Met à jour uniquement le texte d'observation (Colonne I)"""
    try:
        data = request.json
        sheet_name = data.get('sheet_name')
        row_idx = data.get('row_idx')
        text = data.get('text')
        
        ss = get_spreadsheet()
        ws = ss.worksheet(sheet_name)
        
        # Colonne I = Index 9
        ws.update_cell(row_idx, 9, text)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/execute-action', methods=['POST'])
def execute_action():
    """Exécute une action (Conforme, NC, Info, Supprimer)"""
    try:
        data = request.json
        action = data.get('action') # 'conforme', 'non_conforme', 'info', 'supprimer'
        sheet_name = data.get('sheet_name')
        row_idx = data.get('row_idx')
        
        ss = get_spreadsheet()
        ws = ss.worksheet(sheet_name)
        
        if action == 'supprimer':
            ws.delete_rows(row_idx)
            return jsonify({"success": True, "message": "Ligne supprimée"})

        if action == 'info':
            # Déplacer vers une feuille "Informative"
            try:
                ws_info = ss.worksheet("Informative")
            except:
                ws_info = ss.add_worksheet("Informative", 1000, 20)
                # Copier les headers si vide
                headers = ws.row_values(1)
                ws_info.append_row(headers)
            
            row_data = ws.row_values(row_idx)
            ws_info.append_row(row_data)
            ws.delete_rows(row_idx)
            return jsonify({"success": True, "message": "Transféré vers Informative"})

        if action == 'non_conforme':
            # 1. Mise à jour Conformité (NC)
            # Index 12: Conformité
            ws.update_cell(row_idx, 12, "NC")
            
            # 2. Envoyer vers le Plan d'Action
            try:
                ws_plan = ss.worksheet("Plan_Action")
            except:
                ws_plan = ss.add_worksheet("Plan_Action", 1000, 10)
                ws_plan.append_row(["Date", "Texte", "Thème", "Criticité", "Action Requise", "Responsable", "Échéance", "Statut"])
            
            row_data = ws.row_values(row_idx)
            # On extrait Titre (6), Thème (7), Criticité (index variable - à chercher)
            header = ws.row_values(1)
            crit_idx = header.index('Criticité') + 1 if 'Criticité' in header else 7
            
            plan_row = [
                datetime.now().strftime("%d/%m/%Y"), # Date
                row_data[5], # Titre
                row_data[6], # Thème
                row_data[crit_idx-1] if crit_idx <= len(row_data) else "N/A", # Criticité
                "Mise en conformité requise", # Action
                "", "", "À faire"
            ]
            ws_plan.append_row(plan_row)
            
            return jsonify({"success": True, "message": "NC enregistré et envoyé au Plan d'Action"})

        if action == 'conforme':
            # 1. Mise à jour Conformité (C) et Dates
            today = datetime.now().strftime("%d/%m/%Y")
            
            # Périodicité par défaut (3 ans)
            next_eval = (datetime.now().replace(year=datetime.now().year + 3)).strftime("%d/%m/%Y")
            
            # Index 12: Conformité, 15: Dernière éval, 16: Prochaine éval
            ws.update_cell(row_idx, 12, "C")
            ws.update_cell(row_idx, 15, today)
            ws.update_cell(row_idx, 16, next_eval)
            
            # Enregistrement Audit Trail (Qui/Quand)
            # On cherche ou crée la colonne "Validé par"
            header = ws.row_values(1)
            if "Validé par" not in header:
                ws.update_cell(1, len(header) + 1, "Validé par")
                valide_idx = len(header) + 1
            else:
                valide_idx = header.index("Validé par") + 1
            
            ws.update_cell(row_idx, valide_idx, "Anthony (LMS Auto)")
            
            # 2. Si on est dans Rapport_Veille_Auto, on déplace vers Base_Active
            if sheet_name == "Rapport_Veille_Auto":
                ws_base = ss.worksheet("Base_Active")
                row_data = ws.row_values(row_idx)
                ws_base.append_row(row_data)
                ws.delete_rows(row_idx)
                return jsonify({"success": True, "message": "Evalué et transféré en Base Active"})
            
            return jsonify({"success": True, "message": "Conformité validée"})

    except Exception as e:
        print(f"Error executing action: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/search', methods=['GET'])
def search_sheets():
    """Recherche des textes par mots-clés dans les deux onglets principaux"""
    try:
        query = request.args.get('q', '').lower()
        if not query:
            return jsonify([])
            
        ss = get_spreadsheet()
        results = []
        
        for name in ["Rapport_Veille_Auto", "Base_Active"]:
            ws = ss.worksheet(name)
            records = ws.get_all_records()
            for i, row in enumerate(records):
                # On cherche dans Intitulé, Thème, Commentaires, Evaluation
                text_to_search = f"{row.get('Intitulé','')} {row.get('Thème','')} {row.get('Commentaires','')} {row.get('Statut','')}".lower()
                if query in text_to_search:
                    row['source_sheet'] = name
                    row['row_idx'] = i + 2
                    results.append(row)
        
        return jsonify(results)
    except Exception as e:
        print(f"Error searching: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = 5000
    print(f"🚀 GDD Interactivity Server running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
