import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import time

# Configuration
SHEET_ID = "1JFB6gjfNAptugLRSxlCmTGPbsPwtG4g_NxmutpFDUzg"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "../config/credentials.json")

def heal_rapport():
    print("--- [HEAL] Réparation chirurgicale de Rapport_Veille_Auto ---")
    
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        ss = client.open_by_key(SHEET_ID)
        ws = ss.worksheet("Rapport_Veille_Auto")
        
        # On récupère TOUT pour traiter en mémoire
        rows = ws.get_all_values()
        if not rows: return
        
        header = rows[0]
        new_rows = [header]
        
        modified_count = 0
        
        # Indices (0-based)
        # K=10 (Statut), L=11 (Conformité), M=12 (Délai), N=13 (Commentaires)
        
        for i in range(1, len(rows)):
            row = list(rows[i])
            idx = i + 1
            
            # 1. Correction du décalage Horizontal "A traiter"
            # Si K="A traiter" et L est un statut IA, on décale à gauche à partir de L
            if len(row) > 11 and row[10] == "A traiter" and row[11] in ["Mise en place", "Réévaluation"]:
                print(f"   > Ligne {idx}: Correction décalage Horizontal (A traiter push)")
                row[10] = row[11] # Statut correct
                row[11] = ""      # Clear Conformité
                # Si M est vide et N a du texte, on ramène N dans M
                if len(row) > 13 and row[12] == "" and row[13] != "":
                    row[12] = row[13]
                    row[13] = ""
                modified_count += 1

            # 2. Correction du décalage Vertical des Commentaires
            # Si on n'est pas à la dernière ligne
            if i < len(rows) - 1:
                next_row = rows[i+1]
                # Si mon N (13) ressemble au M (12) du suivant
                curr_n = row[13] if len(row) > 13 else ""
                next_m = next_row[12] if len(next_row) > 12 else ""
                
                if curr_n != "" and next_m == "" and len(curr_n) > 50:
                    # Cas spécifique : Mon N est le commentaire du suivant qui est vide en M
                    print(f"   > Ligne {idx}: Correction décalage Vertical (Commentaire déplacé vers {idx+1})")
                    # On déplace curr_n vers next_row[12]
                    # On ne peut pas modifier rows[i+1] directement car on l'utilisera au prochain tour
                    # On va modifier next_row in-place
                    while len(next_row) <= 12: next_row.append("")
                    next_row[12] = curr_n
                    row[13] = ""
                    modified_count += 1
                elif curr_n != "" and next_m != "" and (curr_n[:50] == next_m[:50]):
                    # Cas : Doublon (Mon N est le début du suivant)
                    print(f"   > Ligne {idx}: Suppression doublon vertical (Commentaire suivant présent en N)")
                    row[13] = ""
                    modified_count += 1

            new_rows.append(row)

        if modified_count > 0:
            print(f"\n--- [UPLOAD] Envoi de {modified_count} corrections ---")
            # Clear et Update (Plus sûr pour les décalages)
            ws.clear()
            # On découpe par blocs de 100 pour éviter les timeouts API
            batch_size = 100
            for i in range(0, len(new_rows), batch_size):
                batch = new_rows[i:i+batch_size]
                ws.append_rows(batch, value_input_option='USER_ENTERED')
                print(f"      - Bloc {i//batch_size + 1} envoyé...")
                time.sleep(1)
            print("   ✅ Réparation terminée avec succès.")
        else:
            print("   ✅ Aucun décalage détecté.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"   ❌ Erreur : {e}")

if __name__ == "__main__":
    heal_rapport()
