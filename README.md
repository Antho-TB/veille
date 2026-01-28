# 🛡️ Veille Réglementaire Automatisée (GDD)

Système intelligent de veille réglementaire HSE pour GDD (Découpage/Emboutissage), propulsé par l'IA Google Gemini.

## 🎯 Résumé du Projet

**Objectif** : Automatiser la veille réglementaire HSE pour GDD et simplifier le suivi de conformité sur le terrain.

### Les 3 Piliers de la Solution

1.  **Le Cerveau (IA)** 🧠
    *   **Script** : `pipeline_veille.py`
    *   **Rôle** : Scanne le web pour trouver les nouveaux textes (Lois, Arrêtés...) spécifiques à votre activité (ICPE, Métaux...). Il filtre le bruit et remplit automatiquement le Google Sheet (`Rapport_Veille_Auto`).

2.  **Le Terrain (Contrôle)** 📋
    *   **Script** : `generate_checklist.py`
    *   **Rôle** : Transforme votre tableau Excel complexe en **Fiches de Contrôle Mobiles** (HTML) simples et claires.
    *   **Résultat** : Deux fiches distinctes, une pour les **Nouveautés** (à qualifier) et une pour la **Base Active** (contrôle périodique).

3.  **Le Flux (Automatisation)** 🔄
    *   **Script** : `sync_compliance.py`
    *   **Rôle** : Fait le lien entre les deux. Dès qu'un point est évalué (date saisie), il le déplace automatiquement dans la base officielle.

---

## 📁 Structure du Projet

```
veille/
├── .github/workflows/ci-cd.yml    # CI/CD GitHub Actions
├── .gitignore                     # Fichiers ignorés par Git
├── README.md                      # Documentation complète (Ce fichier)
├── credentials.json               # Secrets (gitignored)
├── pipeline_veille.py             # 🧠 Script principal (IA + Recherche)
├── generate_checklist.py          # 📋 Générateur de fiches de contrôle
├── sync_compliance.py             # 🔄 Synchronisation Rapport -> Base
├── run_tasks.bat                  #  Script d'automatisation (Windows)
├── requirements.txt               # Dépendances Python
├── check_report.py                # Outil de diagnostic
├── summarize_titles.py            # Outil de nettoyage des titres
├── test_pipeline_mock.py          # Tests unitaires
└── test_sheets_connection.py      # Tests connexion Google
```

### Rôles des Fichiers Clés
*   **`pipeline_veille.py`** : Le cœur du système. Cherche, analyse et qualifie les textes.
*   **`generate_checklist.py`** : Génère les fichiers HTML `checklist_*.html` pour l'équipe qualité.
*   **`sync_compliance.py`** : Automatise le déplacement des lignes traitées du Rapport vers la Base Active.
*   **`run_tasks.bat`** : Lance tout le flux en un clic (Sync -> Veille -> Checklist).

---
##  Utilisation

### ➤ Mode Automatique (Recommandé)
Double-cliquez sur **`run_tasks.bat`**.
Cela va lancer séquentiellement :
1.  🔄 **Sync** : Archivage des points évalués.
2.  🧠 **Veille** : Recherche des nouveautés.
3.  📋 **Checklist** : Mise à jour des fiches de contrôle.

### ➤ Mode Manuel

#### 1. Lancer la veille
```bash
python pipeline_veille.py
```
*Alimente l'onglet `Rapport_Veille_Auto` avec les nouveautés.*

#### 2. Générer les fiches de contrôle
```bash
python generate_checklist.py
```
*Crée deux fichiers HTML dans le dossier :*
*   `checklist_nouveautes_DATE.html` (Pour traiter les alertes)
*   `checklist_base_active_DATE.html` (Pour le contrôle périodique)

#### 3. Synchroniser la conformité
```bash
python sync_compliance.py
```
*Déplace les lignes ayant une "Date de dernière évaluation" vers l'onglet `Base_Active`.*

---

## 📦 Installation

1.  **Prérequis** : Python 3.10+ installé.
2.  **Installation des dépendances** :
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configuration** :
    *   Placer le fichier `credentials.json` (Compte de service Google) à la racine.
    *   Vérifier les clés API dans `pipeline_veille.py` (Config).

## 📂 Structure Google Sheets

*   **`Rapport_Veille_Auto`** : Zone tampon des nouveautés détectées par l'IA. C'est ici qu'on qualifie l'impact initial.
*   **`Base_Active`** : Registre officiel de conformité. Contient tous les textes applicables et leur historique.
*   **`Config_IA`** : (Optionnel) Liste de mots-clés personnalisés pour guider l'IA.

## 🤖 Architecture Technique

*   **Moteur de Recherche** : Google Custom Search API.
*   **Analyse Sémantique** : Google Gemini 2.5 Flash.
*   **Base de Données** : Google Sheets (via `gspread`).
*   **Vector Store** : ChromaDB (pour éviter les doublons et la recherche sémantique future).

---

## ⚙️ Fonctionnement du Processus (Step-by-Step)

Le système suit un flux automatisé précis pour garantir la pertinence des informations :

1.  **Chargement de l'Identité (Contexte Dynamique)** : Le script lit d'abord une fiche d'identité (Google Doc) décrivant GDD (rubriques ICPE 2560/2564, types de métaux, enjeux ISO 14001).
2.  **Génération des Requêtes IA** : Gemini utilise ce contexte pour créer des mots-clés de recherche ultra-précis (ex: "arrêté ministériel métaux", "loi AGEC industrie").
3.  **Scan & Déduplication** : Le système scanne le web (Légifrance, JOUE, sites spécialisés) et élimine les textes déjà présents dans la base.
4.  **Analyse Sémantique par l'IA** : Pour chaque nouveau texte, l'IA vérifie l'impact réel sur GDD et génère :
    *   Un résumé simplifié.
    *   Une proposition d'action concrète.
    *   Un niveau de criticité.
5.  **Alimentation du Rapport** : Les textes validés sont ajoutés dans le Google Sheet `Rapport_Veille_Auto`.
6.  **Génération des Livrables** : Le système génère le `dashboard.html` et les `checklists` mobiles pour l'équipe Qualité.
7.  **Synchronisation de Conformité** : Une fois évalués sur le terrain, les points sont transférés automatiquement vers la `Base_Active`.

---

## 🚀 Synthèse pour l'Équipe Métier

### 🎯 Vision
Passer d'une veille réglementaire subie et manuelle à un **système proactif et automatisé**, garantissant la conformité environnementale (ISO 14001) avec un minimum d'effort humain.

### 🏗️ Les 3 Piliers Technologiques
1.  **Le Cerveau (IA Gemini)** 🧠 : Scanne, lit et qualifie les textes officiels selon le contexte GDD (ICPE 2560/2564).
2.  **Le Terrain (Checklists Mobiles)** 📋 : Interfaces web légères pour valider la conformité directement en atelier sur tablette.
3.  **Le Flux (Synchronisation)** 🔄 : Automatisation complète de la détection à l'archivage en base active.

### 📈 État d'Avancement
*   ✅ **Connecteurs en place** (Google Sheets + Google Search + Gemini).
*   ✅ **Base Active initialisée** (+1 300 textes suivis).
*   ✅ **Dernière exécution réussie** le 28/01/2026.

> [!TIP]
> **Argument de Choc** : Ce système divise par 4 le temps passé sur la lecture des textes, pour se concentrer à 100% sur les actions de mise en conformité.
