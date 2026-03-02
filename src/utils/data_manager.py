"""
=============================================================================
GESTIONNAIRE DE DONNÉES GOOGLE SHEETS - VEILLE GDD
=============================================================================

Ce module s'occupe de tout ce qui touche à la lecture et l'écriture dans 
les Google Sheets. 
"DataManager" est comme un bibliothécaire qui sait exactement où ranger 
les nouveaux livres et où retrouver les anciens.

"""

import os
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from src.core.config_manager import Config

class DataManager:
    """
    Classe responsable de faire le lien entre le code Python et le fichier Google Sheets.
    """
    def __init__(self):
        # Le client représente notre connexion vers Google Sheets
        self.client = None
    
    def _connect(self):
        """ Établit la connexion sécurisée à Google Sheets """
        if not os.path.exists(Config.CREDENTIALS_FILE): 
            raise FileNotFoundError(f"Le fichier de clés {Config.CREDENTIALS_FILE} est manquant.")
        
        # Junior Tip : Les 'scopes' expliquent à Google ce qu'on a le droit de faire (lire/écrire)
        scope = [
            "https://spreadsheets.google.com/feeds", 
            "https://www.googleapis.com/auth/drive"
        ]
        
        # On utilise le fichier credentials.json téléchargé depuis la Google Cloud Console
        self.client = gspread.authorize(
            ServiceAccountCredentials.from_json_keyfile_name(Config.CREDENTIALS_FILE, scope)
        )

    def load_data(self):
        """ Charge les données des différents onglets pour éviter de chercher des doublons """
        print("--- [DataManager] Chargement multi-feuilles ---")
        try:
            if not self.client: self._connect()
            sheet = self.client.open_by_key(Config.SHEET_ID)
            
            all_dfs = []
            # On scanne les 3 onglets principaux
            for ws_name in ['Base_Active', 'Rapport_Veille_Auto', 'Informative']:
                try:
                    ws = sheet.worksheet(ws_name)
                    data = ws.get_all_records()
                    if data:
                        temp_df = pd.DataFrame(data)
                        # Junior Tip : .strip() enlève les espaces cachés dans les noms de colonnes
                        temp_df.columns = [c.strip() for c in temp_df.columns]
                        all_dfs.append(temp_df)
                except Exception as e:
                    print(f"      [Info] Onglet '{ws_name}' ignoré ou vide : {e}")
                    continue
            
            if not all_dfs:
                return pd.DataFrame(), pd.DataFrame()
                
            # On fusionne tout en un seul grand tableau (DataFrame)
            df = pd.concat(all_dfs, ignore_index=True)
            
            # Mapping pour harmoniser les noms de colonnes (parfois il y a des fautes de frappe ou des espaces)
            mapping = {
                "Intitulé": "titre", "Intitulé ": "titre",
                "Lien Internet": "url", "Lien internet": "url", "Lien": "url", "URL": "url"
            }
            df = df.rename(columns=mapping)
            
            # On s'assure d'avoir les colonnes essentielles
            for col in ['titre', 'url']:
                if col not in df.columns: df[col] = ""
            
            print(f"      > {len(df)} textes historiques chargés.")

            # On charge aussi les mots-clés configurés par l'utilisateur
            try: 
                df_conf = pd.DataFrame(sheet.worksheet('Config_IA').get_all_records())
            except: 
                print("      [!] Onglet 'Config_IA' absent, utilisation de mots-clés par défaut.")
                df_conf = pd.DataFrame({'keywords': ['Arrêté type 2560', 'ICPE 2564']})

            return df, df_conf
        except Exception as e:
            print(f"❌ ERREUR CHARGEMENT GOOGLE SHEETS : {e}")
            return pd.DataFrame(), pd.DataFrame()

    def save_report(self, df_report):
        """ Enregistre les nouvelles alertes trouvées dans les Google Sheets """
        print("--- [DataManager] Sauvegarde des résultats ---")
        if df_report.empty: 
            print("      > Aucune donnée à sauvegarder.")
            return
        
        # Liste officielle des colonnes attendues dans le fichier Excel/Sheets de l'usine GDD
        cols = [
            'Mois', 'Sources', 'Type de texte', 'N°', 'Date', 'Intitulé ', 'Thème', 
            'Grand thème', 'Commentaires (ALSAPE, APORA…)', 'Lien Internet', 'Statut', 'Conformité', 
            "Délai d'application", 'Commentaires', 'date de la dernère évaluation', 
            'date de la prochaine évaluation', "Evaluation pour le site Pommier (date d'évaluation)",
            'Criticité', 'Preuve de Conformité Attendue', 'Plan Action', 
            'Responsable', 'Échéance'
        ]
        
        # Enrichissement automatique des données avant l'envoi
        df_report['Mois'] = datetime.now().strftime("%B %Y")
        df_report['Sources'] = "Veille Auto"
        df_report['Intitulé '] = df_report.get('titre', '')
        df_report['Lien Internet'] = df_report.get('url', '')
        df_report['Type de texte'] = df_report.get('type_texte', 'Autre')
        df_report['Date'] = df_report.get('date', '')
        df_report['Preuve de Conformité Attendue'] = df_report.get('preuve_attendue', '')
        
        # Fusion du résumé et de l'action pour la colonne commentaire
        df_report['Commentaires'] = df_report.apply(
            lambda x: f"{x.get('resume', '')} (Action: {x.get('action', '')})", axis=1
        )
        
        df_report['Statut'] = "A traiter"
        
        # On remplit les colonnes manquantes par du vide
        for c in cols: 
            if c not in df_report.columns: df_report[c] = ""
        
        # On sépare les textes 'Critiques' des textes purement 'Informatifs'
        mask_info = (df_report['criticite'].isin(['Non', 'Informatif']))
        df_alerts = df_report[~mask_info]
        df_info = df_report[mask_info]

        try:
            if not self.client: self._connect()
            sheet = self.client.open_by_key(Config.SHEET_ID)
            
            def safe_append(ws_name, data_df):
                if data_df.empty: return
                try: 
                    ws = sheet.worksheet(ws_name)
                except: 
                    ws = sheet.add_worksheet(ws_name, 1000, 25)
                    ws.append_row(cols)
                
                rows = data_df[cols].fillna("").astype(str).values.tolist()
                # On ajoute les lignes à la suite !
                ws.append_rows(rows, value_input_option='USER_ENTERED')
                print(f"      [OK] {len(rows)} lignes ajoutées dans '{ws_name}'.")

            safe_append('Rapport_Veille_Auto', df_alerts)
            safe_append('Informative', df_info)
            
        except Exception as e: 
            print(f"   > Erreur lors de la sauvegarde : {e}")
