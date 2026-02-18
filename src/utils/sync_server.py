
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

def find_col(header, name):
    """Trouve l'index d'une colonne (1-based) de façon robuste"""
    try:
        # Match exact
        if name in header: return header.index(name) + 1
        # Match case-insensitive et sans espaces
        n = name.lower().strip()
        for i, h in enumerate(header):
            if h.lower().strip() == n: return i + 1
        return None
    except: return None

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "GDD Sync Server is running"})

@app.route('/sync-observation', methods=['POST'])
def sync_observation():
    """Met à jour une cellule spécifique via son nom de colonne ou index"""
    try:
        data = request.json
        sheet_name = data.get('sheet_name')
        row_idx = data.get('row_idx')
        text = data.get('text')
        column_name = data.get('column') # Optionnel : ex "Preuves disponibles"
        
        ss = get_spreadsheet()
        ws = ss.worksheet(sheet_name)
        header = ws.row_values(1)
        
        col_idx = find_col(header, column_name) if column_name else find_col(header, "Commentaires (ALSAPE, APORA…)")
        if not col_idx: col_idx = 9 # Fallback historique
        
        ws.update_cell(row_idx, col_idx, text)
        
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
        header = ws.row_values(1)
        
        conf_idx = find_col(header, "Conformité") or 11
        if action == 'supprimer':
            ws.delete_rows(row_idx)
            return jsonify({"success": True, "message": "Ligne supprimée"})

        if action == 'info':
            # Déplacer vers une feuille "Informative"
            try:
                ws_info = ss.worksheet("Informative")
            except:
                ws_info = ss.add_worksheet("Informative", 1000, 20)
                ws_info.append_row(header)
            
            row_data = ws.row_values(row_idx)
            ws_info.append_row(row_data)
            ws.delete_rows(row_idx)
            return jsonify({"success": True, "message": "Transféré vers Informative"})

        if action == 'non_conforme':
            ws.update_cell(row_idx, conf_idx, "NC")
            
            try:
                ws_plan = ss.worksheet("Plan_Action")
            except:
                ws_plan = ss.add_worksheet("Plan_Action", 1000, 10)
                ws_plan.append_row(["Date", "Texte", "Thème", "Criticité", "Action Requise", "Responsable", "Échéance", "Statut"])
            
            row_data = ws.row_values(row_idx)
            crit_idx = find_col(header, 'Criticité') or 18
            titre_idx = find_col(header, 'Intitulé') or 6
            theme_idx = find_col(header, 'Thème') or 7

            plan_row = [
                datetime.now().strftime("%d/%m/%Y"), 
                row_data[titre_idx-1] if titre_idx <= len(row_data) else "N/A",
                row_data[theme_idx-1] if theme_idx <= len(row_data) else "N/A",
                row_data[crit_idx-1] if crit_idx <= len(row_data) else "N/A",
                "Mise en conformité requise", 
                "", "", "À faire"
            ]
            ws_plan.append_row(plan_row)
            return jsonify({"success": True, "message": "NC enregistré et envoyé au Plan d'Action"})

        if action == 'conforme':
            today = datetime.now().strftime("%d/%m/%Y")
            next_eval = (datetime.now().replace(year=datetime.now().year + 3)).strftime("%d/%m/%Y")
            
            last_idx = find_col(header, "date de la dernère évaluation") or 15
            next_idx = find_col(header, "date de la prochaine évaluation") or 16
            
            ws.update_cell(row_idx, conf_idx, "C")
            ws.update_cell(row_idx, last_idx, today)
            ws.update_cell(row_idx, next_idx, next_eval)
            
            valide_idx = find_col(header, "Validé par")
            if not valide_idx:
                valide_idx = len(header) + 1
                ws.update_cell(1, valide_idx, "Validé par")
            
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
