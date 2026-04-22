## ADDED Requirements

### Requirement: Cloner toutes les price rules de la boutique source
Le système SHALL récupérer toutes les price rules de la boutique source via `GET /price_rules.json?limit=250` et créer leur équivalent sur la boutique cible.

#### Scenario: Clonage d'une price rule simple
- **WHEN** une price rule existe sur la source
- **THEN** une price rule identique (mêmes type, valeur, conditions, dates) est créée sur la cible avec un nouvel ID

#### Scenario: Price rule avec entitled_product_ids
- **WHEN** une price rule cible des produits spécifiques (`entitled_product_ids` non vide)
- **THEN** les IDs produits sont remappés via la table `id_map` avant création sur la cible

#### Scenario: Price rule avec entitled_collection_ids
- **WHEN** une price rule cible des collections spécifiques (`entitled_collection_ids` non vide)
- **THEN** les IDs collections sont remappés via la table `id_map` avant création sur la cible

#### Scenario: Price rule avec prerequisite_product_ids
- **WHEN** une price rule a des produits prérequis (`prerequisite_product_ids` non vide)
- **THEN** les IDs produits sont remappés via la table `id_map` avant création sur la cible

### Requirement: Remettre les compteurs d'utilisation à zéro
Le système SHALL exclure le champ `usage_count` du payload lors de la création d'une price rule sur la cible, garantissant que le compteur repart à zéro.

#### Scenario: Exclusion de usage_count
- **WHEN** une price rule source a `usage_count > 0`
- **THEN** la price rule créée sur la cible a `usage_count = 0`

### Requirement: Copier les codes de réduction associés
Le système SHALL récupérer tous les discount codes d'une price rule source via `GET /price_rules/{id}/discount_codes.json` et les recréer sur la price rule cible correspondante.

#### Scenario: Copie d'un code de réduction
- **WHEN** une price rule source a un ou plusieurs discount codes
- **THEN** chaque code est recréé sur la price rule cible (même chaîne de caractères)

#### Scenario: Code de réduction déjà existant
- **WHEN** un code de réduction existe déjà sur la boutique cible (clonage relancé)
- **THEN** l'erreur est ignorée silencieusement et le clonage continue

### Requirement: Enregistrer les price rules dans la table de correspondance
Le système SHALL enregistrer la correspondance `source_id → target_id` pour chaque price rule clonée via `mapping.set("price_rule", source_id, target_id)`.

#### Scenario: Enregistrement de la correspondance
- **WHEN** une price rule est clonée avec succès
- **THEN** `mapping.get("price_rule", source_id)` retourne le `target_id` correspondant

### Requirement: Tolérance aux erreurs par price rule
Le système SHALL capturer les exceptions au niveau de chaque price rule individuelle, logger l'erreur, et continuer avec la suivante sans interrompre la phase.

#### Scenario: Erreur sur une price rule
- **WHEN** la création d'une price rule échoue sur la cible
- **THEN** l'erreur est loggée avec l'ID et le titre de la rule, et le traitement passe à la price rule suivante
