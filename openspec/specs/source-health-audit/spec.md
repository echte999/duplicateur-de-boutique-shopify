# source-health-audit Specification

## Purpose
TBD - created by archiving change audit-source-health. Update Purpose after archive.
## Requirements
### Requirement: Audit de santé préflight avant clonage
Le système SHALL exécuter un audit de santé de la boutique source avant la première écriture sur la boutique cible. Cet audit SHALL respecter les phases sélectionnées pour le run courant, écrire un rapport `output/source_health_audit.json`, et afficher un résumé terminal. Si au moins une anomalie est détectée, le système SHALL demander une confirmation explicite avant de poursuivre le clonage.

#### Scenario: Aucune anomalie détectée
- **WHEN** l'utilisateur lance un clonage et que l'audit ne trouve aucun objet orphelin dans le périmètre sélectionné
- **THEN** le système écrit un rapport d'audit sans issue et poursuit automatiquement le clonage

#### Scenario: Anomalies détectées puis abandon utilisateur
- **WHEN** l'audit trouve une ou plusieurs anomalies et que l'utilisateur refuse de continuer
- **THEN** le système arrête le run avant toute écriture cible, après avoir persisté le rapport d'audit

#### Scenario: Run partiel
- **WHEN** l'utilisateur lance un clonage avec uniquement `theme` sélectionné
- **THEN** le système n'exécute que les contrôles d'audit nécessaires au thème et ignore les détecteurs menus et réductions

### Requirement: Détection des références orphelines dans les menus source
Le système SHALL inspecter tous les items de menus source et signaler comme anomalie toute référence structurée (`resourceId`) pointant vers un produit, une collection, une page, un blog ou un article absent de la boutique source, ainsi que tout type de ressource non supporté pour le remapping.

#### Scenario: Item de menu vers un produit supprimé
- **WHEN** un item de menu source référence `gid://shopify/Product/123` et que le produit `123` n'existe pas dans la boutique source
- **THEN** l'audit ajoute une anomalie de menu décrivant l'item concerné et la référence manquante

#### Scenario: Item de menu vers un type non supporté
- **WHEN** un item de menu source porte un `resourceId` d'un type Shopify non géré par le clone
- **THEN** l'audit ajoute une anomalie indiquant le type non supporté et la localisation de l'item

### Requirement: Détection des références orphelines dans les réductions source
Le système SHALL inspecter les price rules source et signaler comme anomalie toute référence de `entitled_product_ids`, `entitled_collection_ids` ou `prerequisite_product_ids` vers une ressource absente de la boutique source.

#### Scenario: Réduction ciblant une collection supprimée
- **WHEN** une price rule source contient `entitled_collection_ids: [456]` et que la collection `456` n'existe plus dans la boutique source
- **THEN** l'audit ajoute une anomalie de réduction contenant l'ID de la rule et l'ID de collection manquante

#### Scenario: Réduction saine
- **WHEN** toutes les références produits et collections d'une price rule existent dans la boutique source
- **THEN** l'audit n'ajoute aucune anomalie pour cette règle

### Requirement: Détection des références orphelines dans les assets JSON du thème
Le système SHALL analyser les assets JSON du thème source et signaler comme anomalie toute référence structurée produit ou collection (GID Shopify ou ID remappable) qui ne correspond à aucune ressource source existante.

#### Scenario: GID produit cassé dans un template JSON
- **WHEN** un asset JSON du thème contient `gid://shopify/Product/789` et que le produit `789` n'existe pas dans la boutique source
- **THEN** l'audit ajoute une anomalie de thème indiquant le fichier et la référence cassée

#### Scenario: Référence collection valide dans `settings_data.json`
- **WHEN** un asset JSON du thème contient une référence collection qui correspond à une collection source existante
- **THEN** l'audit ne crée pas d'anomalie pour cette référence

