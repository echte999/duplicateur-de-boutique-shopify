## ADDED Requirements

### Requirement: Lecture de toutes les politiques depuis la boutique source
Le système SHALL lire l'ensemble des politiques du site depuis la boutique source via `GET /admin/api/2024-01/policies.json` et retourner la liste des politiques avec leur type et leur `body` HTML.

#### Scenario: Boutique avec politiques définies
- **WHEN** la boutique source a des politiques (remboursement, CGV, confidentialité…)
- **THEN** toutes sont retournées avec leur `title`, `body`, et le type déductible

#### Scenario: Boutique sans politique définie
- **WHEN** la boutique source n'a aucune politique configurée
- **THEN** la phase se termine sans erreur et aucune écriture n'est effectuée

### Requirement: Remapping du contenu de chaque politique
Le système SHALL appliquer `domain.remap()` sur le `body` HTML de chaque politique avant écriture, incluant le remplacement du nom de boutique source par le nom de boutique cible.

#### Scenario: Politique contenant le domaine source
- **WHEN** le `body` d'une politique contient `https://source.myshopify.com`
- **THEN** l'URL est remplacée par le domaine cible avant écriture

#### Scenario: Politique contenant le nom de la boutique source
- **WHEN** le `body` contient le nom de la boutique source (ex : "Ma Boutique Source")
- **THEN** le nom est remplacé par le nom de la boutique cible avant écriture

### Requirement: Écriture des politiques sur la boutique cible
Le système SHALL écrire chaque politique remappée sur la boutique cible. Shopify ne fournissant pas d'ID unique par politique, l'écriture utilise le type de politique comme identifiant (`refund_policy`, `privacy_policy`, etc.).

#### Scenario: Écriture réussie d'une politique
- **WHEN** la politique remappée est envoyée à la boutique cible
- **THEN** la politique est mise à jour sur la boutique cible et le résultat est ajouté au rapport avec statut `ok`

#### Scenario: Politique non modifiable sur la boutique cible
- **WHEN** l'API retourne une erreur 422 (politique non modifiable sur ce plan Shopify)
- **THEN** l'erreur est loguée, la politique est marquée `skipped` dans le rapport, et le clonage continue

### Requirement: Inclusion des politiques dans le rapport post-clonage
Le système SHALL ajouter une entrée par politique dans `clone_report.json` avec les champs `type`, `title`, `statut` (`ok` ou `skipped`), et le motif d'erreur si applicable.

#### Scenario: Rapport après clonage complet
- **WHEN** toutes les politiques ont été traitées
- **THEN** chaque politique apparaît dans le rapport avec son statut final
