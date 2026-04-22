### Requirement: Sélection des phases avant lancement
L'utilisateur SHALL pouvoir choisir, via l'interface web, quelles phases de clonage exécuter avant de lancer le clonage. Les phases disponibles sont : `products`, `collections`, `pages`, `blogs`, `menus`, `policies`, `discounts`, `theme`.

#### Scenario: Toutes les phases cochées par défaut
- **WHEN** l'utilisateur ouvre l'interface web
- **THEN** toutes les cases à cocher de phases sont cochées par défaut

#### Scenario: Lancement avec sélection partielle
- **WHEN** l'utilisateur décoche certaines phases et clique sur "Lancer le clonage"
- **THEN** seules les phases cochées sont exécutées, dans l'ordre de dépendance habituel

#### Scenario: Aucune phase sélectionnée
- **WHEN** l'utilisateur décoche toutes les phases et clique sur "Lancer le clonage"
- **THEN** le système refuse le lancement et affiche un message d'erreur demandant de sélectionner au moins une phase

### Requirement: Mémorisation de la sélection
Le système SHALL sauvegarder la dernière sélection de phases dans `config.json` sous la clé `selected_phases`, et pré-remplir le formulaire avec cette sélection au prochain chargement.

#### Scenario: Rechargement après sélection partielle
- **WHEN** l'utilisateur a lancé un clonage avec une sélection partielle puis recharge l'interface
- **THEN** les mêmes phases que lors du dernier lancement sont pré-cochées

#### Scenario: Aucune sélection sauvegardée
- **WHEN** `config.json` ne contient pas de clé `selected_phases`
- **THEN** toutes les phases sont cochées par défaut

### Requirement: Avertissement de dépendances manquantes
Si l'utilisateur sélectionne une phase qui dépend d'une autre phase non sélectionnée, le système SHALL afficher un avertissement visuel (non bloquant) dans l'UI.

#### Scenario: Collections sélectionnées sans produits
- **WHEN** l'utilisateur coche "Collections" mais décoche "Produits"
- **THEN** l'interface affiche un avertissement indiquant que les collections dépendent des produits pour le remapping des IDs

#### Scenario: Menus sélectionnés sans collections ni pages
- **WHEN** l'utilisateur coche "Menus" mais décoche "Collections" et "Pages"
- **THEN** l'interface affiche un avertissement indiquant que les menus référencent des collections et des pages

### Requirement: Transmission de la sélection au backend
L'UI SHALL envoyer la liste des phases sélectionnées dans le body du POST `/api/start` sous la clé `phases` (liste de strings).

#### Scenario: Envoi de la sélection
- **WHEN** l'utilisateur clique sur "Lancer le clonage" avec une sélection valide
- **THEN** le POST `/api/start` contient `{"phases": ["products", "theme"]}` (exemple) et le backend démarre le clonage avec uniquement ces phases
