# Pipeline Veille Réglementaire Automatisée GDD

Pipeline intelligent de veille réglementaire HSE pour la Société Générale de Découpage, avec analyse IA et déduplication automatique.

## 🚀 Installation Rapide

### 1. Prérequis
```bash
pip install -r requirements.txt
```

### 2. Configuration des Clés API

**Fichier `credentials.json` (Google Cloud):**
- Téléchargez depuis la console Google Cloud
- Renommez en `credentials.json`
- Placez dans le dossier du projet

**Dans `pipeline_veille.py` :**
- Ligne 52 : `GEMINI_API_KEY` - Votre clé API Gemini (IA)
- Ligne 55 : `SEARCH_API_KEY` - Votre clé API Google Custom Search
- Ligne 57 : `SHEET_ID` - ID de votre Google Sheet
- Ligne 59 : `EMAIL_SENDER` - Votre email Gmail
- Ligne 62 : `EMAIL_PASSWORD` - Mot de passe d'application Gmail

### 3. Lancement
```bash
python pipeline_veille.py
```

## ✨ Fonctionnalités

### 🔍 Recherche Intelligente
- **Période**: 2 ans de veille réglementaire (configurable via `SEARCH_PERIOD`)
- **Mots-clés dynamiques**: Générés automatiquement par IA selon le contexte GDD
- **Sources**: Google Custom Search API (moteur personnalisé)

### 🤖 Analyse IA (Gemini 2.0 Flash)
- Classification automatique (Type de texte, Thème, Criticité)
- Extraction de dates et résumés
- Recommandations d'actions (Lire, Mettre à jour, Vérifier...)

### 🛡️ Déduplication
- Vérification automatique contre la base `Base_Active`
- Évite les doublons par URL et titre
- Économise du temps de traitement

### 📊 Export Google Sheets
- Colonnes alignées sur `Base_Active`
- **Préserve le formatage manuel** (utilise `append_rows`)
- Statut automatique "A traiter"
- Mapping intelligent des données IA

### 🎯 Audit GAP (Optionnel)
- Détecte les textes réglementaires manquants
- Analysable via `RUN_FULL_AUDIT = True/False`

## 📋 Configuration Avancée

### Paramètres de Recherche (`Config` class)
```python
RUN_FULL_AUDIT = False    # True pour activer l'audit GAP
SEARCH_PERIOD = 'y2'      # m1/m6/y1/y2 (mois/années)
```

### Contexte Entreprise
Le pipeline utilise `CONTEXTE_ENTREPRISE` pour cibler les recherches :
- Rubriques ICPE (2560, 2561, 2564, 2565)
- Déchets dangereux (fluides de coupe, solvants)
- Lois spécifiques (AGEC, REP)

## ⚠️ Limitations & Solutions

### Quota API Gemini
**Erreur 429**: Quota gratuit dépassé (200 requêtes/jour)
- **Solution**: Attendre la réinitialisation (24h) ou augmenter le quota
- **Astuce**: Désactiver `RUN_FULL_AUDIT` si non nécessaire

### Pas de résultats
1. Vérifier que `SEARCH_API_KEY` est valide
2. Vérifier la connexion à Google Sheets
3. Consulter les logs pour identifier les erreurs

## 📁 Structure du Projet

```
veille/
├── pipeline_veille.py          # Script principal
├── credentials.json            # Clés Google Cloud (à créer)
├── requirements.txt            # Dépendances Python
├── test_pipeline_mock.py       # Tests unitaires
└── README.md                   # Ce fichier
```

## 🔗 Intégrations

- **Google Sheets API**: Lecture/écriture des données
- **Google Custom Search**: Recherche web ciblée
- **Gemini API**: Analyse intelligente par IA
- **ChromaDB**: Base vectorielle (optionnel, pour RAG futur)

## 📧 Support

Pour toute question, consulter la documentation interne ou contacter l'équipe QHSE.

---

**Dernière mise à jour**: Novembre 2024  
**Version**: 2.0 (Recherche 2 ans + Déduplication + Colonnes enrichies)