# Stratégie de Mise en Production - Veille Réglementaire GDD (Standard TB-Groupe)

Ce document définit la trajectoire technique pour déployer l'architecture de veille sur **Microsoft Azure**, en stricte conformité avec les standards de la **Landing Zone TB-Groupe**.

## 1. Architecture & Gouvernance (Standards TB)

### Convention de Nommage
Toutes les ressources doivent suivre le format imposé par le prestataire : `<Prefix>-shsv-veille-<Env>`.
*   **Azure Function** : `func-shsv-veille-prod`
*   **Key Vault** : `kv-shsv-veille-prod`
*   **Storage Account** : `stshsvveilleprod` (Sans tirets, minuscules)
*   **Log Analytics** : Connexion obligatoire au puit central `log-platform-logs-prd`.

### Région & Localisation
- **Région unique** : `North Europe` (northeurope). 
- **Management Group** : `Shared Services` (shsv).

### Tags Obligatoires (FinOps & Inventaire)
| Tag | Valeur |
| :--- | :--- |
| `project` | `GDD-Veille` |
| `deployment` | `IaC` |
| `owner` | `QHSE-GDD` |

---

## 2. Infrastructure as Code (Terraform)

Le déploiement doit utiliser le module standard `mod-landing-zone`.
- **Secrets** : Utilisation d'**Identités Managées (MSI)** (Azure Key Vault). Plus aucun secret ne doit transiter en clair dans les variables d'environnement.
- **Réseau** : Isolation dans un VNet dédié avec accès restreint via Azure Policy.

---

## 3. MLOps & Monitoring (Observabilité)

### MLflow & Docker
- **Composant** : Serveur MLflow hébergé via **Azure Container Instance (ACI)**.
- **Backend** : Stockage des artefacts (Embeddings CamemBERT) sur un Azure Blob Storage sécurisé.

### Observabilité
- Centralisation forcée des logs vers le workspace global `log-platform-logs-prd`.
- Alerting configuré via **Application Insights** pour les échecs critiques du pipeline Gemini.

---

## 4. Pipeline CI/CD (GitHub Actions)

Utilisation des templates de CI TB-Groupe :
1. **Tokenisation** : Injection des secrets via le format `@#{SECRET_NAME}#@`.
2. **Runners** : Utilisation de **Self-hosted Runners** pour garantir l'accès au réseau privé de la Landing Zone.

---

## 5. Analyse des Risques de Migration (Local ➡️ Cloud)

Le passage d'un prototype local (Windows) à une infrastructure d'entreprise (Linux/Azure) comporte des risques critiques :

### A. Migration Cross-Platform (Windows ➡️ Linux)
- **Risque** : Utilisation de chemins statiques (`C:\...`) ou de séparateurs Windows (`\`) dans le code local.
- **Solution** : Utilisation de `os.path.join` et de variables d'environnement dynamiques.

### B. Gouvernance & Sécurité (Key Vault)
- **Risque** : Une isolation réseau trop stricte dans la Landing Zone pourrait bloquer l'accès aux API Google Gemini ou Google Sheets.
- **Solution** : Autoriser les flux sortants vers les APIs Google dans le VNet de la landing zone.

### C. Ressources mémoire (Deep Learning)
- **Risque** : L'audit sémantique CamemBERT est gourmand (> 512 Mo).
- **Solution** : Allouer un Service Plan de type **Premium V2 (EP1)** strict pour éviter les OOM.

### D. Timezones & Horaires
- **Risque** : Les dates dans les rapports pourraient être décalées (UTC vs Paris).
- **Solution** : Configurer `WEBSITE_TIMEZONE = Europe/Paris` dans l'Azure Function.

---

> [!IMPORTANT]
> **Consigne de Sécurité** : Ne jamais pousser le répertoire `config/` (contenant les credentials Google) sur le dépôt Git. Ces secrets doivent être injectés manuellement dans le Key Vault.
