
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
import pandas as pd
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
    """
    Moteur de recherche multi-critères pour le Dashboard.
    Supporte les filtres : q (texte), theme, crit (criticité), conf (conformité).
    """
    try:
        query = request.args.get('q', '').lower().strip()
        theme_filter = request.args.get('theme', '').lower().strip()
        crit_filter = request.args.get('crit', '').lower().strip()
        conf_filter = request.args.get('conf', '').lower().strip()
        
        # Si aucun filtre, on renvoie []
        if not any([query, theme_filter, crit_filter, conf_filter]):
            return jsonify([])
            
        ss = get_spreadsheet()
        results = []
        
        for name in ["Base_Active", "Rapport_Veille_Auto"]:
            try:
                ws = ss.worksheet(name)
                records = ws.get_all_records()
            except: continue

            for i, row in enumerate(records):
                # Nettoyage des clés (headers)
                r = {str(k).strip(): v for k, v in row.items()}
                
                # 1. Filtre par texte (Query)
                if query:
                    text_to_search = f"{r.get('Intitulé','')}{r.get('Thème','')}{r.get('Commentaires','')}{r.get('Statut','')}".lower()
                    if query not in text_to_search: continue
                
                # 2. Filtre par Thème
                if theme_filter:
                    t = str(r.get('Thème', '')).lower().strip()
                    if theme_filter not in t: continue
                
                # 3. Filtre par Criticité
                if crit_filter:
                    c = ""
                    for k in ['Criticité', 'criticite', 'Crit']:
                        if k in r: c = str(r[k]).lower().strip()
                    if crit_filter not in c: continue
                
                # 4. Filtre par Conformité / Statut (Mapping spécial pour l'UX Dashboard)
                if conf_filter:
                    conf = str(r.get('Conformité', '')).lower().strip()
                    # Mapping spécial pour les filtres du dashboard (ex: 'nc' englobe 'en cours')
                    if conf_filter == 'nc':
                        if conf not in ['nc', 'non conforme', 'en cours d\'étude', 'à qualifier'] and 'étude' not in conf: continue
                    elif conf_filter == 'c':
                        if conf not in ['c', 'conforme']: continue
                    elif conf_filter == 'qualif':
                        if conf != "": continue
                    elif conf_filter not in conf: continue

                r['source_sheet'] = name
                r['row_idx'] = i + 2
                # On ajoute aussi l'URL ici pour le dashboard
                r['url'] = str(r.get('Lien Internet', f"https://www.google.com/search?q={str(r.get('Intitulé','')).replace(' ', '+')}"))
                results.append(r)
        
        return jsonify(results)
    except Exception as e:
        print(f"Error searching: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Calcule les statistiques en temps réel pour le dashboard"""
    try:
        ss = get_spreadsheet()
        
        # 1. Chargement des données
        ws_base = ss.worksheet("Base_Active")
        ws_news = ss.worksheet("Rapport_Veille_Auto")
        
        df_base = pd.DataFrame(ws_base.get_all_records())
        df_news = pd.DataFrame(ws_news.get_all_records())
        
        if df_base.empty:
            return jsonify({"error": "Base_Active est vide"}), 404

        # Nettoyage
        df_base.columns = [c.strip() for c in df_base.columns]
        if not df_news.empty:
            df_news.columns = [c.strip() for c in df_news.columns]

        # 2. Calcul des KPIs
        # Termes robustes pour Conformité
        conf_col = 'Conformité' if 'Conformité' in df_base.columns else 'Statut' 
        df_app = df_base[~df_base[conf_col].astype(str).str.lower().str.strip().isin(['sans objet', 'archivé', ''])].copy()
        
        # MEC
        def is_mec(val):
            v = str(val).upper().strip()
            return v in ['NC', 'NON CONFORME', 'EN COURS D\'ÉTUDE', 'À QUALIFIER'] or 'ÉTUDE' in v
        
        count_mec = len(df_app[df_app[conf_col].apply(is_mec)])
        
        # Réévaluation
        next_eval_col = 'date de la prochaine évaluation'
        def is_past(date_str):
            date_str = str(date_str).strip()
            if not date_str or date_str.lower() in ['', 'nan']: return True
            for fmt in ['%d/%m/%Y', '%Y-%m-%d']:
                try: return datetime.strptime(date_str, fmt) <= datetime.now()
                except: continue
            return True
        
        mask_conf = df_app[conf_col].astype(str).str.lower().str.strip().isin(['c', 'conforme'])
        mask_past = df_app[next_eval_col].apply(is_past) if next_eval_col in df_app.columns else pd.Series([True]*len(df_app))
        count_reeval = len(df_app[mask_conf & mask_past])
        
        count_qualif = len(df_app[df_app[conf_col].astype(str).str.strip() == ""])

        # 3. Criticité
        def get_crit(r):
            for k in ['Criticité', 'criticite', 'Crit']:
                if k in r and str(r[k]).strip(): return str(r[k]).strip().capitalize()
            return 'Basse'
        
        df_base['Crit_Clean'] = df_base.apply(get_crit, axis=1)
        crit_counts = df_base['Crit_Clean'].value_counts()
        crit_labels = ["Haute", "Moyenne", "Basse"]
        crit_values = [int(crit_counts.get(l, 0)) for l in crit_labels]

        # 4. Compliance Pie
        c_count = len(df_app[mask_conf & ~mask_past])
        nc_count = len(df_app[df_app[conf_col].astype(str).str.upper().str.strip().isin(['NC', 'NON CONFORME'])])
        eval_count = len(df_app) - c_count - nc_count + len(df_news)

        stats = {
            "last_update": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "kpis": {
                "total_tracked": len(df_base),
                "applicable": len(df_app),
                "actions_required": count_mec + count_reeval + count_qualif,
                "sub_mec": count_mec,
                "sub_reeval": count_reeval,
                "sub_qualif": count_qualif,
                "alerts_ia": len(df_news),
                "proof_score": "En calcul..."
            },
            "compliance": {
                "labels": ["Conforme", "Non Conforme", "À évaluer"],
                "values": [c_count, nc_count, eval_count]
            },
            "criticite": {
                "labels": crit_labels,
                "values": crit_values
            }
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = 5000
    print(f"🚀 GDD Interactivity Server running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
