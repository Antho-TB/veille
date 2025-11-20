# 🔐 SECRETS GITHUB - Configuration Complète

## Instructions

1. Allez sur votre dépôt GitHub
2. Cliquez sur `Settings` > `Secrets and variables` > `Actions`
3. Cliquez sur `New repository secret`
4. Ajoutez chaque secret ci-dessous

---

## ✅ Secret 1: GEMINI_API_KEY

**Nom du secret:** `GEMINI_API_KEY`

**Valeur:**
```
AIzaSyC5HKLQIQq7k0nM-_fFbcs84j__qG1ot3I
```

**Description:** Clé API pour Gemini (Intelligence Artificielle)

---

## ✅ Secret 2: SEARCH_API_KEY

**Nom du secret:** `SEARCH_API_KEY`

**Valeur:**
```
AIzaSyALFplNyJTXDRU-jB5RRqkb7ML629lL_54
```

**Description:** Clé API pour Google Custom Search

---

## ✅ Secret 3: EMAIL_SENDER

**Nom du secret:** `EMAIL_SENDER`

**Valeur:**
```
anthony.bezille@gmail.com
```

**Description:** Email pour les notifications

---

## ✅ Secret 4: EMAIL_PASSWORD

**Nom du secret:** `EMAIL_PASSWORD`

**Valeur:**
```
xdqz ptef dnts remb
```

**Description:** Mot de passe d'application Gmail (pour notifications)

---

## ✅ Secret 5: GOOGLE_CREDENTIALS

**Nom du secret:** `GOOGLE_CREDENTIALS`

**Valeur:** Tout le contenu du fichier `credentials.json`

### Comment copier credentials.json:

**Option 1 - PowerShell (Recommandé):**
```powershell
Get-Content credentials.json | Set-Clipboard
```
Puis collez directement dans GitHub (Ctrl+V)

**Option 2 - Manuellement:**
1. Ouvrez `credentials.json` dans votre éditeur
2. Sélectionnez tout (Ctrl+A)
3. Copiez (Ctrl+C)
4. Collez dans le champ "Value" de GitHub

**⚠️ IMPORTANT:** Copiez TOUT le fichier JSON, y compris les accolades `{ }` de début et fin.

Le contenu devrait commencer par:
```json
{
  "type": "service_account",
  "project_id": "lemag-477407",
  ...
```

Et finir par:
```json
  ...
  "universe_domain": "googleapis.com"
}
```

---

## 📋 Checklist de Validation

Après avoir ajouté les 5 secrets, vérifiez que:

- [ ] Le nom de chaque secret est EXACTEMENT comme indiqué (sensible à la casse)
- [ ] Aucun espace avant/après les valeurs
- [ ] `GOOGLE_CREDENTIALS` contient un JSON valide complet
- [ ] Les secrets apparaissent dans la liste (mais les valeurs sont masquées)

---

## 🚀 Prochaine Étape

Une fois les secrets configurés:

```bash
# 1. Initialiser Git (si pas déjà fait)
git init

# 2. Ajouter le remote
git remote add origin https://github.com/VOTRE_USERNAME/veille-reglementaire.git

# 3. Commit et push
git add .
git commit -m "Initial commit: Pipeline de veille avec CI/CD"
git push -u origin main
```

Le workflow démarrera automatiquement ! 🎯

---

## ❓ Dépannage

**Les secrets ne s'affichent pas:**
- Normal ! GitHub masque les valeurs pour la sécurité
- Vous verrez juste le nom du secret

**Erreur "Invalid credentials":**
- Vérifiez que `GOOGLE_CREDENTIALS` contient bien TOUT le JSON
- Pas de caractères invisibles ou espaces

**Email non reçu:**
- Vérifiez que `EMAIL_PASSWORD` est un "Mot de passe d'application" Gmail
- Activez l'accès moins sécurisé si nécessaire
