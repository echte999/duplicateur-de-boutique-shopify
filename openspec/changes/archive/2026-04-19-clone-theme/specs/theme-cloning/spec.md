## ADDED Requirements

### Requirement: Identifier le thème actif sur la boutique source
Le système SHALL récupérer le thème dont le `role` est `main` sur la boutique source via `GET /admin/api/2024-01/themes.json`.

#### Scenario: Thème actif trouvé
- **WHEN** la boutique source a un thème avec `role: "main"`
- **THEN** le système utilise son ID pour toutes les opérations de récupération d'assets

#### Scenario: Aucun thème actif
- **WHEN** aucun thème n'a `role: "main"` sur la boutique source
- **THEN** le système lève une erreur explicite et interrompt la phase thème

---

### Requirement: Créer un nouveau thème vide sur la boutique cible
Le système SHALL créer un nouveau thème sur la boutique cible via `POST /admin/api/2024-01/themes.json` avec un nom identique au thème source et `role: "unpublished"` pendant l'upload.

#### Scenario: Création réussie
- **WHEN** le thème source est identifié
- **THEN** le système crée un thème cible vide et enregistre son ID dans la table de correspondance

#### Scenario: Activation en fin de phase
- **WHEN** tous les assets ont été uploadés avec succès
- **THEN** le système met à jour le thème cible avec `role: "main"` via `PUT /admin/api/2024-01/themes/{id}.json`

---

### Requirement: Lister et récupérer tous les assets du thème source
Le système SHALL récupérer la liste complète des assets via `GET /themes/{id}/assets.json`, puis télécharger chaque asset individuellement.

#### Scenario: Asset textuel (Liquid, JSON, CSS, JS)
- **WHEN** l'API retourne un asset avec un champ `value`
- **THEN** le système utilise la valeur string directement pour le traitement et l'upload

#### Scenario: Asset binaire (image, font)
- **WHEN** l'API retourne un asset avec un champ `attachment` (base64)
- **THEN** le système conserve la valeur base64 et l'uploade telle quelle sur la cible

#### Scenario: Asset inaccessible
- **WHEN** la récupération d'un asset retourne une erreur HTTP (404, 500)
- **THEN** le système log l'erreur dans le rapport, marque l'asset comme `skipped`, et continue avec l'asset suivant

---

### Requirement: Appliquer le remapping de domaine sur les assets textuels
Le système SHALL appliquer le remapping de domaine (via `cloner/domain.py`) sur le contenu de tous les assets textuels avant upload vers la cible.

#### Scenario: Domaine source présent dans un fichier Liquid
- **WHEN** un fichier `.liquid` contient une URL référençant le domaine source
- **THEN** le système remplace le domaine source par le domaine cible avant upload

#### Scenario: Domaine source présent dans settings_data.json
- **WHEN** `settings_data.json` contient une valeur string avec le domaine source
- **THEN** le système remplace le domaine source par le domaine cible avant upload

---

### Requirement: Injecter les IDs remappés dans les fichiers JSON du thème
Le système SHALL parcourir récursivement les fichiers JSON du thème (templates et `settings_data.json`) et remplacer tout GID Shopify ou ID numérique correspondant à une entrée de la table `id_map`.

#### Scenario: GID produit dans settings_data.json
- **WHEN** `settings_data.json` contient une valeur `"gid://shopify/Product/123"` et que l'ID `123` est dans la table `id_map`
- **THEN** le système remplace la valeur par le GID cible correspondant avant upload

#### Scenario: GID collection dans un template JSON
- **WHEN** un fichier `templates/*.json` contient une valeur `"gid://shopify/Collection/456"` et que l'ID `456` est dans la table `id_map`
- **THEN** le système remplace la valeur par le GID cible correspondant avant upload

#### Scenario: ID numérique dans le JSON du thème
- **WHEN** une valeur string dans un JSON de thème correspond exactement à un ID source de la table `id_map`
- **THEN** le système remplace la valeur par l'ID cible correspondant (sous forme de string)

#### Scenario: Fichier Liquid (non-JSON)
- **WHEN** l'asset est un fichier `.liquid`
- **THEN** le système applique uniquement le remapping de domaine, pas le remapping d'IDs

---

### Requirement: Uploader chaque asset vers le thème cible
Le système SHALL uploader chaque asset (modifié ou non) vers le thème cible via `PUT /admin/api/2024-01/themes/{id}/assets.json` en conservant la même `key` que l'asset source.

#### Scenario: Upload réussi
- **WHEN** l'upload d'un asset retourne HTTP 200
- **THEN** le système enregistre l'asset comme `success` dans le rapport

#### Scenario: Erreur d'upload
- **WHEN** l'upload d'un asset échoue après les retries du client
- **THEN** le système log l'erreur, marque l'asset comme `error` dans le rapport, et continue

---

### Requirement: Enregistrer les résultats dans le rapport de clonage
Le système SHALL ajouter une entrée dans `clone_report.json` pour le thème et pour chaque asset traité, avec les champs `type`, `key`, `statut` (success / skipped / error).

#### Scenario: Phase thème terminée
- **WHEN** tous les assets ont été traités
- **THEN** le rapport contient une entrée par asset avec son statut et une entrée pour le thème global indiquant le nombre d'assets uploadés
