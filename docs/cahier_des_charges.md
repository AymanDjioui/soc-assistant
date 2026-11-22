# Cahier des charges — P11 : Assistant SOC basé sur un LLM

**Module :** IA appliquée à la cybersécurité · **Réalisation :** individuelle · **Durée :** 4 semaines

## 1. Contexte et problématique

Les analystes d'un SOC (Security Operations Center) reçoivent un volume important d'alertes. Pour chaque alerte, ils doivent comprendre ce qu'elle signifie, la rattacher à une technique d'attaque connue et retrouver la procédure de réponse adaptée. Cette recherche est lente et dépend de l'expérience de l'analyste.

Les LLM peuvent accélérer ce travail, mais posent trois problèmes : ils **inventent** des informations (hallucinations), ils peuvent être **manipulés** par du texte malveillant (prompt injection, y compris caché dans une alerte), et les données d'un SOC sont **sensibles** et ne doivent pas quitter l'organisation.

## 2. Objectif

Développer un assistant conversationnel **local** qui aide l'analyste à :

1. interpréter une alerte (résumé d'incident enrichi par MITRE ATT&CK) ;
2. retrouver les procédures de réponse dans des playbooks publics ;
3. fournir des réponses **sourcées** (citations) et **refuser** lorsque les preuves sont insuffisantes ;
4. résister aux injections de prompt directes et indirectes.

## 3. Périmètre fonctionnel (MVP)

| ID | Fonction | Priorité |
|---|---|---|
| F1 | Indexation de playbooks publics et de MITRE ATT&CK (chunking, embeddings, base vectorielle) | Indispensable |
| F2 | Recherche hybride BM25 + dense | Indispensable |
| F3 | Chat question/réponse avec citations des sources | Indispensable |
| F4 | Sélection d'une alerte synthétique → résumé d'incident structuré | Indispensable |
| F5 | Contrôle des hallucinations : refus si score faible, validation des citations | Indispensable |
| F6 | Détecteur de prompt injection entraîné + isolation des données dans le prompt | Indispensable |
| F7 | Mapping automatique alerte → technique ATT&CK évalué | Optionnel |

## 4. Données

- **MITRE ATT&CK** (Enterprise, format STIX 2.1, dépôt `mitre/cti`).
- **Playbooks publics** : CISA, NIST SP 800-61 et dépôts publics de playbooks de réponse à incident (licences vérifiées avant redistribution).
- **Alertes synthétiques** générées par script (format proche de Sigma/ECS), étiquetées par technique ATT&CK, dont une partie contient des charges d'injection.
- **Corpus d'injection** : jeu de données public + exemples synthétiques (bénin / malveillant).

## 5. Architecture technique

Garde anti-injection → recherche hybride → filtre de refus → construction du prompt (données isolées comme non fiables) → LLM local (Ollama, `qwen3:4b-instruct-2507`, accéléré par l'iGPU Intel Iris Xe via Vulkan) → validation des citations → interface Streamlit.

**Langue :** l'assistant (corpus, questions, réponses) fonctionne en anglais, langue de référence de MITRE ATT&CK et des playbooks. Seul le rapport est rédigé en français.

**Approche hybride local/cloud :** l'application, le LLM, la base vectorielle et la démonstration fonctionnent **entièrement en local** (aucune donnée ne quitte la machine). Le cloud (Google Colab / Kaggle, GPU gratuit) sert uniquement à l'**entraînement** du détecteur d'injection. Une API cloud peut être activée en option pendant le développement, jamais pour la démonstration.

## 6. Modèles et évaluation

| Composant | Modèle de référence | Modèle principal | Métriques |
|---|---|---|---|
| Détection d'injection | TF-IDF + régression logistique | DistilBERT / MiniLM fine-tuné | Matrice de confusion, Précision, Rappel, F1, courbes d'entraînement |
| Recherche | BM25 | Hybride BM25 + dense | hit@k, MRR |
| Génération | — | LLM local + garde-fous | Taux de citations valides, exactitude des refus |
| Sécurité de bout en bout | Sans garde | Avec garde | Taux de réussite des attaques |

## 7. Jalons

| Semaine | Jalon | Livrable |
|---|---|---|
| 0 | Cahier des charges | Ce document, squelette du dépôt, LLM local fonctionnel |
| 1 | Préparation des données | Ingestion ATT&CK + playbooks, recherche hybride, chat de base |
| 2 | Fonctionnalités | Alertes synthétiques, résumés d'incident, citations, refus |
| 3 | Développement des modèles | Détecteur d'injection (baseline vs transformer), intégration |
| 4 | Évaluation et démonstration | Résultats chiffrés, rapport (15–25 p.), démonstration |

## 8. Livrables

Code Python documenté (dépôt GitHub), scripts de téléchargement des données, modèle entraîné, résultats d'évaluation (matrices de confusion, P/R/F1, courbes, comparaisons), rapport de 15 à 25 pages, démonstration opérationnelle.

## 9. Contraintes et risques

- Machine sans GPU : modèle 3B quantifié, réponses en streaming, entraînement sur Colab/Kaggle.
- Licences des données : scripts de téléchargement plutôt que redistribution.
- Réalisation individuelle : périmètre MVP strict ; la fonction F7 est abandonnée en priorité en cas de retard.
