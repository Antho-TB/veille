"""
=============================================================================
GÉNÉRATEUR DE FICHES DE CONTRÔLE - VEILLE RÉGLEMENTAIRE
=============================================================================

Ce script prend les données (les listes d'alertes) depuis Google Sheets 
et les transforme en de jolies pages web interactives (fiches de contrôle HTML).
Ces pages peuvent être lues sur ordinateur ou sur mobile par les auditeurs
sur le terrain.

"""

import os
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import sys

# Ajouter la racine du projet au path
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from src.core.pipeline import Config

# --- CONFIGURATION (Chemins relatifs à la racine du projet) ---
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../output")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "../../assets")

OUTPUT_NOUVEAUTES = os.path.join(OUTPUT_DIR, "checklist_nouveautes.html")
OUTPUT_BASE = os.path.join(OUTPUT_DIR, "checklist_base_active.html")
LOGOS = {
    "gdd": "../assets/logo_gdd.png",  # Relatif au fichier HTML dans output/
    "tb": "../assets/logo_tb.png"
}

class ChecklistGenerator:
    """
    Cette classe gère la création des pages HTML.
    Elle se connecte à Google Sheets, télécharge les données, 
    les nettoie, puis génère le code HTML de la page web.
    """
    def __init__(self, client=None):
        self.client = client
    
    def connect(self):
        if not os.path.exists(Config.CREDENTIALS_FILE):
            raise FileNotFoundError("Manque credentials.json")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope))

    def get_data(self, worksheet_name):
        """
        Télécharge le contenu d'un onglet précis (worksheet_name) depuis Google Sheets
        et le transforme en un "DataFrame" Pandas (un tableau de données facile à manipuler).
        """
        print(f"--- Chargement des données : {worksheet_name} ---")
        if not self.client: self.connect()
        # On ouvre notre fichier Google Sheets en utilisant son ID secret
        sheet = self.client.open_by_key(Config.SHEET_ID)
        
        try:
            # On récupère toutes les informations de l'onglet demandé
            ws = sheet.worksheet(worksheet_name)
            records = ws.get_all_records()
            # On transforme ça en tableau de données Pandas
            df = pd.DataFrame(records)
            
            # Normalisation des colonnes (suppression des espaces)
            df.columns = [c.strip() for c in df.columns]
            return df
        except Exception as e:
            print(f"Erreur lors de la lecture de l'onglet {worksheet_name} : {e}")
            return pd.DataFrame()

    def clean_theme(self, t, row_text=""):
        """
        MLE Tip: Cette fonction fait partie du 'Feature Engineering' / 'Data Cleaning'.
        Elle normalise les thèmes disparates en catégories QHSE propres (Standard APORA intègre).
        """
        t = str(t).upper().strip()
        context = f"{t} {str(row_text).upper()}" if row_text else t
        
        # 1. Mots-clés prioritaires (Massifs)
        if 'SANTE' in context or 'TRAVAIL' in context or 'MEDICAL' in context or 'PERSONNEL' in context or 'HYGIENE' in context or 'FORMATION' in context or 'SECURITE' in context or 'EPI' in context: return 'SÉCURITÉ / SANTÉ'
        if 'ENERGIE' in context or 'CARBONE' in context or 'CHAUFFAGE' in context or 'ELECTRI' in context or 'CLIM' in context or 'GAZ' in context or 'ELECTRIC' in context or 'RELEVE' in context or 'THERMIQUE' in context or 'ECONOMIQUES' in context or 'CEE' in context: return 'ÉNERGIE'
        if 'PRODUIT' in context or 'LABEL' in context or 'ECO' in context or 'AFFICHAGE' in context or 'RSE' in context or 'ESG' in context or 'MANAGEMENT' in context or 'REACH' in context or 'ROHS' in context or 'SUBSTANCE' in context: return 'RSE & SUBSTANCES'
        if 'BATIMENT' in context or 'IMMOBILIER' in context or 'URBA' in context or 'DEMOLITION' in context or 'SOL' in context or 'INFRA' in context or 'FOSSES' in context or 'CONSTRUCTION' in context or 'POLLUES' in context: return 'SOLS / INFRASTRUCTURES'
        if 'VEHICULE' in context or 'MOBILITE' in context or 'ADR' in context or 'TMD' in context or 'TRANSPORT' in context or 'FLOTTE' in context: return 'TRANSPORT / ADR'
        if 'EAU' in context or 'EFFLUENT' in context or 'FORAGE' in context or 'PAYSAGE' in context: return 'EAU'
        if 'AIR' in context or 'GES' in context or 'POLLU' in context or 'MACF' in context or 'EMISSION' in context: return 'AIR'
        if 'DECHET' in context or 'REP' in context or 'CIRCULAIRE' in context or 'GACHIS' in context or 'EMBALLAGE' in context or 'PLASTIQUE' in context: return 'DÉCHETS / REP'
        if 'BRUIT' in context or 'SONOR' in context or 'VIBRATION' in context or 'RISQUE' in context or 'ESP' in context or 'CHIMIQ' in context or 'SISMIQUE' in context or 'INCENDIE' in context or 'FOUDROIEMENT' in context or 'EPI' in context: return 'RISQUES & SÉCURITÉ'
        if 'ICPE' in context or 'IOTA' in context or 'INSTALLATION' in context or 'AUTORISATION' in context or 'DECLARATION' in context or 'ENREGISTREMENT' in context: return 'ICPE / IOTA'
        if 'FORET' in context or 'BOIS' in context or 'BIODIV' in context or 'NATURE' in context or 'ESPECE' in context: return 'BIODIVERSITÉ / PATRIMOINE'
        if 'FISCALITE' in context or 'TAXE' in context or 'REDEVANCE' in context: return 'FISCALITÉ / TAXES'
        
        # 2. Si pas de match, on reste en GOUVERNANCE
        if not t or 'DIVER' in t or 'AUTRE' in t or 'DROIT' in t or 'ADMIN' in t or 'TEXTE' in t or 'GOUV' in t or 'GENERAL' in t or 'PROCEDURE' in t:
             return 'ADMINISTRATION / GOUVERNANCE'
             
        return t

    def generate_html(self, df, title, output_file, is_base_active=False):
        """
        Prend le tableau de données (df), et construit un gros fichier HTML 
        pour afficher toutes les alertes de manière visuelle et cliquable.
        """
        from datetime import datetime as dt
        print(f"--- Génération du HTML : {output_file} ---")
        if df.empty:
            print("Aucune donnée à traiter.")
            return

        # Filtrage
        if is_base_active:
            # Pour la base active, on filtre par date de prochaine évaluation
            if 'date de la prochaine évaluation' in df.columns:
                today = dt.now()
                
                def needs_evaluation(date_str):
                    """Retourne True si la date est vide ou dépassée"""
                    date_str = str(date_str).strip()
                    if not date_str or date_str.lower() in ['', 'nan', 'none']:
                        return True  # Pas de date = à évaluer
                    
                    # Tentative de parsing de la date (formats courants)
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                        try:
                            eval_date = dt.strptime(date_str, fmt)
                            return eval_date <= today  # Date dépassée
                        except:
                            continue
                    return True  # Si format inconnu, on affiche par sécurité
                
                to_check = df[df['date de la prochaine évaluation'].apply(needs_evaluation)]
            else:
                to_check = df  # Si pas de colonne, on affiche tout
        else:
            if 'Conformité' in df.columns:
                to_check = df[~df['Conformité'].astype(str).str.lower().isin(['conforme', 'archivé', 'sans objet'])]
            else:
                to_check = df
        
        # Nettoyage des lignes vides (sans titre) et sans action
        to_check = to_check[
            (to_check['Intitulé'].astype(str).str.strip() != "") & 
            (to_check['Intitulé'].astype(str).str.strip().str.lower() != "titre manquant") &
            (to_check['Commentaires'].astype(str).str.strip() != "") &
            (to_check['Commentaires'].astype(str).str.strip().str.lower() != "aucune action spécifiée")
        ]

        if 'Thème' not in to_check.columns: to_check['Thème'] = 'Général'
        
        themes = to_check['Thème'].unique()
        
        # Déterminer le nom de l'onglet source pour le JS
        current_sheet = "Base_Active" if is_base_active else "Rapport_Veille_Auto"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                
                body {{ 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    color: #212529; 
                    padding: 20px;
                    line-height: 1.6;
                    min-height: 100vh;
                }}
                
                .container {{ 
                    max-width: 1200px; 
                    margin: 0 auto; 
                    background: white; 
                    box-shadow: 0 10px 40px rgba(0,0,0,0.08);
                    border-radius: 12px; 
                    overflow: hidden;
                    animation: slideIn 0.5s ease-out;
                }}
                
                @keyframes slideIn {{
                    from {{ opacity: 0; transform: translateY(20px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
                
                /* Header */
                .header {{ 
                    background: linear-gradient(135deg, #1a1f36 0%, #2d3748 100%);
                    color: white; 
                    padding: 35px 40px; 
                    text-align: center;
                    position: relative;
                    border-bottom: 3px solid #d64545;
                }}
                
                .header-logos {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 20px;
                    margin-bottom: 20px;
                }}
                
                .header-logos img {{
                    height: 55px;
                    width: auto;
                    padding: 10px;
                    border-radius: 6px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                }}
                
                .header-logos img:first-child {{ background: white; }}
                .header-logos img:last-child {{ background: #2d3748; border: 2px solid rgba(255,255,255,0.2); }}
                
                .header h1 {{ 
                    font-size: 2.2em; 
                    font-weight: 600; 
                    margin-bottom: 10px; 
                    letter-spacing: -0.3px;
                }}
                
                .header-info {{ 
                    font-size: 0.95em; 
                    opacity: 0.9; 
                    margin-top: 8px; 
                    font-weight: 300;
                }}
                
                /* Intro */
                .intro {{ 
                    padding: 30px 40px; 
                    background: #f8f9fa;
                    border-bottom: 1px solid #dee2e6;
                    text-align: center;
                }}
                
                .intro strong {{ 
                    color: #1a1f36; 
                    display: block; 
                    margin-bottom: 10px; 
                    font-size: 1.2em;
                    font-weight: 600;
                }}
                
                .intro p {{ 
                    margin: 6px 0; 
                    font-size: 0.95em; 
                    color: #495057;
                    max-width: 800px;
                    margin-left: auto;
                    margin-right: auto;
                }}
                
                .intro .auto-info {{ 
                    font-size: 0.88em; 
                    color: #6c757d; 
                    margin-top: 14px; 
                    padding: 10px 18px;
                    background: white;
                    border-radius: 6px;
                    display: inline-block;
                    border: 1px solid #e9ecef;
                }}

                .warning-text {{
                    color: #c53030;
                    font-weight: 600;
                    margin-top: 15px !important;
                    background-color: #fff5f5;
                    padding: 10px;
                    border-radius: 4px;
                    border: 1px solid #feb2b2;
                    display: inline-block;
                }}
                
                /* Content */
                .content {{ padding: 35px; }}
                
                .theme-section {{ 
                    margin-bottom: 35px;
                    animation: fadeIn 0.5s ease-out;
                }}
                
                @keyframes fadeIn {{
                    from {{ opacity: 0; transform: translateY(15px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
                
                .theme-header {{ 
                    background: linear-gradient(135deg, #1a1f36 0%, #2d3748 100%);
                    color: white; 
                    padding: 16px 22px; 
                    font-size: 1.15em; 
                    font-weight: 600;
                    border-radius: 8px;
                    margin-bottom: 18px;
                    box-shadow: 0 2px 8px rgba(26, 31, 54, 0.15);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    border-left: 4px solid #d64545;
                }}
                
                .theme-header::before {{ content: '📂'; font-size: 1.2em; }}
                
                /* Items */
                /* Items - Style LMS Auditeur */
                .item {{ 
                    background: white;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 22px; 
                    margin-bottom: 25px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                    transition: all 0.25s ease;
                    position: relative;
                    border-left: 6px solid #6c757d;
                }}
                
                .item.crit-haute {{ border-left: 6px solid #dc2626; }}
                .item.crit-moyenne {{ border-left: 6px solid #f59e0b; }}
                .item.crit-basse {{ border-left: 6px solid #10b981; }}
                
                .item:hover {{ 
                    border-color: #adb5bd;
                    box-shadow: 0 8px 15px rgba(0,0,0,0.08);
                    transform: translateY(-2px);
                }}
                
                .filter-bar {{
                    background: white;
                    padding: 15px 40px;
                    display: flex;
                    justify-content: center;
                    gap: 15px;
                    border-bottom: 1px solid #eee;
                    position: sticky;
                    top: 0;
                    z-index: 100;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                }}

                .filter-btn {{
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-size: 0.85em;
                    font-weight: 600;
                    cursor: pointer;
                    border: 1px solid #ddd;
                    background: #f8f9fa;
                    transition: all 0.2s;
                    color: #4b5563;
                }}

                .filter-btn.active {{ background: #1a1f36; color: white; border-color: #1a1f36; }}
                .filter-btn.crit-haute:hover {{ background: #fee2e2; color: #991b1b; }}
                .filter-btn.crit-moyenne:hover {{ background: #fef3c7; color: #92400e; }}
                .filter-btn.crit-basse:hover {{ background: #d1fae5; color: #065f46; }}
                
                .item-header {{ 
                    display: flex; 
                    justify-content: space-between; 
                    align-items: flex-start; 
                    margin-bottom: 14px;
                    gap: 14px;
                }}
                
                .item-title {{ 
                    font-weight: 600; 
                    font-size: 1.05em; 
                    color: #1a1f36; 
                    flex-grow: 1;
                    line-height: 1.4;
                }}
                
                .item-title a {{ color: #1a1f36; text-decoration: none; transition: color 0.2s; }}
                .item-title a:hover {{ color: #d64545; }}
                
                .row-badge {{ 
                    background: #f8f9fa; color: #495057; 
                    padding: 5px 12px; border-radius: 16px; 
                    font-size: 0.75em; font-weight: 600;
                    white-space: nowrap; border: 1px solid #dee2e6;
                }}
                
                .item-meta {{ display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }}
                
                .tag {{ 
                    background: #f8f9fa; color: #495057;
                    padding: 5px 11px; border-radius: 5px; 
                    font-size: 0.85em; font-weight: 500;
                    border: 1px solid #e9ecef;
                }}
                
                .item-action {{ 
                    background: #fff3cd; color: #856404; 
                    padding: 15px 17px; border-radius: 6px; 
                    margin-bottom: 16px; border-left: 3px solid #ffc107;
                    font-size: 0.95em; line-height: 1.6;
                }}
                
                .item-action strong {{ color: #664d03; display: block; margin-bottom: 5px; }}
                
                /* Barres de statut (Cases à cocher) */
                .status-bar {{
                    display: flex;
                    gap: 12px;
                    margin-bottom: 15px;
                    flex-wrap: wrap;
                    padding-bottom: 15px;
                    border-bottom: 1px solid #f1f3f5;
                }}

                .status-option {{
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    background: #f8f9fa;
                    padding: 8px 14px;
                    border-radius: 20px;
                    border: 1px solid #e9ecef;
                    cursor: pointer;
                    font-size: 0.9em;
                    font-weight: 500;
                    transition: all 0.2s;
                }}

                .status-option:hover {{
                    background: #e9ecef;
                    border-color: #ced4da;
                }}

                .status-option input[type="radio"] {{
                    accent-color: #1a1f36;
                    width: 16px;
                    height: 16px;
                    cursor: pointer;
                }}

                /* Zone Observations */
                .obs-section {{ margin-top: 10px; }}

                .obs-label {{
                    font-weight: 600;
                    color: #1a1f36;
                    margin-bottom: 8px;
                    display: block;
                    font-size: 0.95em;
                }}
                
                textarea {{ 
                    width: 100%; padding: 12px; border: 1px solid #ced4da; 
                    border-radius: 6px; height: 85px; 
                    font-family: inherit; font-size: 0.93em; resize: vertical;
                    transition: all 0.2s;
                }}
                
                textarea:focus {{ outline: none; border-color: #1a1f36; box-shadow: 0 0 0 3px rgba(26, 31, 54, 0.08); }}
                
                /* Footer */
                .footer {{ 
                    text-align: center; padding: 28px; background: #f8f9fa;
                    color: #6c757d; font-size: 0.85em;
                    border-top: 1px solid #dee2e6; font-weight: 500;
                }}
                
                @media print {{
                    body {{ background: white; padding: 0; }}
                    .container {{ box-shadow: none; border-radius: 0; }}
                    .item {{ page-break-inside: avoid; border: 1px solid #ccc; }}
                }}
                
                /* Interactivity UI */
                .saving {{ opacity: 0.6; pointer-events: none; }}
                .save-indicator {{
                    position: fixed; bottom: 20px; right: 20px;
                    background: #1a1f36; color: white;
                    padding: 10px 20px; border-radius: 30px;
                    font-size: 0.8em; display: none; z-index: 1000;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                }}
                .item.removed {{
                    transform: translateX(100px);
                    opacity: 0;
                    margin-top: -100px;
                    transition: all 0.5s ease-in-out;
                }}
                .item.processed {{
                    opacity: 0.5;
                    filter: grayscale(1);
                    pointer-events: none;
                    border-color: #dee2e6 !important;
                    background: #f8f9fa !important;
                }}
            </style>
        </head>
        <body>
            <div id="save-indicator" class="save-indicator">Synchronisation en cours...</div>
            <div class="container">
                <div class="header">
                    <div class="header-logos">
                        <img src="{LOGOS['gdd']}" alt="GDD Logo">
                        <img src="{LOGOS['tb']}" alt="TB Groupe Logo">
                    </div>
                    <h1>Fiche de Contrôle - {title.replace('Fiche Contrôle - ', '')}</h1>
                    <div class="header-info">
                        Généré le {dt.now().strftime('%d/%m/%Y à %H:%M')}<br>
                        Pour l'équipe Qualité de TB Groupe
                    </div>
                </div>
        """
        # Calcul des compteurs
        count_all = len(to_check)
        
        # Robustesse Criticité : on remplace vide par 'Basse'
        to_check['Crit_Norm'] = to_check.get('Criticité', pd.Series(['Basse']*len(to_check)))
        to_check['Crit_Norm'] = to_check['Crit_Norm'].replace('', 'Basse').fillna('Basse').astype(str).str.strip().str.capitalize()
        
        # Vérification si la colonne n'existait pas du tout (fallback)
        if 'Crit_Norm' not in to_check.columns or to_check['Crit_Norm'].isnull().all():
             to_check['Crit_Norm'] = 'Basse'

        count_haute = len(to_check[to_check['Crit_Norm'] == 'Haute'])
        count_moyenne = len(to_check[to_check['Crit_Norm'] == 'Moyenne'])
        count_basse = len(to_check[to_check['Crit_Norm'] == 'Basse'])
        
        # Pour Mise en Place (MEC)
        # On reproduit la logique utilisée plus bas dans la boucle
        # is_mec = "étude" in conf_val or not is_base_active
        def check_mec(row):
            conf_val = str(row.get('Conformité', '')).lower()
            return "étude" in conf_val or not is_base_active
            
        count_mec = len(to_check[to_check.apply(check_mec, axis=1)])

        # Filtre Bar (Criticité)
        html_content += f"""
            <div class="filter-bar">
                <button class="filter-btn active" onclick="filterItems('all', 'all', this)">Tout ({count_all})</button>
                <button class="filter-btn crit-haute" onclick="filterItems('crit', 'Haute', this)">🟥 Haute ({count_haute})</button>
                <button class="filter-btn crit-moyenne" onclick="filterItems('crit', 'Moyenne', this)">🟧 Moyenne ({count_moyenne})</button>
                <button class="filter-btn crit-basse" onclick="filterItems('crit', 'Basse', this)">🟨 Basse ({count_basse})</button>
                <button class="filter-btn" style="border-color: #8b5cf6; color: #8b5cf6;" onclick="filterItems('type', 'MEC', this)">À mettre en place ({count_mec})</button>
            </div>
        """
        # Intro Textes Personnalisés
        if is_base_active:
            intro_text = """
                <div class="intro">
                    <strong>📋 Checklist Base Active</strong>
                    <p>Cette fiche présente les textes réglementaires nécessitant une réévaluation (date dépassée ou non planifiée). Vérifiez la conformité de chaque point et notez vos observations.</p>
                    <p class="auto-info">ℹ️ Automatisation : Cette fiche est générée quotidiennement à 8h00. Les items proviennent des nouveautés évaluées (transférées automatiquement depuis le Rapport de Veille).</p>

                </div>
            """
        else:
            intro_text = """
                <div class="intro">
                    <strong>🆕 Checklist Nouveautés</strong>
                    <p>Cette fiche présente les nouveaux textes détectés par l'IA qui nécessitent une évaluation initiale. Qualifiez l'impact pour GDD et déterminez les actions à mettre en place.</p>
                    <p class="auto-info">ℹ️ Automatisation : L'IA scanne le web quotidiennement à 8h00 et filtre les textes pertinents pour GDD (ICPE, Métaux, HSE). Une fois évalués (date saisie dans le Google Sheet), les items sont automatiquement transférés vers la Base Active.</p>

                </div>
            """
        
        html_content += intro_text
        html_content += '<div class="content">'
        
        # --- BOUCLE PRINCIPALE ---
        for theme in sorted(themes):
            if not theme: theme_display = "Non classé"
            else: theme_display = theme
            
            section_items = to_check[to_check['Thème'] == theme]
            if section_items.empty: continue

            # Ouverture Theme
            html_content += f"""
            <div class="theme-section">
                <div class="theme-header">{theme_display} ({len(section_items)})</div>
            """
            
            for index, row in section_items.iterrows():
                sheet_row = index + 2
                
                titre = row.get('Intitulé', '⚠️ Titre manquant')
                # Lien Robuste
                url = str(row.get('Lien Internet', '')).strip()
                if not url.startswith('http') and titre != '⚠️ Titre manquant':
                    # Fallback Recherche Google si l'URL est cassée ou manquante
                    url = f"https://www.google.com/search?q={titre.replace(' ', '+')}"
                
                action = row.get('Commentaires', '')
                if not action: action = "Aucune action spécifiée."
                
                date_eval = row.get('date de la dernère évaluation', 'Jamais')
                type_texte = row.get('Type de texte', 'N/A')
                date_texte = row.get('Date', 'N/A')
                
                # RECHERCHE ROBUSTE DES COLONNES (Accents / Espaces)
                def get_val(r, possible_keys, default=""):
                    for k in possible_keys:
                        if k in r and str(r[k]).strip(): return str(r[k]).strip()
                    return default

                crit = get_val(row, ['Criticité', 'criticite', 'Crit'], 'Basse').capitalize()
                preuve = get_val(row, ['Preuve de Conformité Attendue', 'preuve_attendue', 'Preuve'], 'Non spécifiée')
                
                # Si par erreur la preuve contient "Moyenne" or "Haute", on nettoie
                if preuve in ['Moyenne', 'Haute', 'Basse']: preuve = "À définir"
                
                # Suivi des preuves disponibles
                preuves_dispo = str(row.get('Preuves disponibles', 'Non')).strip().capitalize()
                is_proof_ok = preuves_dispo == 'Oui'
                proof_bg = "bg-green-100 text-green-800" if is_proof_ok else "bg-red-100 text-red-800"
                proof_text = "✅ Preuve de conformité disponible" if is_proof_ok else "❌ En attente de preuve physique"
                
                # Détermination du Type (MEC vs Réévaluation)
                conf_val = str(row.get('Conformité', '')).lower()
                is_mec = "étude" in conf_val or not is_base_active
                item_type = "MEC" if is_mec else "REVAL"

                is_informative = str(type_texte).lower() in ["pour info", "pour information", "à titre indicatif"]
                eval_tag = f'<span class="tag">🔍 Dern. Éval: {date_eval}</span>' if not is_informative else ""

                # Item
                html_content += f"""
                <div class="item crit-{crit.lower()}" data-crit="{crit}" data-type="{item_type}" data-proof="{'Oui' if is_proof_ok else 'Non'}">
                    <div class="item-header">
                        <div class="item-title">
                            <span class="row-badge">Sheet Ligne: {sheet_row}</span>
                            <a href="{url}" target="_blank">{titre}</a>
                        </div>
                    </div>
                    <div class="item-meta">
                        <span class="tag">📅 Texte: {date_texte}</span>
                        <span class="tag">📄 Type: {type_texte}</span>
                        {eval_tag}
                        <span class="tag {proof_bg}" id="proof-tag-{sheet_row}">{proof_text}</span>
                    </div>
                    
                    <div class="item-action">
                        <strong>👉 Action / Résumé :</strong>
                        {action}
                    </div>

                    <div class="item-action" style="background: #f0f7ff; border-left-color: #0ea5e9; margin-top: 10px;">
                        <strong>🛡️ Preuve attendue (Audit) :</strong>
                        <textarea id="proof_{sheet_row}" style="font-size: 0.9em; color: #1e40af; font-style: italic; background: transparent; border: 1px dashed #0ea5e9; height: 60px; margin-top: 5px;"
                                  onblur="syncProof({sheet_row}, this.value)">{preuve}</textarea>
                    </div>

                    <div class="status-bar">
                        <label class="status-option">
                            <input type="radio" name="status_{sheet_row}" value="conforme" onclick="executeAction('conforme', {sheet_row})"> ✅ Conforme
                        </label>
                        <label class="status-option">
                            <input type="radio" name="status_{sheet_row}" value="non_conforme" onclick="executeAction('non_conforme', {sheet_row})"> ❌ Non Conforme
                        </label>
                        <label class="status-option" style="background: {'#dcfce7' if is_proof_ok else '#fee2e2'}; border-color: {'#86efac' if is_proof_ok else '#fca5a5'};">
                            <input type="checkbox" id="proof_check_{sheet_row}" {'checked' if is_proof_ok else ''} 
                                   onchange="toggleProof({sheet_row}, this.checked)"> 📁 Preuve Dispo
                        </label>
                        <label class="status-option">
                            <input type="radio" name="status_{sheet_row}" value="info" onclick="executeAction('info', {sheet_row})"> ℹ️ Pour Info
                        </label>
                    </div>
                        <label class="status-option">
                            <input type="radio" name="status_{sheet_row}" value="supprimer" onclick="executeAction('supprimer', {sheet_row})"> 🗑️ Supprimer
                        </label>
                    </div>

                    <div class="obs-section">
                        <label class="obs-label">Observations :</label>
                        <textarea id="obs_{sheet_row}" placeholder="Saisir vos remarques ici..." 
                                  onblur="syncObservation({sheet_row}, this.value)">{row.get('Commentaires (ALSAPE, APORA…)', '')}</textarea>
                    </div>

                </div> """
            
            # Fermeture Theme
            html_content += "</div>"

        # Fin du contenu et Ajout du Footer UNIQUE
        html_content += f"""
            </div> <div class="footer">
                Généré par l'Assistant Veille Réglementaire GDD, Anthony, Service Data&IA
            </div>
            
            </div> 
            
            <script>
                const SHEET_NAME = "{current_sheet}";
                const API_BASE = "http://127.0.0.1:5000";

                function showLoading(show) {{
                    document.getElementById('save-indicator').style.display = show ? 'block' : 'none';
                }}

                async function toggleProof(rowIdx, isChecked) {{
                    const statusVal = isChecked ? 'Oui' : 'Non';
                    showLoading(true);
                    try {{
                        const res = await fetch(`${{API_BASE}}/sync-observation`, {{ // On réutilise sync pour économiser un endpoint ou on en crée un
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ 
                                sheet_name: SHEET_NAME, 
                                row_idx: rowIdx, 
                                column: 'Preuves disponibles',
                                text: statusVal 
                            }})
                        }});
                        const data = await res.json();
                        if (data.success) {{
                            const tag = document.getElementById(`proof-tag-${{rowIdx}}`);
                            tag.className = `tag ${{isChecked ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}}`;
                            tag.innerText = isChecked ? "✅ Preuve de conformité disponible" : "❌ En attente de preuve physique";
                            
                            // Colorer le label du checkbox
                            const checkbox = document.getElementById(`proof_check_${{rowIdx}}`);
                            checkbox.parentElement.style.background = isChecked ? '#dcfce7' : '#fee2e2';
                            checkbox.parentElement.style.borderColor = isChecked ? '#86efac' : '#fca5a5';
                        }}
                    }} catch (e) {{
                        alert("Erreur de synchronisation Preuves.");
                    }}
                    showLoading(false);
                }}

                async function syncObservation(rowIdx, text) {{
                    showLoading(true);
                    try {{
                        const res = await fetch(`${{API_BASE}}/sync-observation`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ sheet_name: SHEET_NAME, row_idx: rowIdx, text: text }})
                        }});
                        const data = await res.json();
                        if (data.success) console.log('Observation synced');
                    }} catch (e) {{
                        alert("Erreur de synchronisation. Vérifiez que le serveur Flask tourne.");
                    }}
                    showLoading(false);
                }}

                async function syncProof(rowIdx, text) {{
                    showLoading(true);
                    try {{
                        const res = await fetch(`${{API_BASE}}/sync-observation`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ 
                                sheet_name: SHEET_NAME, 
                                row_idx: rowIdx, 
                                column: 'Preuve de Conformité Attendue',
                                text: text 
                            }})
                        }});
                        const data = await res.json();
                        if (data.success) console.log('Proof synced');
                    }} catch (e) {{
                        alert("Erreur de synchronisation Preuve.");
                    }}
                    showLoading(false);
                }}

                async function executeAction(action, rowIdx) {{
                    if (action === 'supprimer' && !confirm('Supprimer définitivement cette ligne ?')) return;
                    
                    showLoading(true);
                    try {{
                        const res = await fetch(`${{API_BASE}}/execute-action`, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ action: action, sheet_name: SHEET_NAME, row_idx: rowIdx }})
                        }});
                        const data = await res.json();
                        if (data.success) {{
                            // Effet visuel : Geler la carte
                            const inputs = document.getElementsByName(`status_${{rowIdx}}`);
                            const card = inputs[0].closest('.item');
                            card.classList.add('processed');
                            
                            // Ajout bouton Annuler (Un-grey)
                            if (!card.querySelector('.undo-btn')) {{
                                const undoBtn = document.createElement('button');
                                undoBtn.className = 'undo-btn';
                                undoBtn.innerText = '↺ Annuler la validation (Dégriser)';
                                undoBtn.style.cssText = 'margin-top: 12px; padding: 6px 12px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; display: block; font-size: 0.8em; font-weight: 600;';
                                undoBtn.onclick = () => {{
                                    card.classList.remove('processed');
                                    undoBtn.remove();
                                }};
                                card.appendChild(undoBtn);
                            }}
                        }}
                    }} catch (e) {{
                        alert("Erreur d'action. Vérifiez que le serveur Flask tourne.");
                    }}
                    showLoading(false);
                }}
                function filterItems(attr, val, btn) {{
                    const items = document.querySelectorAll('.item');
                    const buttons = document.querySelectorAll('.filter-btn');
                    
                    buttons.forEach(b => b.classList.remove('active'));
                    if (btn) btn.classList.add('active');

                    items.forEach(item => {{
                        if (attr === 'all') {{
                            item.style.display = 'block';
                        }} else if (attr === 'crit') {{
                            item.style.display = (item.getAttribute('data-crit') === val) ? 'block' : 'none';
                        }} else if (attr === 'type') {{
                            item.style.display = (item.getAttribute('data-type') === val) ? 'block' : 'none';
                        }}
                    }});
                }}
            </script>
        </body>
        </html>
        """

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"✅ Checklist générée : {output_file}")

    def generate_dashboard_stats(self, df_base, df_news):
        """
        MLE Tip: Cette fonction transforme les données brutes en 'Insights'.
        C'est ici qu'on calcule les indicateurs de performance (KPIs).
        """
        print("--- Génération des statistiques du tableau de bord ---")
        import json
        
        # 1. Calcul des Volumes
        total_base = len(df_base)
        # Applicable = Tout sauf SANS OBJET, ARCHIVÉ, ou vide
        df_app = df_base[~df_base['Conformité'].astype(str).str.lower().str.strip().isin(['sans objet', 'archivé', ''])].copy()
        applicable_count = len(df_app)
        
        # Category A: À mettre en place (NC)
        # On inclut 'NC', 'NON CONFORME', 'EN COURS D'ÉTUDE', 'À QUALIFIER', etc.
        def is_mec_status(val):
            v = str(val).upper().strip()
            return v in ['NC', 'NON CONFORME', 'EN COURS D\'ÉTUDE', 'À QUALIFIER', 'A QUALIFIER'] or 'ÉTUDE' in v or 'ETUDE' in v
            
        mask_mec = df_app['Conformité'].apply(is_mec_status)
        count_mec = len(df_app[mask_mec])
        
        # Category B: Réévaluation (C ou c mais date passée)
        def is_past_date(date_str):
            date_str = str(date_str).strip()
            if not date_str or date_str.lower() in ['', 'nan', 'none']: return True
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                try:
                    return datetime.strptime(date_str, fmt) <= datetime.now()
                except: continue
            return True

        mask_conf = df_app['Conformité'].astype(str).str.lower().str.strip().isin(['c', 'conforme'])
        mask_past = df_app['date de la prochaine évaluation'].apply(is_past_date)
        count_reeval = len(df_app[mask_conf & mask_past])
        
        # Category C: À qualifier (Conformité vide - Nouveautés)
        mask_qualif = (df_app['Conformité'].astype(str).str.strip() == "")
        count_qualif = len(df_app[mask_qualif])
        
        # 2. Répartition Thématique (Nettoyage des catégories)
        theme_col = 'Thème' if 'Thème' in df_base.columns else df_base.columns[6]
        intitule_col = 'Intitulé ' if 'Intitulé ' in df_base.columns else 'titre'
        
        df_base['Theme_Clean'] = df_base.apply(lambda row: self.clean_theme(row.get(theme_col, ""), row.get(intitule_col, "")), axis=1)
        theme_counts = df_base['Theme_Clean'].value_counts().head(12)
        labels = theme_counts.index.tolist()
        values = theme_counts.values.tolist()
        theme_counts = df_base['Theme_Clean'].value_counts().head(12)
        labels = theme_counts.index.tolist()
        values = theme_counts.values.tolist()
        
        # 3. Ratio Conformité (Vue Auditeur Unifiée)
        df_news_app = df_news[~df_news['Conformité'].astype(str).str.lower().isin(['sans objet', 'archivé', ''])].copy() if not df_news.empty else pd.DataFrame()
        
        # Conforme = 'C' ET Date non passée (uniquement dans Base car News sont par définition 'À évaluer')
        mask_c_ok = mask_conf & ~mask_past
        c_count = len(df_app[mask_c_ok])
        
        # Non Conforme = 'NC'
        mask_nc = df_app['Conformité'].astype(str).str.upper().str.strip().isin(['NC', 'NON CONFORME'])
        nc_count = len(df_app[mask_nc])
        
        # À évaluer = (Base - C - NC) + Toutes les News applicables
        eval_count = (len(df_app) - c_count - nc_count) + len(df_news_app)
        
        # Total unifié pour le camembert
        total_unified_comp = c_count + nc_count + eval_count
        
        # 4. Répartition par Criticité
        def get_crit(r):
            # Chercher 'Criticité' avec ou sans accent
            for k in ['Criticité', 'criticite', 'Crit']:
                if k in r: return str(r[k]).strip().capitalize()
            return 'Basse'

        df_base['Crit_Clean'] = df_base.apply(get_crit, axis=1)
        df_base['Crit_Clean'] = df_base['Crit_Clean'].replace('', 'Basse').fillna('Basse')
        
        crit_counts = df_base['Crit_Clean'].value_counts()
        crit_labels = ["Haute", "Moyenne", "Basse"]
        crit_values = [int(crit_counts.get(l, 0)) for l in crit_labels]

        # 5. Score de Preuves (Audit Readiness)
        # On calcule le ratio d'Items Applicables ayant 'Oui' dans 'Preuves disponibles'
        proof_col = 'Preuves disponibles'
        df_app_p = df_app.copy()
        if proof_col in df_app_p.columns:
            total_app = len(df_app_p)
            with_proof = len(df_app_p[df_app_p[proof_col].astype(str).str.lower().str.strip() == 'oui'])
            proof_score = round((with_proof / total_app * 100), 1) if total_app > 0 else 0
        else:
            proof_score = 0

        stats = {
            "last_update": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "kpis": {
                "total_tracked": total_base,
                "applicable": applicable_count,
                "actions_required": count_mec + count_reeval + count_qualif,
                "sub_mec": count_mec,
                "sub_reeval": count_reeval,
                "sub_qualif": count_qualif,
                "alerts_ia": len(df_news),
                "proof_score": f"{proof_score}%"
            },
            "themes": {
                "labels": labels,
                "values": values
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
        
        # Export en JS pour éviter les erreurs CORS en local (file://)
        js_path = os.path.join(OUTPUT_DIR, "dashboard_stats.js")
        json_path = os.path.join(OUTPUT_DIR, "dashboard_stats.json")
        
        js_content = f"var DASHBOARD_DATA = {json.dumps(stats, indent=4, ensure_ascii=False)};"
        with open(js_path, "w", encoding="utf-8") as f:
            f.write(js_content)
        
        # Backup JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=4, ensure_ascii=False)
            
        print(f"✅ Statistiques mises à jour : {stats['kpis']['actions_required']} actions.")
        print(f"   > {count_mec} Mise en place, {count_reeval} Réévaluation, {count_qualif} À qualifier.")

if __name__ == "__main__":
    cg = ChecklistGenerator()
    
    # 1. Chargement des données
    df_news = cg.get_data('Rapport_Veille_Auto')
    df_base = cg.get_data('Base_Active')

    # 2. Génération des statistiques
    cg.generate_dashboard_stats(df_base, df_news)
    
    # 3. Checklist Nouveautés
    cg.generate_html(df_news, "Fiche Contrôle - Nouveautés", OUTPUT_NOUVEAUTES, is_base_active=False)

    # 4. Checklist Base Active
    cg.generate_html(df_base, "Fiche Contrôle - Base Active", OUTPUT_BASE, is_base_active=True)