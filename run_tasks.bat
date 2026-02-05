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

echo [1/6] Activation de l'environnement virtuel...
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Pas de venv detecte, utilisation du python global...
)

echo.
echo -----------------------------------------------------------
echo [2/6] Démarrage du Serveur de Synchronisation (Interactif)
echo -----------------------------------------------------------
start "GDD Sync Server" /MIN python src/utils/sync_server.py
timeout /t 3 > nul

echo.
echo -----------------------------------------------------------
echo [3/6] Etape 1 : Nettoyage des donnees (Purge non-officielles)
echo -----------------------------------------------------------
python src/utils/sanitize_sheets.py

echo.
echo -----------------------------------------------------------
echo [4/6] Etape 2 : Synchronisation Conformite (Rapport -> Base)
echo -----------------------------------------------------------
python src/utils/sync_compliance.py

echo.
echo -----------------------------------------------------------
echo [5/6] Etape 3 : Lancement de la Veille (Recherche + IA)
echo -----------------------------------------------------------
python src/core/pipeline.py

echo.
echo -----------------------------------------------------------
echo [6/6] Etape 4 : Generation des Checklists ^& Stats Dashboard
echo -----------------------------------------------------------
python src/core/checklists.py

echo.
echo ===========================================================
echo  TOUTES LES TACHES SONT TERMINEES AVEC SUCCES
echo ===========================================================
:: La pause permet de lire les logs si lance manuellement. 
:: Pour une tache planifiee, vous pouvez retirer la ligne ci-dessous.
timeout /t 10
