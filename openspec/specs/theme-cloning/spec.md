## Requirements

### Requirement: Identifier le thème actif sur la boutique source
Le système SHALL récupérer la liste complète des thèmes installés sur la boutique source via `GET /admin/api/2024-01/themes.json` et identifier, dans cet inventaire, le thème dont le `role` est `main`.

#### Scenario: Inventaire des thèmes récupéré
- **WHEN** la boutique source expose plusieurs thèmes installés via `themes.json`
- **THEN** le système traite chaque thème de cet inventaire pendant la phase `theme`

#### Scenario: Thème actif trouvé dans l'inventaire
- **WHEN** un thème de l'inventaire a `role: "main"`
- **THEN** le système l'identifie comme unique thème à publier sur la cible en fin de phase

#### Scenario: Aucun thème actif
- **WHEN** aucun thème de l'inventaire n'a `role: "main"`
- **THEN** le système lève une erreur explicite et interrompt la phase thème

---

### Requirement: Créer un nouveau thème vide sur la boutique cible
Le système SHALL créer un thème cible distinct pour chaque thème source installé via `POST /admin/api/2024-01/themes.json`, avec un nom dérivé du thème source et `role: "unpublished"` pendant l'upload.

#### Scenario: Création réussie pour chaque thème source
- **WHEN** l'inventaire source contient N thèmes installés
- **THEN** le système crée N thèmes cibles distincts et enregistre chaque correspondance dans la table de mapping

#### Scenario: Préservation du thème publié
- **WHEN** tous les thèmes source ont été clonés avec succès
- **THEN** le système met à jour uniquement le thème cible correspondant au thème source `main` avec `role: "main"`

#### Scenario: Thèmes non principaux conservés non publiés
- **WHEN** un thème source n'a pas `role: "main"`
- **THEN** le thème cible correspondant reste non publié après la fin de la phase

#### Scenario: Collision de nom sur la cible
- **WHEN** la cible contient déjà un thème portant le même nom qu'un thème source à cloner
- **THEN** le système crée le nouveau thème avec un nom dérivé déterministe permettant de l'identifier sans écraser l'existant

---

### Requirement: Lister et récupérer tous les assets du thème source
Le système SHALL, pour chaque thème source identifié dans l'inventaire, récupérer la liste complète de ses assets via `GET /themes/{id}/assets.json`, puis télécharger chaque asset individuellement.

#### Scenario: Asset textuel (Liquid, JSON, CSS, JS)
- **WHEN** l'API retourne, pour un thème donné, un asset avec un champ `value`
- **THEN** le système utilise la valeur string directement pour le traitement et l'upload vers le thème cible correspondant

#### Scenario: Asset binaire (image, font)
- **WHEN** l'API retourne, pour un thème donné, un asset avec un champ `attachment` (base64)
- **THEN** le système conserve la valeur base64 et l'uploade telle quelle vers le thème cible correspondant

#### Scenario: Asset inaccessible
- **WHEN** la récupération d'un asset d'un thème donné retourne une erreur HTTP (404, 500)
- **THEN** le système log l'erreur dans le rapport, marque l'asset comme `skipped`, et continue avec l'asset suivant du même thème

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
Le système SHALL uploader chaque asset d'un thème source vers le thème cible qui lui correspond via `PUT /admin/api/2024-01/themes/{id}/assets.json` en conservant la même `key` que l'asset source.

#### Scenario: Upload réussi
- **WHEN** l'upload d'un asset d'un thème donné retourne HTTP 200
- **THEN** le système enregistre l'asset comme `success` dans le rapport du thème correspondant

#### Scenario: Erreur d'upload
- **WHEN** l'upload d'un asset d'un thème donné échoue après les retries du client
- **THEN** le système log l'erreur, marque l'asset comme `error` dans le rapport du thème correspondant, et continue

---

### Requirement: Enregistrer les résultats dans le rapport de clonage
Le système SHALL ajouter une entrée dans `clone_report.json` pour chaque thème cloné et pour chaque asset traité, de façon à distinguer clairement le thème source, le thème cible correspondant et le statut du traitement.

#### Scenario: Inventaire de thèmes cloné
- **WHEN** la phase thème se termine avec succès
- **THEN** le rapport contient une entrée de synthèse pour chaque thème source cloné et des entrées d'assets rattachées à chacun de ces thèmes

#### Scenario: Thème principal publié
- **WHEN** le thème source `main` a été cloné puis publié sur la cible
- **THEN** le rapport permet d'identifier quel thème cible correspond au thème publié final

#### Scenario: Échec partiel sur un thème
- **WHEN** un thème donné échoue pendant le traitement de certains assets
- **THEN** le rapport conserve les statuts déjà produits pour ce thème sans masquer ceux des autres thèmes traités avant l'erreur
