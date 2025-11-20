# 🚀 Commandes Git pour Configurer le CI/CD

# ÉTAPE 1 : Initialiser Git localement
git init

# ÉTAPE 2 : Configurer l'identité (si pas déjà fait)
git config user.name "Anthony Bezille"
git config user.email "anthony.bezille@gmail.com"

# ÉTAPE 3 : Ajouter le remote GitHub
git remote add origin https://github.com/Antho-TB/veille.git

# ÉTAPE 4 : Créer la branche main
git branch -M main

# ÉTAPE 5 : Ajouter tous les fichiers (sauf ceux dans .gitignore)
git add .

# ÉTAPE 6 : Vérifier ce qui sera commité
git status

# ÉTAPE 7 : Premier commit
git commit -m "feat: Pipeline de veille réglementaire avec CI/CD

- Pipeline de veille automatisée (recherche 2 ans)
- Déduplication anti-doublons
- Analyse IA (Gemini)
- GitHub Actions (tests + exécution quotidienne)
- Documentation complète"

# ÉTAPE 8 : Pousser vers GitHub
git push -u origin main

# ✅ TERMINÉ ! Vérifiez sur GitHub :
# - https://github.com/Antho-TB/veille (fichiers)
# - https://github.com/Antho-TB/veille/actions (workflows)
