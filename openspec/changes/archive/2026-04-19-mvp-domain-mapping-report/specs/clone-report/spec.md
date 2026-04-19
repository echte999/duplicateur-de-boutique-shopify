## ADDED Requirements

### Requirement: Accumuler les entrées de rapport pendant le clonage
Le système SHALL permettre d'ajouter une entrée au rapport via `report.add_entry(type, src_id, tgt_id, status)` depuis n'importe quelle phase de clonage.

#### Scenario: Ajout d'une entrée produit réussie
- **WHEN** un produit est cloné avec succès
- **THEN** `report.add_entry("product", 1234, 9876, "ok")` ajoute l'entrée sans erreur

#### Scenario: Ajout d'une entrée en échec
- **WHEN** une ressource échoue à être clonée
- **THEN** `report.add_entry("product", 1234, None, "error")` enregistre l'échec avec `tgt_id` null

### Requirement: Générer le fichier rapport JSON en fin de clonage
Le système SHALL écrire `output/clone_report.json` via `report.generate()`, contenant la liste de toutes les entrées accumulées au format `{ "type", "id_source", "id_cible", "statut" }`.

#### Scenario: Génération du rapport après clonage complet
- **WHEN** toutes les phases sont terminées et `report.generate()` est appelé
- **THEN** `output/clone_report.json` existe et contient une liste JSON de toutes les entrées

#### Scenario: Format de chaque entrée
- **WHEN** le rapport est généré
- **THEN** chaque entrée contient exactement les champs `type`, `id_source`, `id_cible`, `statut`

#### Scenario: Génération même en cas d'échec partiel
- **WHEN** `report.generate()` est appelé dans un bloc `finally` après une erreur
- **THEN** le fichier est écrit avec les entrées accumulées jusqu'à l'erreur

### Requirement: Le rapport est accessible via l'interface web
Le système SHALL servir `output/clone_report.json` via l'endpoint `GET /api/report` de FastAPI, pour affichage dans la page `/report` de l'interface web.

#### Scenario: Accès au rapport via l'API
- **WHEN** un GET sur `/api/report` est effectué après clonage
- **THEN** la réponse JSON contient la liste des entrées du rapport

#### Scenario: Rapport absent
- **WHEN** un GET sur `/api/report` est effectué avant tout clonage
- **THEN** la réponse retourne une liste vide ou un message indiquant que le rapport n'existe pas encore
