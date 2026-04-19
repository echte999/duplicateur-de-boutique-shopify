## ADDED Requirements

### Requirement: Structure de la table de correspondance
Le système SHALL maintenir une table de correspondance en mémoire et sur disque (`output/id_map.json`) avec la structure `{ "product": { "id_source": "id_cible" }, "variant": { "id_source": "id_cible" } }`.

#### Scenario: Table vide au démarrage
- **WHEN** aucun fichier `output/id_map.json` n'existe
- **THEN** la table est initialisée comme `{ "product": {}, "variant": {}, "collection": {}, "page": {}, "blog": {}, "article": {}, "menu": {} }`

#### Scenario: Chargement d'une table existante
- **WHEN** `output/id_map.json` existe (clone précédent partiel)
- **THEN** la table est chargée depuis le fichier et les entrées existantes sont conservées

### Requirement: Persistance après chaque ressource créée
Le système SHALL sauvegarder `output/id_map.json` sur disque immédiatement après chaque ressource créée avec succès.

#### Scenario: Sauvegarde intermédiaire
- **WHEN** le produit 5 sur 100 est créé avec succès
- **THEN** `output/id_map.json` contient les correspondances des 5 premiers produits avant de traiter le 6ème

### Requirement: Résolution d'ID via la table
Le système SHALL exposer une méthode `get(resource_type, source_id)` qui retourne l'ID cible correspondant, ou lève une `KeyError` si la correspondance n'existe pas.

#### Scenario: Résolution existante
- **WHEN** `get("product", "111")` est appelé et `id_map["product"]["111"] == "999"`
- **THEN** retourne `"999"`

#### Scenario: Correspondance manquante
- **WHEN** `get("product", "999")` est appelé et aucune entrée n'existe
- **THEN** lève `KeyError` avec un message indiquant le type et l'ID source manquant

### Requirement: Enregistrer une correspondance via register()
Le système SHALL permettre d'enregistrer une entrée `(type, id_source, id_cible)` dans la table via `id_map.register(type, src_id, tgt_id)`.

#### Scenario: Enregistrement d'un produit
- **WHEN** un produit est créé sur la boutique cible avec l'ID `9876`
- **THEN** `id_map.register("product", 1234, 9876)` ajoute l'entrée sans erreur

#### Scenario: Enregistrement d'une collection
- **WHEN** une collection est créée sur la boutique cible
- **THEN** la correspondance est enregistrée avec le type `"collection"`

### Requirement: Résoudre un ID source en ID cible via resolve()
Le système SHALL exposer une méthode `resolve(src_id)` qui retourne l'ID cible correspondant, ou `None` si l'ID n'est pas connu.

#### Scenario: Résolution d'un ID enregistré
- **WHEN** `id_map.register("product", 1234, 9876)` a été appelé
- **THEN** `id_map.resolve(1234)` retourne `9876`

#### Scenario: Résolution d'un ID inconnu
- **WHEN** un ID source n'a pas été enregistré
- **THEN** `id_map.resolve(99999)` retourne `None`

### Requirement: Persister la table sur disque après chaque phase via save()
Le système SHALL écrire la table complète dans `output/id_map.json` via `id_map.save()` après chaque phase de clonage.

#### Scenario: Sauvegarde après la phase produits
- **WHEN** tous les produits ont été clonés
- **THEN** `output/id_map.json` contient toutes les correspondances produits enregistrées

#### Scenario: Le fichier est lisible entre deux exécutions
- **WHEN** `id_map.load()` est appelé au démarrage avec un fichier existant
- **THEN** toutes les correspondances précédemment sauvegardées sont disponibles via `resolve()`

### Requirement: Charger la table depuis le disque au démarrage via load()
Le système SHALL charger `output/id_map.json` au démarrage via `id_map.load()` si le fichier existe, pour permettre la reprise d'un clonage interrompu.

#### Scenario: Démarrage avec un fichier existant
- **WHEN** `output/id_map.json` existe avec des entrées valides
- **THEN** `id_map.load()` les charge et elles sont disponibles via `resolve()`

#### Scenario: Démarrage sans fichier existant
- **WHEN** `output/id_map.json` n'existe pas
- **THEN** `id_map.load()` initialise une table vide sans erreur
