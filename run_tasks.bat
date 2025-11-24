@echo off
:: ================================================================
:: SCRIPT D'AUTOMATISATION - VEILLE REGLEMENTAIRE
:: ================================================================
:: Ce script lance séquentiellement :
:: 1. La synchronisation (Déplacement des lignes évaluées)
:: 2. La recherche de veille (Pipeline IA)
:: 3. La génération des fiches de contrôle mises à jour
:: ================================================================

cd /d "%~dp0"

echo [1/3] Activation de l'environnement virtuel...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Pas de venv detecte, utilisation du python global...
)

echo.
echo -----------------------------------------------------------
echo [2/3] Etape 1 : Synchronisation Conformite (Rapport -> Base)
echo -----------------------------------------------------------
python sync_compliance.py

echo.
echo -----------------------------------------------------------
echo [3/3] Etape 2 : Lancement de la Veille (Recherche + IA)
echo -----------------------------------------------------------
python pipeline_veille.py

echo.
echo -----------------------------------------------------------
echo [4/4] Etape 3 : Generation des Checklists
echo -----------------------------------------------------------
python generate_checklist.py

echo.
echo ===========================================================
echo  TOUTES LES TACHES SONT TERMINEES AVEC SUCCES
echo ===========================================================
:: La pause permet de lire les logs si lance manuellement. 
:: Pour une tache planifiee, vous pouvez retirer la ligne ci-dessous.
timeout /t 10
