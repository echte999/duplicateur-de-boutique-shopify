### Requirement: Cloner les price rules de la boutique source vers la boutique cible
Le système SHALL récupérer toutes les price rules de la boutique source via `GET price_rules.json?limit=250` et les recréer sur la boutique cible en remappant les IDs de produits, collections et variantes référencés.

#### Scenario: Clonage d'une price rule sans références
- **WHEN** une price rule ne référence aucun produit ni collection
- **THEN** elle est recréée à l'identique sur la cible (sans les champs `id`, `admin_graphql_api_id`, `created_at`, `updated_at`, `usage_count`, `customer_segment_prerequisite_ids`)

#### Scenario: Clonage d'une price rule avec entitled_product_ids
- **WHEN** une price rule contient des `entitled_product_ids`
- **THEN** chaque ID source est remplacé par l'ID cible correspondant via `mapping.get("product", pid)`

#### Scenario: Clonage d'une price rule avec entitled_collection_ids
- **WHEN** une price rule contient des `entitled_collection_ids`
- **THEN** chaque ID source est remplacé par l'ID cible correspondant via `mapping.get("collection", cid)`

#### Scenario: Clonage d'une price rule avec prerequisite_product_ids
- **WHEN** une price rule contient des `prerequisite_product_ids`
- **THEN** chaque ID source est remplacé par l'ID cible correspondant via `mapping.get("product", pid)`

#### Scenario: Échec du clonage d'une price rule
- **WHEN** la création d'une price rule sur la cible lève une exception
- **THEN** l'erreur est loggée et l'entrée de rapport contient `statut: "error: <message>"` avec `id_cible: null`

### Requirement: Cloner les discount codes associés à chaque price rule
Le système SHALL copier tous les codes de réduction (`discount_codes`) de chaque price rule source vers la price rule cible correspondante.

#### Scenario: Copie des codes de réduction
- **WHEN** une price rule est clonée avec succès
- **THEN** ses discount codes sont récupérés via `GET price_rules/{source_id}/discount_codes.json` et recrées sur la cible via `POST price_rules/{target_id}/discount_codes.json`

#### Scenario: Conflit sur un code de réduction
- **WHEN** un code de réduction existe déjà sur la cible ou provoque un conflit
- **THEN** l'exception est silencieusement ignorée et le clonage continue

### Requirement: Enregistrer le mapping source→cible des price rules
Le système SHALL appeler `mapping.set("price_rule", source_id, target_id)` après chaque price rule clonée avec succès.

#### Scenario: Mapping enregistré après clonage réussi
- **WHEN** une price rule est créée avec succès sur la cible
- **THEN** `mapping.set("price_rule", source_id, target_id)` est appelé avec les IDs corrects
