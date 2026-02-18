import sys
import re

def translate(msg):
    # Mapping des préfixes
    msg = msg.replace('fix:', 'Correction :')
    msg = msg.replace('feat:', 'Fonctionnalité :')
    msg = msg.replace('chore:', 'Maintenance :')
    msg = msg.replace('docs:', 'Documentation :')
    msg = msg.replace('merge:', 'Fusion :')
    msg = msg.replace('refactor:', 'Refactorisation :')
    
    # Mapping des messages spécifiques fréquents
    replacements = {
        "Initial commit": "Premier commit",
        "Optimization complete: Sanitized data, refined AI prompt, and dynamic dashboard.": "Optimisation terminée : Données nettoyées, prompt IA affiné et dashboard dynamique.",
        "Pre-optimization backup: Audit complete, environment fixed.": "Sauvegarde avant optimisation : Audit terminé, environnement corrigé.",
        "restore working Search API key and add Tavily support": "Restauration de la clé API Search et ajout du support Tavily",
        "add step-by-step process, vision and cleanup project": "Ajout du processus étape par étape, vision et nettoyage du projet",
        "project cleanup - restore core files and remove redundant reports": "Nettoyage du projet - restauration des fichiers sources et suppression des rapports redondants",
        "Correct test_data_manager_load_data mock data structure": "Correction de la structure des données simulées pour test_data_manager_load_data",
        "Add verified dashboard with real KPIs and integrated checklists": "Ajout du tableau de bord vérifié avec KPIs réels et checklists intégrées",
        "Pipeline de veille réglementaire avec CI/CD": "Pipeline de veille réglementaire avec intégration continue (CI/CD)",
        "Final Enhancements: Interactive Dashboard, Multi-criteria Search, Professional Formatting, and Audit Readiness": "Améliorations finales : Dashboard interactif, recherche multi-critères, formatage professionnel et préparation à l'audit",
        "Critical Fix: Surgical repair of Rapport_Veille_Auto column/row shifts": "Correction Critique : Réparation chirurgicale des décalages de colonnes/lignes dans le Rapport_Veille_Auto"
    }
    
    for en, fr in replacements.items():
        if en.lower() in msg.lower():
            # On essaie de garder la casse du début si possible, mais ici on remplace tout le bloc
            return fr
            
    return msg

if __name__ == "__main__":
    original_msg = sys.stdin.read().strip()
    print(translate(original_msg))
