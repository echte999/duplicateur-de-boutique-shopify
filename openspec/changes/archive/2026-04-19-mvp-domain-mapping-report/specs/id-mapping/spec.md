## ADDED Requirements

### Requirement: Enregistrer la correspondance entre un ID source et un ID cible
Le système SHALL permettre d'enregistrer une entrée `(type, id_source, id_cible)` dans la table de correspondance via `id_map.register(type, src_id, tgt_id)`.

#### Scenario: Enregistrement d'un produit
- **WHEN** un produit est créé sur la boutique cible avec l'ID `9876`
- **THEN** `id_map.register("product", 1234, 9876)` ajoute l'entrée sans erreur

#### Scenario: Enregistrement d'une collection
- **WHEN** une collection est créée sur la boutique cible
- **THEN** la correspondance est enregistrée avec le type `"collection"`

### Requirement: Résoudre un ID source en ID cible
Le système SHALL retourner l'ID cible correspondant à un ID source via `id_map.resolve(src_id)`, ou `None` si l'ID n'est pas connu.

#### Scenario: Résolution d'un ID enregistré
- **WHEN** `id_map.register("product", 1234, 9876)` a été appelé
- **THEN** `id_map.resolve(1234)` retourne `9876`

#### Scenario: Résolution d'un ID inconnu
- **WHEN** un ID source n'a pas été enregistré
- **THEN** `id_map.resolve(99999)` retourne `None`

### Requirement: Persister la table sur disque après chaque phase
Le système SHALL écrire la table complète dans `output/id_map.json` via `id_map.save()` après chaque phase de clonage.

#### Scenario: Sauvegarde après la phase produits
- **WHEN** tous les produits ont été clonés
- **THEN** `output/id_map.json` contient toutes les correspondances produits enregistrées

#### Scenario: Le fichier est lisible entre deux exécutions
- **WHEN** `id_map.load()` est appelé au démarrage avec un fichier existant
- **THEN** toutes les correspondances précédemment sauvegardées sont disponibles via `resolve()`

### Requirement: Charger la table depuis le disque au démarrage
Le système SHALL charger `output/id_map.json` au démarrage via `id_map.load()` si le fichier existe, pour permettre la reprise d'un clonage interrompu.

#### Scenario: Démarrage avec un fichier existant
- **WHEN** `output/id_map.json` existe avec des entrées valides
- **THEN** `id_map.load()` les charge et elles sont disponibles via `resolve()`

#### Scenario: Démarrage sans fichier existant
- **WHEN** `output/id_map.json` n'existe pas
- **THEN** `id_map.load()` initialise une table vide sans erreur
