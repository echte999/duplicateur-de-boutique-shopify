### Requirement: Persistance de l'état d'avancement par phase
Après chaque phase de clonage réussie, le système SHALL écrire dans `output/clone_state.json` la liste des phases complétées, la boutique source associée, et la date de début du clonage.

#### Scenario: Phase complétée avec succès
- **WHEN** une phase de clonage se termine sans erreur
- **THEN** le système met à jour `clone_state.json` en ajoutant le nom de la phase à la liste `completed_phases`

#### Scenario: Erreur lors d'une phase
- **WHEN** une phase lève une exception ou retourne une erreur
- **THEN** le système NE met PAS à jour `clone_state.json` pour cette phase (elle reste absente de `completed_phases`)

### Requirement: Détection et reprise depuis un état partiel
Au démarrage d'un clonage, le système SHALL détecter la présence d'un `clone_state.json` existant et, si la boutique source correspond, sauter automatiquement les phases déjà complétées.

#### Scenario: État partiel détecté, même boutique source
- **WHEN** `clone_state.json` existe et contient la même boutique source que la configuration courante
- **THEN** le système saute les phases listées dans `completed_phases` et reprend à partir de la première phase non complétée

#### Scenario: État partiel détecté, boutique source différente
- **WHEN** `clone_state.json` existe mais contient une boutique source différente de la configuration courante
- **THEN** le système ignore l'état existant, supprime `clone_state.json` et repart de zéro

#### Scenario: Aucun état partiel
- **WHEN** `clone_state.json` n'existe pas
- **THEN** le système démarre le clonage depuis la première phase sans modification de comportement

### Requirement: Réinitialisation de l'état après succès complet
Après un clonage entièrement réussi (toutes les phases complétées), le système SHALL supprimer `clone_state.json` pour permettre un prochain clonage propre.

#### Scenario: Clonage complet réussi
- **WHEN** toutes les phases se terminent avec succès
- **THEN** le système supprime `clone_state.json`

### Requirement: Robustesse en cas de `clone_state.json` corrompu
Si `clone_state.json` est illisible ou invalide, le système SHALL ignorer l'état et repartir de zéro, en journalisant un avertissement.

#### Scenario: Fichier d'état corrompu
- **WHEN** `clone_state.json` existe mais ne peut pas être parsé (JSON invalide, champs manquants)
- **THEN** le système logue un avertissement, ignore le fichier et démarre depuis la première phase
