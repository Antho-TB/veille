#!/bin/bash
# Script de renommage des commits en français pour Git Bash

# Fonction de traduction simplifiée
translate_msg() {
    local msg="$1"
    
    # Remplacements de préfixes
    msg="${msg//fix:/Correction :}"
    msg="${msg//feat:/Fonctionnalité :}"
    msg="${msg//chore:/Maintenance :}"
    msg="${msg//docs:/Documentation :}"
    msg="${msg//merge:/Fusion :}"
    msg="${msg//refactor:/Refactorisation :}"
    
    # Remplacements spécifiques
    case "$msg" in
        "Initial commit") echo "Premier commit" ;;
        *"Optimization complete"*) echo "Optimisation terminée : Données nettoyées et dashboard affiné" ;;
        *"Pre-optimization backup"*) echo "Sauvegarde avant optimisation : Audit terminé" ;;
        *"restore working Search API key"*) echo "Restauration de la clé API Search et support Tavily" ;;
        *"add step-by-step process"*) echo "Ajout de la méthodologie et nettoyage projet" ;;
        *"project cleanup"*) echo "Nettoyage du projet et restauration des fichiers sources" ;;
        *"Correct test_data_manager"*) echo "Correction des données de test pour DataManager" ;;
        *"Add verified dashboard"*) echo "Ajout du tableau de bord avec KPIs réels" ;;
        *"Pipeline de veille réglementaire avec CI/CD"*) echo "Pipeline de veille réglementaire avec intégration continue" ;;
        *"Final Enhancements"*) echo "Améliorations finales : Dashboard interactif et conformité audit" ;;
        *"Critical Fix: Surgical repair"*) echo "Correction Critique : Réparation chirurgicale des décalages" ;;
        *) echo "$msg" ;;
    esac
}

# On lit le message de stdin et on le traduit
read -r original_msg
translate_msg "$original_msg"
