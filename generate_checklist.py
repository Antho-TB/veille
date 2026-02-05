# ---------------------------------------------------------------------------
# Générateur de Fiches de Contrôle - Veille Réglementaire
# ---------------------------------------------------------------------------
# Ce script génère des fiches de contrôle HTML imprimables/mobiles
# à partir des données du Google Sheet (Rapport et Base Active).
# ---------------------------------------------------------------------------

import os
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from pipeline_veille import Config

# --- CONFIGURATION ---
OUTPUT_NOUVEAUTES = "checklist_nouveautes.html"
OUTPUT_BASE = "checklist_base_active.html"

class ChecklistGenerator:
    def __init__(self):
        self.client = None
    
    def connect(self):
        if not os.path.exists(Config.CREDENTIALS_FILE):
            raise FileNotFoundError("Manque credentials.json")
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        self.client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope))

    def get_data(self, worksheet_name):
        print(f"--- Chargement des données : {worksheet_name} ---")
        if not self.client: self.connect()
        sheet = self.client.open_by_key(Config.SHEET_ID)
        
        try:
            ws = sheet.worksheet(worksheet_name)
            records = ws.get_all_records()
            df = pd.DataFrame(records)
            
            # Normalisation des colonnes (suppression des espaces)
            df.columns = [c.strip() for c in df.columns]
            return df
        except Exception as e:
            print(f"Erreur lors de la lecture de l'onglet {worksheet_name} : {e}")
            return pd.DataFrame()

    def generate_html(self, df, title, output_file, is_base_active=False):
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
                .item {{ 
                    background: white;
                    border: 1px solid #dee2e6;
                    border-radius: 8px;
                    padding: 22px; 
                    margin-bottom: 18px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                    transition: all 0.25s ease;
                    position: relative;
                }}
                
                .item::before {{
                    content: '';
                    position: absolute;
                    top: 0; left: 0; width: 3px; height: 100%;
                    background: #d64545;
                    transform: scaleY(0);
                    transition: transform 0.25s;
                }}
                
                .item:hover {{ 
                    border-color: #adb5bd;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                    transform: translateY(-2px);
                }}
                
                .item:hover::before {{ transform: scaleY(1); }}
                
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
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="header-logos">
                        <img src="logo_gdd.png" alt="GDD Logo">
                        <img src="logo_tb.png" alt="TB Groupe Logo">
                    </div>
                    <h1>Fiche de Contrôle - {title.replace('Fiche Contrôle - ', '')}</h1>
                    <div class="header-info">
                        Généré le {dt.now().strftime('%d/%m/%Y à %H:%M')}<br>
                        Pour l'équipe Qualité de TB Groupe
                    </div>
                </div>
        """
        
        # Intro Textes Personnalisés
        if is_base_active:
            intro_text = """
                <div class="intro">
                    <strong>📋 Checklist Base Active</strong>
                    <p>Cette fiche présente les textes réglementaires nécessitant une réévaluation (date dépassée ou non planifiée). Vérifiez la conformité de chaque point et notez vos observations.</p>
                    <p class="auto-info">ℹ️ Automatisation : Cette fiche est générée quotidiennement à 8h00. Les items proviennent des nouveautés évaluées (transférées automatiquement depuis le Rapport de Veille).</p>
                    <p class="warning-text">📝 Important : Les modifications effectuées ici doivent être reportées manuellement dans le Google Sheet pour mise à jour de la base.</p>
                </div>
            """
        else:
            intro_text = """
                <div class="intro">
                    <strong>🆕 Checklist Nouveautés</strong>
                    <p>Cette fiche présente les nouveaux textes détectés par l'IA qui nécessitent une évaluation initiale. Qualifiez l'impact pour GDD et déterminez les actions à mettre en place.</p>
                    <p class="auto-info">ℹ️ Automatisation : L'IA scanne le web quotidiennement à 8h00 et filtre les textes pertinents pour GDD (ICPE, Métaux, HSE). Une fois évalués (date saisie dans le Google Sheet), les items sont automatiquement transférés vers la Base Active.</p>
                    <p class="warning-text">📝 Important : Les modifications effectuées ici doivent être reportées manuellement dans le Google Sheet pour mise à jour de la base.</p>
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
                url = row.get('Lien Internet', '#')
                action = row.get('Commentaires', '')
                if not action: action = "Aucune action spécifiée."
                
                date_eval = row.get('date de la dernère évaluation', 'Jamais')
                type_texte = row.get('Type de texte', 'N/A')
                date_texte = row.get('Date', 'N/A')
                
                # Item
                html_content += f"""
                <div class="item">
                    <div class="item-header">
                        <div class="item-title">
                            <a href="{url}" target="_blank">{titre}</a>
                        </div>
                        <span class="row-badge">Ligne {sheet_row}</span>
                    </div>
                    <div class="item-meta">
                        <span class="tag">📅 Texte: {date_texte}</span>
                        <span class="tag">📄 Type: {type_texte}</span>
                        <span class="tag">🔍 Dern. Éval: {date_eval}</span>
                    </div>
                    
                    <div class="item-action">
                        <strong>👉 Action / Résumé :</strong>
                        {action}
                    </div>

                    <div class="status-bar">
                        <label class="status-option">
                            <input type="radio" name="status_{sheet_row}" value="conforme"> ✅ Conforme
                        </label>
                        <label class="status-option">
                            <input type="radio" name="status_{sheet_row}" value="non_conforme"> ❌ Non Conforme
                        </label>
                        <label class="status-option">
                            <input type="radio" name="status_{sheet_row}" value="info"> ℹ️ Pour Info
                        </label>
                        <label class="status-option">
                            <input type="radio" name="status_{sheet_row}" value="supprimer"> 🗑️ Supprimer
                        </label>
                    </div>

                    <div class="obs-section">
                        <label class="obs-label">Observations :</label>
                        <textarea placeholder="Saisir vos remarques ici..."></textarea>
                    </div>

                </div> """
            
            # Fermeture Theme
            html_content += "</div>"

        # Fin du contenu et Ajout du Footer UNIQUE
        html_content += """
            </div> <div class="footer">
                Généré par l'Assistant Veille Réglementaire GDD, Anthony, Service Data&IA
            </div>
            
            </div> </body>
        </html>
        """

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"✅ Checklist générée : {output_file}")

    def generate_dashboard_stats(self, df_base, df_news):
        print("--- Génération des statistiques du tableau de bord ---")
        import json
        
        # 1. KPIs
        total_base = len(df_base)
        
        # Textes applicables (Conformité != Sans objet/Archivé)
        mask_applicable = ~df_base['Conformité'].astype(str).str.lower().isin(['sans objet', 'archivé', ''])
        df_applicable = df_base[mask_applicable]
        applicable_count = len(df_applicable)
        
        # Actions requises : Textes APPLICABLES qui doivent être réévalués
        def needs_evaluation(date_str):
            date_str = str(date_str).strip()
            if not date_str or date_str.lower() in ['', 'nan', 'none']: return True
            for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                try:
                    eval_date = datetime.strptime(date_str, fmt)
                    # On considère comme "Action Requise" si la date est passée ou aujourd'hui
                    return eval_date.date() <= datetime.now().date()
                except: continue
            return True
            
        actions_required = len(df_applicable[df_applicable['date de la prochaine évaluation'].apply(needs_evaluation)])
        
        # 2. Répartition Thématique
        theme_counts = df_base['Thème'].value_counts()
        labels = theme_counts.index.tolist()
        values = theme_counts.values.tolist()
        
        stats = {
            "last_update": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "kpis": {
                "total_tracked": total_base,
                "applicable": applicable_count,
                "actions_required": actions_required,
                "new_alerts": len(df_news)
            },
            "themes": {
                "labels": labels,
                "values": values
            }
        }
        
        with open("dashboard_stats.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=4, ensure_ascii=False)
        print("✅ dashboard_stats.json généré.")

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