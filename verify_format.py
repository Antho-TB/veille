from pipeline_veille import DataManager, Config
import pandas as pd

print(">>> VERIFICATION FORMATAGE <<<")

# Create dummy data
data = [{
    "titre": "Test Article Formatage",
    "url": "http://example.com",
    "type": "TEST",
    "resume": "Ceci est un test de formatage.",
    "action": "Vérifier couleur jaune"
}]
df = pd.DataFrame(data)

# Initialize DataManager
dm = DataManager()

# Call save_report
print("Appel de save_report avec données de test...")
dm.save_report(df)

print(">>> FIN VERIFICATION <<<")
