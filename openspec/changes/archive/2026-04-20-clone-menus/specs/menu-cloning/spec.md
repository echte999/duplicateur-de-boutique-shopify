## ADDED Requirements

### Requirement: Récupération de tous les menus source
Le système SHALL récupérer tous les menus de la boutique source via `GET /admin/api/2023-10/menus.json` et itérer sur l'ensemble des menus retournés (principale, footer, custom).

#### Scenario: Boutique avec plusieurs menus
- **WHEN** la boutique source contient un menu principal, un footer, et un menu custom
- **THEN** les 3 menus sont récupérés et traités

#### Scenario: Boutique sans menus
- **WHEN** la boutique source n'a aucun menu
- **THEN** la phase se termine sans erreur et aucun appel de création n'est effectué

### Requirement: Création des menus sur la cible
Le système SHALL créer chaque menu sur la boutique cible via `POST /admin/api/2023-10/menus.json` avec le même `title` et `handle`. Si le `POST` échoue avec HTTP 422 (handle déjà existant), le système SHALL tenter une mise à jour via `PUT /admin/api/2023-10/menus/{id}.json`. L'ID source et l'ID cible SHALL être enregistrés dans la table de correspondance (`menu_id`).

#### Scenario: Création d'un nouveau menu
- **WHEN** la boutique cible ne contient pas de menu avec le handle `main-menu`
- **THEN** le menu est créé avec `POST`, son ID est mappé source→cible

#### Scenario: Handle déjà existant sur la cible
- **WHEN** la boutique cible contient déjà un menu avec le handle `footer`
- **THEN** le système récupère l'ID existant et met à jour le menu via `PUT`

### Requirement: Remapping des subject_id des items de menu
Pour chaque item de menu dont le `type` est `collection`, `product`, `page`, ou `article`, le système SHALL remplacer le `subject_id` par l'ID cible correspondant dans `id_map`. Si aucune correspondance n'est trouvée, l'item SHALL être converti en `type: frontpage` et l'incident SHALL être loggé dans le rapport.

#### Scenario: Item pointant vers une collection existante
- **WHEN** un item de menu a `type: "collection"` et `subject_id: 123` (mappé vers 456)
- **THEN** l'item créé sur la cible a `subject_id: 456`

#### Scenario: Item orphelin (ressource non clonée)
- **WHEN** un item de menu pointe vers un `subject_id` absent de `id_map`
- **THEN** l'item est converti en `type: frontpage` et l'incident est loggé

### Requirement: Remapping des URLs dans les items http
Pour chaque item de menu dont le `type` est `http`, le système SHALL passer l'`url` par la fonction `domain.remap()` pour remplacer le domaine source par le domaine cible.

#### Scenario: Item http avec URL interne
- **WHEN** un item a `type: "http"` et `url: "https://source.myshopify.com/pages/contact"`
- **THEN** l'URL est remappée vers `https://cible.myshopify.com/pages/contact` avant création

#### Scenario: Item http avec URL externe
- **WHEN** un item a `type: "http"` et `url: "https://example.com"`
- **THEN** l'URL n'est pas modifiée

### Requirement: Préservation de la structure hiérarchique
Le système SHALL préserver les items enfants imbriqués de chaque menu en transmettant la liste `items` complète (avec sous-items) dans le payload de création. L'arborescence entière SHALL être créée en une seule requête.

#### Scenario: Menu avec sous-items
- **WHEN** un item de menu principal a 3 sous-items (collections enfants)
- **THEN** les 3 sous-items sont présents dans le menu cible avec les IDs remappés
