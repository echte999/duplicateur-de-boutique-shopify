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
