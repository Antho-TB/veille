# 📁 Structure du Projet - Version Minimaliste

## ✨ Structure Actuelle (7 fichiers)

```
veille/
├── .github/workflows/ci-cd.yml    # CI/CD GitHub Actions
├── .gitignore                     # Fichiers ignorés par Git
├── README.md                      # Documentation complète
├── credentials.json               # Secrets (gitignored)
├── pipeline_veille.py             # Script principal
├── requirements.txt               # Dépendances Python
├── test_pipeline_mock.py          # Tests unitaires
└── test_sheets_connection.py      # Tests connexion Google
```

## 🎯 Philosophie

**Minimaliste et efficace** - Seulement l'essentiel :
- ✅ 1 script principal (`pipeline_veille.py`)
- ✅ 2 fichiers de tests (pour CI/CD)
- ✅ 1 documentation (`README.md` contient tout)
- ✅ Configuration minimale (`.gitignore`, `requirements.txt`)

## 📚 Documentation

Toute la documentation est centralisée dans **`README.md`** :
- Installation
- Configuration
- Utilisation
- CI/CD (GitHub Actions)
- Dépannage (quota API, etc.)

## 🚀 Démarrage Rapide

```bash
# Installation
pip install -r requirements.txt

# Configuration
# Éditer pipeline_veille.py lignes 28-38 (API keys)
# Ajouter credentials.json

# Exécution
python pipeline_veille.py

# Tests
pytest test_pipeline_mock.py
```

## 🔐 Fichiers Protégés (.gitignore)

Ces fichiers restent locaux uniquement :
- `credentials.json`
- `.venv/`, `venv/`
- `__pycache__/`
- `*.log`

## 📊 Statistiques

- **Fichiers totaux** : 7
- **Lignes de code** : ~13 000 (pipeline)
- **Lignes de tests** : ~4 000
- **Documentation** : Tout dans README.md

---

**Dernière mise à jour** : 2025-11-20  
**Commit** : `ba5f783`  
**Taille totale** : ~30 KB (hors dépendances)
