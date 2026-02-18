
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

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

def clean_theme(t, row_text=""):
    """Normalisation robuste des thèmes QHSE"""
    t = str(t).upper().strip()
    context = f"{t} {str(row_text).upper()}" if row_text else t
    if 'SANTE' in context or 'TRAVAIL' in context or 'MEDICAL' in context or 'PERSONNEL' in context or 'HYGIENE' in context or 'FORMATION' in context or 'SECURITE' in context or 'EPI' in context: return 'SÉCURITÉ / SANTÉ'
    if 'ENERGIE' in context or 'CARBONE' in context or 'CHAUFFAGE' in context or 'ELECTRI' in context or 'CLIM' in context or 'GAZ' in context or 'ELECTRIC' in context or 'RELEVE' in context: return 'ÉNERGIE'
    if 'PRODUIT' in context or 'LABEL' in context or 'ECO' in context or 'AFFICHAGE' in context or 'RSE' in context or 'ESG' in context or 'MANAGEMENT' in context or 'REACH' in context or 'ROHS' in context or 'SUBSTANCE' in context: return 'RSE & SUBSTANCES'
    if 'BATIMENT' in context or 'IMMOBILIER' in context or 'URBA' in context or 'DEMOLITION' in context or 'SOL' in context or 'INFRA' in context or 'FOSSES' in context or 'CONSTRUCTION' in context: return 'SOLS / INFRASTRUCTURES'
    if 'VEHICULE' in context or 'MOBILITE' in context or 'ADR' in context or 'TMD' in context or 'TRANSPORT' in context or 'FLOTTE' in context: return 'TRANSPORT / ADR'
    if 'EAU' in context or 'EFFLUENT' in context or 'FORAGE' in context or 'PAYSAGE' in context: return 'EAU'
    if 'AIR' in context or 'GES' in context or 'POLLU' in context or 'MACF' in context or 'EMISSION' in context: return 'AIR'
    if 'DECHET' in context or 'REP' in context or 'CIRCULAIRE' in context or 'GACHIS' in context or 'EMBALLAGE' in context or 'PLASTIQUE' in context: return 'DÉCHETS / REP'
    if 'BRUIT' in context or 'SONOR' in context or 'VIBRATION' in context or 'RISQUE' in context or 'ESP' in context or 'CHIMIQ' in context or 'SISMIQUE' in context or 'INCENDIE' in context or 'FOUDROIEMENT' in context or 'EPI' in context: return 'RISQUES & SÉCURITÉ'
    if 'ICPE' in context or 'IOTA' in context or 'INSTALLATION' in context or 'AUTORISATION' in context or 'DECLARATION' in context or 'ENREGISTREMENT' in context: return 'ICPE / IOTA'
    if 'FORET' in context or 'BOIS' in context or 'BIODIV' in context or 'NATURE' in context or 'ESPECE' in context: return 'BIODIVERSITÉ / PATRIMOINE'
    if not t or 'DIVER' in t or 'AUTRE' in t or 'DROIT' in t or 'ADMIN' in t or 'TEXTE' in t or 'GOUV' in t or 'GENERAL' in t or 'PROCEDURE' in t:
         return 'ADMINISTRATION / GOUVERNANCE'
    return t

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
    """Calcule les statistiques en temps réel pour le dashboard (Supporte les filtres Power BI)"""
    try:
        # Récupération des filtres
        theme_f = request.args.get('theme', '').lower().strip()
        crit_f = request.args.get('crit', '').lower().strip()
        conf_f = request.args.get('conf', '').lower().strip()

        ss = get_spreadsheet()
        
        # 1. Chargement des données
        vals_base = ss.worksheet("Base_Active").get_all_values()
        vals_news = ss.worksheet("Rapport_Veille_Auto").get_all_values()
        
        if len(vals_base) <= 1:
            return jsonify({"error": "Base_Active est vide"}), 404
            
        header_base = [c.strip() for c in vals_base[0]]
        rows_base = vals_base[1:]
        
        rows_news = vals_news[1:] if len(vals_news) > 1 else []

        # 2. Identification des colonnes
        def get_col_idx(header, names):
            for n in names:
                idx = find_col(header, n)
                if idx: return idx
            return None

        col_conf = get_col_idx(header_base, ["Conformité", "Statut"]) or 12
        col_next = get_col_idx(header_base, ["date de la prochaine évaluation", "Echéance"]) or 16
        col_theme = get_col_idx(header_base, ["Thème", "Grand thème"]) or 7
        col_title = get_col_idx(header_base, ["Intitulé ", "Intitulé", "titre"]) or 6
        col_crit = get_col_idx(header_base, ["Criticité", "criticite", "Crit"]) or 18
        col_proof = get_col_idx(header_base, ["Preuves disponibles"]) or 24

        # 3. Filtrage Initial (Applicables)
        applicable_rows = []
        for r in rows_base:
            if len(r) < col_conf: continue
            conf_val = r[col_conf-1].lower().strip()
            if conf_val not in ['sans objet', 'archivé', '']:
                applicable_rows.append(r)
        
        # 4. FILTRES DYNAMIQUES (Power BI Style)
        filtered_rows = []
        for r in applicable_rows:
            # Filtre Thème
            if theme_f:
                t_raw = r[col_theme-1] if len(r) >= col_theme else ""
                t_title = r[col_title-1] if len(r) >= col_title else ""
                if theme_f not in clean_theme(t_raw, t_title).lower(): continue
            
            # Filtre Criticité
            if crit_f:
                c_raw = r[col_crit-1].lower().strip() if len(r) >= col_crit else "basse"
                if crit_f not in c_raw: continue
            
            # Filtre Conformité
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

        # 5. Calcul des KPIs (Sur les données filtrées)
        def is_mec(val):
            v = str(val).upper().strip()
            return v in ['NC', 'NON CONFORME', 'EN COURS D\'ÉTUDE', 'À QUALIFIER'] or 'ÉTUDE' in v
        
        def is_past(date_str):
            date_str = str(date_str).strip()
            if not date_str or date_str.lower() in ['', 'nan']: return True
            for fmt in ['%d/%m/%Y', '%Y-%m-%d']:
                try: return datetime.strptime(date_str, fmt) <= datetime.now()
                except: continue
            return True

        count_mec = 0
        count_reeval = 0
        count_qualif = 0
        c_count = 0
        nc_count = 0
        with_proof_count = 0
        theme_map = {}
        crit_map = {"Haute": 0, "Moyenne": 0, "Basse": 0}

        for r in filtered_rows:
            conf_val = r[col_conf-1].strip()
            if is_mec(conf_val): count_mec += 1
            if conf_val == "": count_qualif += 1
            
            is_c = conf_val.lower() in ['c', 'conforme']
            past = is_past(r[col_next-1]) if len(r) >= col_next else True
            if is_c:
                if past: count_reeval += 1
                else: c_count += 1
            
            if conf_val.upper() in ['NC', 'NON CONFORME']: nc_count += 1
            
            t_raw = r[col_theme-1] if len(r) >= col_theme else ""
            t_title = r[col_title-1] if len(r) >= col_title else ""
            t_clean = clean_theme(t_raw, t_title)
            theme_map[t_clean] = theme_map.get(t_clean, 0) + 1
            
            c_raw = r[col_crit-1].strip().capitalize() if len(r) >= col_crit else "Basse"
            if c_raw not in crit_map: c_raw = "Basse"
            crit_map[c_raw] += 1
            
            if len(r) >= col_proof and r[col_proof-1].lower().strip() == 'oui':
                with_proof_count += 1

        eval_count = len(filtered_rows) - c_count - nc_count + (len(rows_news) if not any([theme_f, crit_f, conf_f]) else 0)
        proof_score = f"{round((with_proof_count / len(filtered_rows) * 100), 1)}%" if filtered_rows else "0%"

        # Sort themes
        sorted_themes = sorted(theme_map.items(), key=lambda x: x[1], reverse=True)[:12]
        theme_labels = [x[0] for x in sorted_themes]
        theme_values = [x[1] for x in sorted_themes]

        stats = {
            "last_update": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "kpis": {
                "total_tracked": len(rows_base),
                "applicable": len(applicable_rows),
                "actions_required": count_mec + count_reeval + count_qualif,
                "sub_mec": count_mec,
                "sub_reeval": count_reeval,
                "sub_qualif": count_qualif,
                "alerts_ia": len(rows_news),
                "proof_score": proof_score
            },
            "themes": {
                "labels": theme_labels,
                "values": theme_values
            },
            "compliance": {
                "labels": ["Conforme", "Non Conforme", "À évaluer"],
                "values": [c_count, nc_count, eval_count]
            },
            "criticite": {
                "labels": ["Haute", "Moyenne", "Basse"],
                "values": [crit_map["Haute"], crit_map["Moyenne"], crit_map["Basse"]]
            }
        }
        return jsonify(stats)
    except Exception as e:
        print(f"Stats Error: {e}")
        return jsonify({"error": str(e)}), 500
def categorize_proof(p_text):
    """Regroupe les preuves par catégories métier intelligentes"""
    p = p_text.upper().strip()
    
    # Rapports & Bilans
    if any(k in p for k in ['BILAN', 'RAPPORT', 'AUDIT', 'BEGES', 'RELEVÉ', 'SYNTHÈSE', 'REVUE']):
        if 'GES' in p or 'CARBONE' in p: return "Rapports GES / Carbone"
        if 'ÉNERG' in p: return "Audits & Bilans Énergétiques"
        if 'EAU' in p or 'EFFLUENT' in p: return "Suivi des Consommations d'Eau"
        if 'AIR' in p or 'ÉMISSION' in p: return "Mesures & Rapports Air"
        return "Rapports d'Audit & Bilans Périodiques"
        
    # Autorisations & ICPE
    if any(k in p for k in ['ICPE', 'DÉCLARATION', 'AUTORISATION', 'ARRÊTÉ', 'ENREGISTREMENT', 'DOSSIER', 'PREFECT']):
        return "Autorisations Administratives & Dossiers ICPE"
        
    # Certificats & FDS
    if any(k in p for k in ['CERTIFICAT', 'FDS', 'FICHE', 'CONFORMITÉ', 'REACH', 'ROHS', 'ATTESTATION']):
        if 'FDS' in p or 'SÉCURITÉ' in p: return "Fiches de Données de Sécurité (FDS)"
        return "Certificats de Conformité & Attestations Fournisseurs"
        
    # Maintenance & Technique
    if any(k in p for k in ['MAINTENANCE', 'CONTRÔLE', 'ENTRETIEN', 'VÉRIFICATION', 'TEST', 'REGISTRE']):
        if 'INCENDIE' in p or 'SPRINK' in p or 'EXTINCTEUR' in p: return "Sécurité Incendie & Secours"
        return "Maintenance & Contrôles Techniques Périodiques"
        
    # RH & Social
    if any(k in p for k in ['PV', 'CSE', 'FORMATION', 'HABILITATION', 'RISQUE', 'TRAVAIL', 'PERSONNEL']):
        return "Ressources Humaines & Habilitations"
        
    # Déchets
    if any(k in p for k in ['BSD', 'BORDEREAU', 'REGISTRE DÉCHET', 'FILIÈRE', 'DÉCHET']):
        return "Suivi & Bordereaux de Déchets (BSD)"

    return "Autres Preuves & Documents Spécifiques"

# Gestion de l'arbitrage humain (HITL)
ARBITRATION_FILE = 'config/validated_fusions.json'

def load_validated_fusions():
    if not os.path.exists(ARBITRATION_FILE):
        return {"approved": [], "rejected": []}
    try:
        with open(ARBITRATION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"approved": [], "rejected": []}

def normalize_proof_label(p_text):
    """
    Normalisation avancée (Pipeline MLE) :
    1. Nettoyage et Standardisation
    2. COUCHE HITL : Applique les fusions validées par l'utilisateur
    3. Mapping par Dictionnaire Canonique (Heuristique métier)
    4. Fallback : Similarité de Jaccard (Fuzzy Matching DS)
    """
    p_raw = str(p_text).strip()
    p = p_raw.upper().replace('\n', ' ').strip()
    
    # Phase 2: COUCHE HITL (Arbitrage Humain)
    validated = load_validated_fusions()
    for item in validated.get('approved', []):
        if p_raw == item['p1'] or p_raw == item['p2']:
            return item['canonical']

    # Phase 3: TAXONOMIE CANONIQUE (Représente le résultat d'un clustering sémantique préalable)
    canonical_map = {
        "Dossier de Conformité ICPE / Autorisations": ['ICPE', 'ENREGISTREMENT PRÉFECT', 'DÉCLARATION PRÉFECT', 'ARRÊTÉ PRÉFECT', 'RUBRIQUE', 'INSTALLATION CLASSÉE', 'AUTORISATION ENVIRONNEMENTALE'],
        "Déclaration et Paiement de la TGAP (Formulaire 2020)": ['TGAP', 'ACTIVITÉS POLLUANTES', 'FORMULAIRE 2020'],
        "Bilan des Émissions de Gaz à Effet de Serre (BEGES)": ['BEGES', 'BILAN GES', 'BILAN CARBONE', 'ÉMISSIONS DE GAZ', 'RECOURS À L\'ÉNERGIE'],
        "Rapport d'Audit Énergétique Réglementaire": ['AUDIT ENERG', 'AUDIT ÉNERG', 'CONSOMMATION ÉNERGIE', 'BILAN ÉNERG'],
        "Bordereaux de Suivi & Registre des Déchets": ['BSD', 'BORDEREAU DE SUIVI', 'REGISTRE DÉCHET', 'COLLECTE DÉCHET', 'FILIÈRE RÉCUP'],
        "Fiches de Données de Sécurité (FDS)": ['FDS', 'FICHE DE DONNÉES DE SÉCURITÉ', 'SDS', 'SAFETY DATA SHEET'],
        "Certificats de Conformité REACH / RoHS": ['REACH', 'ROHS', 'SUBSTANCES DANGEREUSES', 'PRODUITS CHIMIQUES'],
        "Document Unique d'Évaluation des Risques (DUERP)": ['DUERP', 'DOCUMENT UNIQUE', 'RISQUES PRO', 'ÉVALUATION DES RISQUES'],
        "PV de Consultation du CSE / Dialogue Social": ['CSE', 'PV DE CONSULTATION', 'PROCÈS-VERBAL', 'ÉLECTION PROFESSIONNELLE'],
        "Attestations de Formation & Habilitations": ['FORMATION', 'HABILITATION', 'VÉRIFICATION DES COMPÉTENCES', 'CERTIFICAT D\'APTITUDE'],
        "Maintenance & Contrôles Techniques Périodiques": ['MAINTENANCE', 'CONTRÔLE TECHNIQUE', 'VÉRIFICATION PÉRIODIQUE', 'RÉVISION MACHINE'],
        "Registres & Contrôles Sécurité Incendie": ['INCENDIE', 'SPRINK', 'EXTINCTEUR', 'SYSTÈME DE DÉTECTION', 'ALERTE SECOURS'],
        "Clauses Contractuelles & CGV": ['CONTRAT', 'CGV', 'CLAUSE', 'RESPONSABILITÉ PRODUIT', 'GARANTIE DE CONFORMITÉ'],
        "Suivi des Rejets & Consommations d'Eau": ['EAU', 'EFFLUENT', 'REJET LIQUIDE', 'PRÉLÈVEMENT EAU', 'COMPTEUR EAU'],
        "Mesures & Rapports des Émissions Air": ['AIR', 'ÉMISSION ATMOSPHÉRIQUE', 'CHEMINÉE', 'PRÉLÈVEMENT AIR', 'FILTRE À AIR'],
        "Justificatif de Paiement des Taxes (TICGN/TICPE)": ['TICGN', 'TICPE', 'TAXE INTÉRIEURE', 'GAZ NATUREL', 'ÉLECTRICITÉ'],
        "Plan d'Opération Interne (POI) / Urgence": ['POI', 'PLAN D\'OPÉRATION', 'SITUATION D\'URGENCE', 'SIMULATION D\'ACCIDENT']
    }

    # Phase 2: Heuristique de mapping
    for label, keywords in canonical_map.items():
        if any(k in p for k in keywords):
            return label

    # Phase 3: Fallback Jaccard Similarity (DS Approach)
    # On compare les sets de mots pour attraper les variations non prévues
    p_words = set(p.split())
    best_match = None
    max_sim = 0
    
    for label, keywords in canonical_map.items():
        for k in keywords:
            k_words = set(k.split())
            intersection = len(p_words.intersection(k_words))
            union = len(p_words.union(k_words))
            sim = intersection / union if union > 0 else 0
            if sim > max_sim:
                max_sim = sim
                best_match = label
    
    if max_sim > 0.4: # Seuil de confiance DS
        return best_match

    # Fallback final : Troncature intelligente
    if len(p_text) > 85:
        return p_text.strip()[:82] + "..."
    return p_text.strip()

@app.route('/proofs', methods=['GET'])
def get_proofs():
    """Analyse les preuves avec FUSION intelligente des doublons (Option A+)"""
    try:
        ss = get_spreadsheet()
        
        vals_base = ss.worksheet("Base_Active").get_all_values()
        vals_news = ss.worksheet("Rapport_Veille_Auto").get_all_values()
        
        header_base = [c.strip() for c in vals_base[0]]
        rows_base = vals_base[1:]
        
        header_news = [c.strip() for c in vals_news[0]]
        rows_news = vals_news[1:]
        
        col_proof_base = find_col(header_base, "Preuve de Conformité Attendue") or find_col(header_base, "Preuves attendues") or 19
        col_proof_news = find_col(header_news, "Preuve de Conformité Attendue") or 19
        col_title_base = find_col(header_base, "Intitulé ") or 6
        col_title_news = find_col(header_news, "Intitulé") or 6

        # Structure : { category: { normalized_label: { count: X, instances: [original_texts], titles: [exemples] } } }
        cat_agg = {}
        
        def process_rows(rows, col_p, col_t):
            for r in rows:
                if len(r) < col_p: continue
                p_text = str(r[col_p-1]).strip()
                title = str(r[col_t-1]).strip() if len(r) >= col_t else "Inconnu"
                
                if not p_text or p_text.lower() in ["nan", "n/a", "-", ""] or len(p_text) < 3: continue
                
                cat_name = categorize_proof(p_text)
                norm_label = normalize_proof_label(p_text)
                
                if cat_name not in cat_agg:
                    cat_agg[cat_name] = {}
                
                if norm_label not in cat_agg[cat_name]:
                    cat_agg[cat_name][norm_label] = {"count": 0, "instances": set(), "titles": []}
                
                cat_agg[cat_name][norm_label]["count"] += 1
                cat_agg[cat_name][norm_label]["instances"].add(p_text)
                if title not in cat_agg[cat_name][norm_label]["titles"]:
                    cat_agg[cat_name][norm_label]["titles"].append(title)

        process_rows(rows_base, col_proof_base, col_title_base)
        process_rows(rows_news, col_proof_news, col_title_news)

        # Transformation pour le frontend
        sorted_cats = sorted(cat_agg.items(), key=lambda x: sum(p["count"] for p in x[1].values()), reverse=True)
        
        results = []
        for cat_name, labels_data in sorted_cats:
            proof_details = []
            # On trie les labels normalisés par fréquence
            sorted_labels = sorted(labels_data.items(), key=lambda x: x[1]["count"], reverse=True)
            
            total_items_in_cat = 0
            for label, data in sorted_labels:
                total_items_in_cat += data["count"]
                proof_details.append({
                    "proof": label, # Le label fusionné
                    "count": data["count"],
                    "examples": data["titles"][:5], # Les titres des exigences
                    "variants": list(data["instances"])[:2] # Un aperçu des textes bruts fusionnés
                })

            results.append({
                "category": cat_name,
                "total_count": total_items_in_cat,
                "unique_proofs_count": len(proof_details),
                "details": proof_details
            })

        return jsonify({
            "total_categories": len(results),
            "total_items": sum(c["total_count"] for c in results),
            "categories": results
        })

    except Exception as e:
        print(f"Proofs Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/audit-suggestions', methods=['GET'])
def get_audit_suggestions():
    """Récupère les suggestions générées par CamemBERT pour arbitrage"""
    try:
        csv_path = 'camembert_hits_for_arbitrage.csv'
        if not os.path.exists(csv_path):
            return jsonify([])
        
        df = pd.read_csv(csv_path)
        # On ne garde que ceux non fusionnés
        df = df[df['already_merged_by_heuristic'] == False]
        
        # On filtre ceux déjà arbitrés
        validated = load_validated_fusions()
        arbitrated_pairs = set()
        for item in validated['approved'] + validated['rejected']:
            arbitrated_pairs.add(tuple(sorted([item['p1'], item['p2']])))
            
        suggestions = []
        for _, row in df.iterrows():
            pair = tuple(sorted([row['proof_A'], row['proof_B']]))
            if pair not in arbitrated_pairs:
                suggestions.append({
                    "p1": row['proof_A'],
                    "p2": row['proof_B'],
                    "sim": row['similarity'],
                    "suggested": row['suggested_canonical']
                })
        
        return jsonify(suggestions[:50]) # Limite pour fluidité
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/arbitrate-fusion', methods=['POST'])
def arbitrate_fusion():
    """Enregistre l'arbitrage utilisateur (Approbation / Rejet)"""
    try:
        data = request.json
        p1 = data.get('p1')
        p2 = data.get('p2')
        action = data.get('action') # 'approve' or 'reject'
        canonical = data.get('canonical')
        
        if not p1 or not p2 or not action:
            return jsonify({"error": "Missing params"}), 400
            
        validated = load_validated_fusions()
        
        if action == 'approve':
            validated['approved'].append({
                "p1": p1, "p2": p2, "canonical": canonical, 
                "date": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        else:
            validated['rejected'].append({
                "p1": p1, "p2": p2,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            
        os.makedirs('config', exist_ok=True)
        with open(ARBITRATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(validated, f, indent=2, ensure_ascii=False)
            
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = 5000
    print(f"🚀 GDD Interactivity Server running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
