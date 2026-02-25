# Plan des Tâches - Déploiement Production Azure

- [x] Analyser le flux d'exécution du code local actuel (`run_tasks.bat`).
- [x] Créer les configurations Terraform pour Azure (`main.tf`, `variables.tf`, `providers.tf`).
  - [x] Configurer `func-shsv-veille-prod` (Azure Function)
  - [x] Configurer `kv-shsv-veille-prod` (Key Vault)
  - [x] Configurer `stshsvveilleprod` (Storage Account)
  - [x] Configurer `log-platform-logs-prd` (Log Analytics)
  - [x] S'assurer de la présence des tags spécifiques (`project: GDD-Veille`, `deployment: IaC`, `owner: QHSE-GDD`) et de la région (`North Europe`).
- [x] Refactoriser le code Python pour Azure Functions :
  - [x] Créer une enveloppe `function_app.py` autour de `src/core/pipeline.py`.
  - [x] Gérer les chemins de manière indépendante de l'OS (`os.path.join`).
- [x] Créer un workflow GitHub Actions pour la CI/CD.
  - [x] Déployer l'infrastructure via Terraform.
  - [x] Déployer l'archive zip de la Function Azure.
- [x] Configurer le déploiement de MLflow sur Azure Container Instance (ACI) pointant vers un backend Azure Blob Storage.

## Révision
L'infrastructure Azure a été définie via Terraform (ressources principales, function app, key vault, accès policy, log analytics, ACI pour MLFlow).
L'application Function `function_app.py` a été créée pour automatiser les tâches (timer).
Le workflow GitHub Actions `deploy.yml` a été mis en place pour assurer la CI/CD.
