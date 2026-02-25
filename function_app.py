import azure.functions as func
import logging
import os
import sys
import json
from datetime import datetime

# Ajout du répertoire courant au PYTHONPATH pour permettre les imports de 'src'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.pipeline import run_pipeline
from src.utils.sync_server import get_spreadsheet, clean_theme, find_col, categorize_proof, normalize_proof_label

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.timer_trigger(schedule="0 0 2 * * 1", arg_name="myTimer", run_on_startup=False, use_monitor=False) 
def timer_veille_hebdomadaire(myTimer: func.TimerRequest) -> None:
    """
    Déclencheur planifié (Timer Trigger) pour la veille réglementaire.
    """
    if myTimer.past_due:
        logging.info('Le timer a pris du retard!')

    logging.info('Démarrage du pipeline de veille automatisée Azure.')
    try:
        run_pipeline()
        logging.info('Pipeline de veille exécuté avec succès.')
    except Exception as e:
        logging.error(f"Erreur critique lors de l'exécution du pipeline: {e}")
        raise

@app.route(route="search", methods=["GET"])
def search(req: func.HttpRequest) -> func.HttpResponse:
    """Endpoint de recherche compatible avec le Dashboard"""
    try:
        query = req.params.get('q', '').lower().strip()
        theme_filter = req.params.get('theme', '').lower().strip()
        crit_filter = req.params.get('crit', '').lower().strip()
        conf_filter = req.params.get('conf', '').lower().strip()

        ss = get_spreadsheet()
        results = []
        for name in ["Base_Active", "Rapport_Veille_Auto"]:
            try:
                ws = ss.worksheet(name)
                records = ws.get_all_records()
            except: continue

            for i, row in enumerate(records):
                r = {str(k).strip(): v for k, v in row.items()}
                if query:
                    text_to_search = f"{r.get('Intitulé','')}{r.get('Thème','')}{r.get('Commentaires','')}{r.get('Statut','')}".lower()
                    if query not in text_to_search: continue
                if theme_filter:
                    t = str(r.get('Thème', '')).lower().strip()
                    if theme_filter not in t: continue
                if crit_filter:
                    c = ""
                    for k in ['Criticité', 'criticite', 'Crit']:
                        if k in r: c = str(r[k]).lower().strip()
                    if crit_filter not in c: continue
                if conf_filter:
                    conf = str(r.get('Conformité', '')).lower().strip()
                    if conf_filter == 'nc':
                        if conf not in ['nc', 'non conforme', 'en cours d\'étude', 'à qualifier'] and 'étude' not in conf: continue
                    elif conf_filter == 'c':
                        if conf not in ['c', 'conforme']: continue
                    elif conf_filter == 'qualif':
                        if conf != "": continue
                    elif conf_filter not in conf: continue

                r['source_sheet'] = name
                r['row_idx'] = i + 2
                r['url'] = str(r.get('Lien Internet', f"https://www.google.com/search?q={str(r.get('Intitulé','')).replace(' ', '+')}"))
                results.append(r)
        return func.HttpResponse(json.dumps(results), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")

@app.route(route="stats", methods=["GET"])
def stats(req: func.HttpRequest) -> func.HttpResponse:
    """Calcul des statistiques en temps réel pour le dashboard"""
    try:
        theme_f = req.params.get('theme', '').lower().strip()
        crit_f = req.params.get('crit', '').lower().strip()
        conf_f = req.params.get('conf', '').lower().strip()

        ss = get_spreadsheet()
        vals_base = ss.worksheet("Base_Active").get_all_values()
        vals_news = ss.worksheet("Rapport_Veille_Auto").get_all_values()
        
        if len(vals_base) <= 1:
            return func.HttpResponse(json.dumps({"error": "Base_Active est vide"}), status_code=404, mimetype="application/json")
            
        header_base = [c.strip() for c in vals_base[0]]
        rows_base = vals_base[1:]
        rows_news = vals_news[1:] if len(vals_news) > 1 else []

        col_conf = find_col(header_base, "Conformité") or 12
        col_next = find_col(header_base, "date de la prochaine évaluation") or 16
        col_theme = find_col(header_base, "Thème") or 7
        col_title = find_col(header_base, "Intitulé ") or 6
        col_crit = find_col(header_base, "Criticité") or 18
        col_proof = find_col(header_base, "Preuves disponibles") or 24

        applicable_rows = []
        for r in rows_base:
            if len(r) < col_conf: continue
            conf_val = r[col_conf-1].lower().strip()
            if conf_val not in ['sans objet', 'archivé', '']:
                applicable_rows.append(r)
        
        filtered_rows = []
        for r in applicable_rows:
            if theme_f:
                t_raw = r[col_theme-1] if len(r) >= col_theme else ""
                t_title = r[col_title-1] if len(r) >= col_title else ""
                if theme_f not in clean_theme(t_raw, t_title).lower(): continue
            if crit_f:
                c_raw = r[col_crit-1].lower().strip() if len(r) >= col_crit else "basse"
                if crit_f not in c_raw: continue
            if conf_f:
                cv = r[col_conf-1].lower().strip()
                if conf_f == 'nc':
                    if cv not in ['nc', 'non conforme', 'en cours d\'étude', 'à qualifier'] and 'étude' not in cv: continue
                elif conf_f == 'c':
                    if cv not in ['c', 'conforme']: continue
                elif conf_f == 'qualif':
                    if cv != "": continue
                elif conf_f not in cv: continue
            filtered_rows.append(r)

        count_mec = 0; count_reeval = 0; count_qualif = 0; c_count = 0; nc_count = 0; with_proof_count = 0
        theme_map = {}; crit_map = {"Haute": 0, "Moyenne": 0, "Basse": 0}

        def is_past(date_str):
            date_str = str(date_str).strip()
            if not date_str or date_str.lower() in ['', 'nan']: return True
            for fmt in ['%d/%m/%Y', '%Y-%m-%d']:
                try: return datetime.strptime(date_str, fmt) <= datetime.now()
                except: continue
            return True

        for r in filtered_rows:
            conf_val = r[col_conf-1].strip()
            if conf_val.upper() in ['NC', 'NON CONFORME', 'EN COURS D\'ÉTUDE', 'À QUALIFIER'] or 'ÉTUDE' in conf_val.upper(): count_mec += 1
            if conf_val == "": count_qualif += 1
            is_c = conf_val.lower() in ['c', 'conforme']
            past = is_past(r[col_next-1]) if len(r) >= col_next else True
            if is_c:
                if past: count_reeval += 1
                else: c_count += 1
            if conf_val.upper() in ['NC', 'NON CONFORME']: nc_count += 1
            t_raw = r[col_theme-1] if len(r) >= col_theme else ""; t_title = r[col_title-1] if len(r) >= col_title else ""
            t_clean = clean_theme(t_raw, t_title); theme_map[t_clean] = theme_map.get(t_clean, 0) + 1
            c_raw = r[col_crit-1].strip().capitalize() if len(r) >= col_crit else "Basse"
            if c_raw in crit_map: crit_map[c_raw] += 1
            if len(r) >= col_proof and r[col_proof-1].lower().strip() == 'oui': with_proof_count += 1

        eval_count = len(filtered_rows) - c_count - nc_count + (len(rows_news) if not any([theme_f, crit_f, conf_f]) else 0)
        proof_score = f"{round((with_proof_count / len(filtered_rows) * 100), 1)}%" if filtered_rows else "0%"
        sorted_themes = sorted(theme_map.items(), key=lambda x: x[1], reverse=True)[:12]

        stats = {
            "last_update": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "kpis": {
                "total_tracked": len(rows_base), "applicable": len(applicable_rows),
                "actions_required": count_mec + count_reeval + count_qualif,
                "sub_mec": count_mec, "sub_reeval": count_reeval, "sub_qualif": count_qualif,
                "alerts_ia": len(rows_news), "proof_score": proof_score
            },
            "themes": {"labels": [x[0] for x in sorted_themes], "values": [x[1] for x in sorted_themes]},
            "compliance": {"labels": ["Conforme", "Non Conforme", "À évaluer"], "values": [c_count, nc_count, eval_count]},
            "criticite": {"labels": ["Haute", "Moyenne", "Basse"], "values": [crit_map["Haute"], crit_map["Moyenne"], crit_map["Basse"]]}
        }
        return func.HttpResponse(json.dumps(stats), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")

@app.route(route="proofs", methods=["GET"])
def proofs(req: func.HttpRequest) -> func.HttpResponse:
    """Analyse les preuves avec FUSION intelligente"""
    try:
        ss = get_spreadsheet()
        vals_base = ss.worksheet("Base_Active").get_all_values()
        vals_news = ss.worksheet("Rapport_Veille_Auto").get_all_values()
        
        header_base = [c.strip() for c in vals_base[0]]; rows_base = vals_base[1:]
        header_news = [c.strip() for c in vals_news[0]]; rows_news = vals_news[1:]
        
        col_p_base = find_col(header_base, "Preuve de Conformité Attendue") or 19
        col_p_news = find_col(header_news, "Preuve de Conformité Attendue") or 19
        col_t_base = find_col(header_base, "Intitulé ") or 6
        col_t_news = find_col(header_news, "Intitulé") or 6

        cat_agg = {}
        def process_rows(rows, col_p, col_t):
            for r in rows:
                if len(r) < col_p: continue
                p_text = str(r[col_p-1]).strip(); title = str(r[col_t-1]).strip() if len(r) >= col_t else "Inconnu"
                if not p_text or p_text.lower() in ["nan", "n/a", "-", ""] or len(p_text) < 3: continue
                cat_name = categorize_proof(p_text); norm_label = normalize_proof_label(p_text)
                if cat_name not in cat_agg: cat_agg[cat_name] = {}
                if norm_label not in cat_agg[cat_name]: cat_agg[cat_name][norm_label] = {"count": 0, "instances": set(), "titles": []}
                cat_agg[cat_name][norm_label]["count"] += 1; cat_agg[cat_name][norm_label]["instances"].add(p_text)
                if title not in cat_agg[cat_name][norm_label]["titles"]: cat_agg[cat_name][norm_label]["titles"].append(title)

        process_rows(rows_base, col_p_base, col_t_base)
        process_rows(rows_news, col_p_news, col_t_news)

        sorted_cats = sorted(cat_agg.items(), key=lambda x: sum(p["count"] for p in x[1].values()), reverse=True)
        results = []
        for cat_name, labels_data in sorted_cats:
            proof_details = []
            sorted_labels = sorted(labels_data.items(), key=lambda x: x[1]["count"], reverse=True)
            total_items = 0
            for label, data in sorted_labels:
                total_items += data["count"]
                proof_details.append({"proof": label, "count": data["count"], "examples": data["titles"][:5], "variants": list(data["instances"])[:2]})
            results.append({"category": cat_name, "total_count": total_items, "unique_proofs_count": len(proof_details), "details": proof_details})

        return func.HttpResponse(json.dumps({"total_items": sum(c["total_count"] for c in results), "categories": results}), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(json.dumps({"error": str(e)}), status_code=500, mimetype="application/json")
