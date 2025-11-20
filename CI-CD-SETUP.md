# Configuration CI/CD - Guide de Démarrage

## 📋 Prérequis

1. **Compte GitHub** (ou GitLab/Azure DevOps)
2. **Secrets configurés** dans votre dépôt
3. **Permissions GitHub Actions** activées

## 🔐 Configuration des Secrets

### Dans GitHub

1. Aller dans `Settings` > `Secrets and variables` > `Actions`
2. Cliquer sur `New repository secret`
3. Ajouter les secrets suivants :

| Nom du Secret | Valeur | Description |
|---------------|--------|-------------|
| `GEMINI_API_KEY` | `AIzaSyC...` | Votre clé API Gemini |
| `SEARCH_API_KEY` | `AIzaSyA...` | Votre clé Google Custom Search |
| `GOOGLE_CREDENTIALS` | Contenu de `credentials.json` | Credentials Google Cloud (copier tout le JSON) |
| `EMAIL_SENDER` | `your-email@gmail.com` | Email pour notifications |
| `EMAIL_PASSWORD` | `xdqz ptef dnts remb` | Mot de passe d'application Gmail |

### Copier le contenu de credentials.json

```bash
# Windows PowerShell
Get-Content credentials.json | Set-Clipboard

# Ou manuellement
notepad credentials.json
# Copier tout le contenu et coller dans GitHub Secret
```

## 🚀 Initialisation Git

```bash
# 1. Initialiser le dépôt
git init

# 2. Ajouter le remote GitHub
git remote add origin https://github.com/VOTRE_USERNAME/veille-reglementaire.git

# 3. Créer la branche main
git branch -M main

# 4. Premier commit
git add .
git commit -m "Initial commit: Pipeline de veille réglementaire"

# 5. Push vers GitHub
git push -u origin main
```

## ⚙️ Fonctionnement du CI/CD

### Déclencheurs

1. **Push sur `main`** : Lance les tests uniquement
2. **Tous les jours à 8h** : Lance le pipeline complet
3. **Manuel** : Via onglet `Actions` > `Run workflow`

### Jobs

1. **Test** : 
   - Linting (flake8)
   - Formatage (black)
   - Tests unitaires (pytest)

2. **Run Pipeline** :
   - N'exécute que si les tests passent
   - Crée `credentials.json` depuis les secrets
   - Execute `pipeline_veille.py`
   - Upload des logs
   - Envoi email en cas d'échec

## 📊 Monitoring

### Consulter les exécutions

1. Aller dans l'onglet `Actions` de votre dépôt
2. Cliquer sur un workflow pour voir les logs détaillés
3. Télécharger les artifacts (logs) si nécessaire

### Activer les notifications

GitHub vous notifie automatiquement par email en cas d'échec.

## 🔧 Personnalisation

### Changer l'heure d'exécution

Dans `.github/workflows/ci-cd.yml`, modifier la ligne cron :

```yaml
schedule:
  - cron: '0 7 * * *'  # 7h UTC = 8h Paris
```

Exemples :
- `'30 6 * * *'` : 7h30 Paris
- `'0 12 * * 1-5'` : 13h Paris, du lundi au vendredi
- `'0 0 1 * *'` : 1er de chaque mois à 1h Paris

### Désactiver les tests

Commenter ou supprimer le job `test` dans le workflow.

### Ajouter Slack/Teams

Remplacer l'action `dawidd6/action-send-mail` par :
- Slack: `slackapi/slack-github-action@v1`
- Teams: `aliencube/microsoft-teams-actions@v0.8.0`

## 🐛 Dépannage

### Erreur "credentials.json not found"

Vérifier que le secret `GOOGLE_CREDENTIALS` est bien configuré.

### Quota API dépassé

Le workflow s'arrête proprement. Relancer manuellement le lendemain.

### Tests échouent localement mais pas dans CI

Vérifier les versions Python :
```bash
python --version  # Doit être 3.10+
```

## 📦 Déploiement Alternatif (Local Windows)

Si vous préférez exécuter localement plutôt que GitHub Actions :

### Tâche Planifiée Windows

```powershell
# Créer le script bat
@echo off
cd C:\Users\abezille\dev\veille
call venv\Scripts\activate
python pipeline_veille.py
deactivate
```

Puis créer une tâche dans le Planificateur de tâches Windows.

## 🌐 Déploiement Cloud (Optionnel)

### Google Cloud Run (Recommandé pour Google Sheets)

```bash
# 1. Créer Dockerfile
# 2. Build et push
# 3. Déployer sur Cloud Run avec Cloud Scheduler
```

### Azure Functions

```bash
# 1. Créer Azure Function (Timer trigger)
# 2. Deploy depuis VS Code
```

---

**Support** : Consultez la [documentation GitHub Actions](https://docs.github.com/actions) pour plus d'infos.
