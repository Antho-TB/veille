# Rapport d'Analyse Reglementaire - Etat de Preparation Audit ISO 14001

Ce document detaille la mythodologie d'analyse des donnees et les garanties de conformite pour Generale de Decoupage (GDD). Il est concu pour etre presente lors d'un audit de certification.

---

## 1. Assurance de l'Exhaustivite
**Question :** "Comment etre sur que nous avons releve tous les textes qui nous concernent ?"

Le systeme repose sur une veille active "Open-Web" :
*   **Recherche Multi-Sources (Google et Tavily)** : Contrairement a une veille statique limitee a quelques URLs, l'outil utilise des APIs de recherche pour indexer l'integralite du web accessible. Tout nouveau texte publie (Loi, Decret, Arrete prefectoral) est capture des son indexation.
*   **Perimetre Metier Dynamique** : La veille est pilotee par des mots-cles "metier" generes dynamiquement par l'IA en fonction de la Fiche Descriptive Detaillee de GDD.
*   **Analyse d'Ecart par IA (Gap Analysis)** : Un algorithme compare periodiquement la base avec les obligations theoriques decoulant du profil industriel de l'usine pour identifier d'eventuels manquements.
*   **Double Validation** : L'IA agit comme un filtre de pertinence pour eliminer le bruit tout en garantissant qu'aucune exigence majeure n'est ignoree.

## 2. Portee Technologique de la Recherche
**Question :** "La recherche se fait-elle sur tous les sites accessibles via Google ?"

**Reponse : OUI.** L'integration utilise le mode "Search the entire web".

*   **Google Custom Search API** : S'appuie sur l'index mondial de Google. Elle detecte tout document PDF, Arrete ou article des qu'il est indexe par Google (Legifrance, INERIS, Prefectures, DREAL, etc.).
*   **Filtrage par Concepts** : La recherche ne se limite pas a des URLs specifiques mais a des concepts (ex: "Arrete ICPE 2560"). Cela permet de decouvrir des textes sur des sites de syndicats professionnels ou de revues juridiques.
*   **Analyse Semantique par LLM** : Le moteur recupere les resultats, puis les soumet au modele Google Gemini qui decide de l'applicabilite reelle pour GDD.

## 3. Methodologie de Criticite (Methode KPR)
La criticite est calculee via le Keyword-based Priority Ranking (KPR), simulant le regard d'un auditeur de certification :

| Niveau | Logique Auditoriale | Impact Operationnel |
| :--- | :--- | :--- |
| **HAUTE** | Risque penal, arret d'activite ou modification majeure d'arrete ICPE. | Sanction immediate ou mise en demeure. |
| **MOYENNE** | Obligation de reporting technique, investissement modere. | Risque de non-conformite majeure en audit. |
| **BASSE** | Mise a jour administrative mineure ou piste d'amelioration. | Remarque ou recommandation simple. |
| **INFORMATIF** | Texte utile pour la culture QHSE mais sans action immédiate. | Documentation et veille generale. |

## 4. Transparence des Algorithmes (Prompts IA)
Pour garantir la transparence totale de l'audit, voici les instructions exactes (prompts) fournies a l'IA :

### 1. Generation des Mots-Cles de Recherche (Open-Web)
```text
Directeur QHSE. Genere 12 mots-cles Google Strategiques pour la veille de GDD.
Focus : Nouvelles lois Environnement, SST, ICPE metaux, REACH, CSRD.
CONTEXTE USINE : [Contenu de la Fiche Descriptive Detaillee]
Reponds au format JSON : ["mot-cle 1", "mot-clle 2", ...]
```

### 2. Analyse de Pertinence et Criticite (Filtrage)
```text
Role : Directeur QHSE Expert GDD.
CONTEXTE USINE : [Contenu de la Fiche Descriptive Detaillee (Synchro Live via Google Docs)]
EVALUE CE TEXTE : "[Extrait du web]"

MISSION : Determiner l'applicabilite, la criticite et l'action requise pour le site industriel.

HISTORIQUE AUDIT ISO 14001 (A PRIORISER) :
1. Le dernier audit a releve des faiblesses sur la consommation energetique.
2. Vigilance particuliere attendue sur les Dechets et l'Energie.

REGLE DE TRI :
- SOIS EXHAUSTIF : Retiens un maximum de textes applicables de pres ou de loin a l'entreprise (ICPE, Energie, Securite...), classe-les plutot en 'Basse' ou 'Informatif' plutot que de les rejeter.
- Ne mets en criticite 'Non' (Bruit) QUE si le texte est TOTALEMENT hors-sujet ou etranger au perimetre. Tous les autres textes industriels doivent etre gardes.

CRITERES DE CRITICITE (KPR) :
- Haute : Risque penal, arret d'activite ou modification majeure d'arrete ICPE.
- Moyenne : Obligation de reporting technique, investissement modere ou risque de non-conformite majeure en audit.
- Basse : Mise a jour administrative mineure ou piste d'amelioration.

CONSIGNE TECHNIQUE :
- 'numero' : Extraire le N° officiel (ex: Decret 2026-23).
- 'preuve_attendue' : Doit etre un document TANGIBLE (ex: Registre, Certificat).
- 'justification' : Raison pour laquelle la criticite choisie a ete attribuee.
```

### 3. Gap Analysis (Audit de Completude Mensuel)
```text
Expert QHSE. MISSION : Identifier les textes reglementaires manquants pour l'usine GDD.
CONTEXTE USINE (Fiche d'identite) : [Contenu de la Fiche Descriptive Detaillee]
BASE ACTUELLE : [Liste des 500 derniers textes en base]

HISTORIQUE AUDIT ISO 14001 (A PRIORISER) :
- Le dernier audit (DNV) a releve des faiblesses sur la consommation energetique.
- Cherche imperativement si des textes sur l'efficacite energetique et les F-Gas sont manquants.

CONSIGNES :
1. Identifie 10 textes MAJEURS manquants (Lois, Decrets, Arretes). Focus Energie, ICPE 2560, REACH, Dechets.
2. Pour chaque texte, identifie precisement le titre, la date, la criticite KPR, l'action attendue et la preuve.
```

## 5. Elements pour l'Auditeur ISO 14001
*   **Registre des Preuves** : Le champ "Preuve de Conformite Attendue" est complete par l'IA pour chaque texte.
*   **Dashboard Interactif** : Pilotage via une interface "Live" (Recherche multi-mots, tri par pertinence).
*   **Piste d'Audit (Audit Trail)** : Historisation technique via MLflow (frequence, reussite/echec, modele utilise).
*   **Routage IA et Justification** : Isolation automatique des textes pertinents non-bloquants dans un onglet `Informative`.
*   **Filtre Rejet (Anti-Bruit)** : Tout texte rejete par l'IA (non-applicable) est logue dans l'onglet `Filtre_Rejet` avec sa justification pour un re-controle echantillonable par un humain.
*   **Reevaluation** : Controle automatique de la validite des preuves tous les 3 ans avec proposition d'actions concretes.

---
*Ce document fait partie integrante du systeme de management environnemental de Generale de Decoupage.*
