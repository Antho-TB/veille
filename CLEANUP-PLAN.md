# 🧹 Plan de Nettoyage du Projet

## Fichiers à SUPPRIMER ❌

### 1. Scripts Temporaires de Développement
- `GIT-INIT.sh` - Utilisé une seule fois pour init Git, plus nécessaire
- `debug_search.py` - Script de debug temporaire
- `test.py` - Script de test temporaire
- `verify_format.py` - Script de vérification ponctuel
- `inspect_columns.py` - Script d'inspection ponctuel  
- `inspect_format.py` - Script d'inspection ponctuel
- `read_doc.py` - Script utilitaire temporaire

**Raison:** Ces scripts ont servi au développement initial mais ne sont plus utiles en production.

### 2. Cache Python
- `__pycache__/` - Cache Python auto-généré (déjà dans .gitignore)

**Raison:** Sera recréé automatiquement, inutile de le garder.

### 3. Environnements Virtuels (seulement local)
- `venv/` - Ancien venv (déjà dans .gitignore)
- `.venv/` - Nouveau venv (déjà dans .gitignore)

**Raison:** Ne doit jamais être commité, chaque environnement est unique.

---

## Fichiers à GARDER ✅

### Code Principal
- ✅ `pipeline_veille.py` - **LE** script principal
- ✅ `requirements.txt` - Dépendances
- ✅ `credentials.json` - Credentials Google (dans .gitignore)

### Tests
- ✅ `test_pipeline_mock.py` - Tests unitaires (utilisé par CI/CD)
- ✅ `test_sheets_connection.py` - Tests de connexion (peut être utile)

### Configuration
- ✅ `.gitignore` - Protection des fichiers sensibles
- ✅ `.github/workflows/ci-cd.yml` - Workflow CI/CD

### Documentation
- ✅ `README.md` - Doc principale
- ✅ `CI-CD-SETUP.md` - Guide CI/CD
- ✅ `GITHUB-SECRETS.md` - Liste des secrets
- ✅ `VERIFICATION-CICD.md` - Rapport de vérification (à commiter)

---

## Actions Recommandées

### Étape 1: Supprimer les fichiers temporaires
```bash
rm GIT-INIT.sh debug_search.py test.py verify_format.py inspect_columns.py inspect_format.py read_doc.py
```

### Étape 2: Nettoyer le cache
```bash
rm -rf __pycache__
```

### Étape 3: Ajouter le nouveau fichier de vérification
```bash
git add VERIFICATION-CICD.md
git commit -m "docs: Ajout rapport de vérification CI/CD"
```

### Étape 4: Commit du nettoyage
```bash
git add .
git commit -m "chore: Nettoyage fichiers de développement temporaires"
git push origin main
```

---

## Structure Finale (Clean)

```
veille/
├── .github/
│   └── workflows/
│       └── ci-cd.yml          ✅ Workflow CI/CD
├── .venv/                     🚫 (gitignored)
├── __pycache__/               🚫 (sera supprimé + gitignored)
├── credentials.json           🚫 (gitignored)
├── .gitignore                 ✅ Configuration Git
├── CI-CD-SETUP.md            ✅ Documentation
├── GITHUB-SECRETS.md         ✅ Documentation
├── README.md                  ✅ Documentation
├── VERIFICATION-CICD.md      ✅ Documentation
├── pipeline_veille.py         ✅ Code principal
├── requirements.txt           ✅ Dépendances
├── test_pipeline_mock.py      ✅ Tests
└── test_sheets_connection.py  ✅ Tests
```

**Total après nettoyage:** 12 fichiers essentiels (vs 17 actuellement)

---

## Pourquoi garder test_sheets_connection.py ?

Vous pouvez le supprimer aussi si vous voulez, mais il peut être utile pour :
- Vérifier la connexion Google Sheets en cas de problème
- Tester les permissions du service account
- Debug futur

**Décision:** À vous de choisir !
