
import os
import pandas as pd
from src.core.checklists import ChecklistGenerator

def check_proofs():
    cg = ChecklistGenerator()
    for sheet_name in ['Rapport_Veille_Auto', 'Base_Active']:
        df = cg.get_data(sheet_name)
        print(f"\n--- Analysis for {sheet_name} ---")
        print(f"Columns: {df.columns.tolist()[:10]}... (Total: {len(df.columns)})")
        
        col_name = 'Preuve de Conformité Attendue'
        if col_name in df.columns:
            df[col_name] = df[col_name].astype(str)
            valid_proofs = df[df[col_name].str.strip() != ""]
            print(f"Found {len(valid_proofs)} rows with proofs out of {len(df)}.")
            if not valid_proofs.empty:
                print("Sample proofs:")
                for p in valid_proofs[col_name].head(3).tolist():
                    print(f" - {p}")
        else:
            print(f"Column '{col_name}' NOT FOUND in sheet!")

if __name__ == "__main__":
    check_proofs()
