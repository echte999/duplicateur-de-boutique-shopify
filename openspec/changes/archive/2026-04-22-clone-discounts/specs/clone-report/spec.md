## MODIFIED Requirements

### Requirement: Accumuler les entrées de rapport pendant le clonage
Le système SHALL permettre d'ajouter une entrée au rapport via `report.add_entry(type, src_id, tgt_id, status)` depuis n'importe quelle phase de clonage, y compris la phase `discounts` qui produit des entrées de type `price_rule`.

#### Scenario: Ajout d'une entrée produit réussie
- **WHEN** un produit est cloné avec succès
- **THEN** `report.add_entry("product", 1234, 9876, "ok")` ajoute l'entrée sans erreur

#### Scenario: Ajout d'une entrée en échec
- **WHEN** une ressource échoue à être clonée
- **THEN** `report.add_entry("product", 1234, None, "error")` enregistre l'échec avec `tgt_id` null

#### Scenario: Ajout d'une entrée price_rule réussie
- **WHEN** une price rule est clonée avec succès
- **THEN** `report.add_entry("price_rule", src_id, tgt_id, "ok")` ajoute l'entrée sans erreur

#### Scenario: Ajout d'une entrée price_rule en échec
- **WHEN** la création d'une price rule échoue
- **THEN** `report.add_entry("price_rule", src_id, None, "error: ...")` enregistre l'échec
