# 📋 Rapport d'Analyse Réglementaire & État de Préparation Audit ISO 14001

Ce document détaille la méthodologie d'analyse des données et les garanties de conformité pour **Générale de Découpage**. Il est conçu pour être présenté lors d'un audit de certification.

---

## 1. Assurance de l'Exhaustivité
**Question :** *"Comment être sûr que nous avons relevé tous les textes qui nous concernent ?"*

Le système repose sur une veille active **"Open-Web"** :
*   **Recherche Multi-Sources (Google & Tavily)** : Contrairement à une veille statique limitée à quelques URLs, l'outil utilise l'API Google Search pour indexer l'intégralité du web accessible. Tout nouveau texte publié (Loi, Décret, Arrêté préfectoral) est capturé dès son indexation.
*   **Périmètre Métier Configuré** : La veille est pilotée par des mots-clés "métier" ultra-précis (Rubriques ICPE 2560/2564, Découpage métaux, Fluides, TMD).
*   **Analyse d'Écart par IA (Gap Analysis)** : Un algorithme compare périodiquement la base avec un référentiel théorique standard pour identifier d'éventuels manquements historiques.
*   **Double Validation** : L'IA agit comme un filtre de pertinence pour éviter le "bruit" tout en garantissant qu'aucune exigence majeure n'est ignorée.

## 2. Portée Technologique de la Recherche
**Question :** *"La recherche se fait-elle sur tous les sites accessibles via Google ?"*

**Réponse : OUI.** Contrairement à une recherche manuelle ou une veille par flux RSS qui se limite à quelques sites, notre intégration utilise le mode **"Search the entire web"**.

*   **Google Custom Search API** : S'appuie sur l'index mondial de Google. Elle détecte tout document PDF, Arrêté ou article dès qu'il est indexé par Google (Légifrance, INERIS, Préfectures, DREAL, etc.).
*   **Filtrage par Concepts** : Nous ne limitons pas la recherche à des URLs spécifiques mais à des concepts (ex: "Arrêté ICPE 2560"). Cela permet de découvrir des textes sur des sites de syndicats professionnels ou de revues juridiques que nous n'aurions pas listés manuellement.
*   **Analyse Sémantique par LLM** : Le moteur récupère les résultats, puis les soumet à un modèle de langage (Google Gemini 1.5 Pro) qui décide si le texte concerne réellement l'activité de GDD.

## 3. Méthodologie de Criticité (Méthode KPR)
La criticité est calculée via le **Keyword-based Priority Ranking (KPR)**, simulant le regard d'un auditeur de certification :

| Niveau | Logique Auditoriale | Impact Opérationnel |
| :--- | :--- | :--- |
| **HAUTE** | Sanction pénale, Changement de VLE (Air/Eau), MAJ d'arrêté ICPE. | Arrêt d'activité ou mise en demeure possible. |
| **MOYENNE** | Obligation de reporting (REP, Registre), Investissement mineur. | Risque de non-conformité majeure en audit. |
| **BASSE** | Mise à jour administrative (Cerfa), Changement de site web. | Remarque ou piste d'amélioration en audit. |

## 4. Éléments pour l'Auditeur ISO 14001
*   **Registre des Preuves** : Le champ "Preuve de Conformité Attendue" a été ajouté pour chaque texte. Lors de l'audit, il suffit de présenter ce document précis (PV, Registre, BSD) pour clore le point.
*   **Sources Officielles** : La veille s'appuie exclusivement sur des institutions de confiance (Légifrance, INERIS, DREAL, JOUE).
*   **Piste d'Audit (Audit Trail)** : L'historique complet des évaluations est conservé dans l'onglet **`Base_Active`** et tracé via **MLflow** pour prouver la continuité de la veille.

## 5. Analyse des KPIs (Février 2026)
*   **994 textes suivis** : Base de données exhaustive couvrant l'historique nécessaire.
*   **291 textes applicables** : Filtrage efficace pour ne garder que les exigences substantielles.
*   **Ratio de Divers < 10%** : Thématiques ré-analysées pour une classification précise (Risques, Déchets, Eau).
*   **261 actions requises** : Principalement des réévaluations périodiques pour maintenir la conformité.

---
*Ce document fait partie intégrante du système de management environnemental de Générale de Découpage.*
