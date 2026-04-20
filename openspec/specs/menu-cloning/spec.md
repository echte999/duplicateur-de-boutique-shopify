### Requirement: Récupération de tous les menus source
Le système SHALL récupérer tous les menus de la boutique source via l'API GraphQL (`menus` query avec pagination) et itérer sur l'ensemble des menus retournés (principale, footer, custom).

#### Scenario: Boutique avec plusieurs menus
- **WHEN** la boutique source contient un menu principal, un footer, et un menu custom
- **THEN** les 3 menus sont récupérés et traités

#### Scenario: Boutique sans menus
- **WHEN** la boutique source n'a aucun menu
- **THEN** la phase se termine sans erreur et aucun appel de création n'est effectué

### Requirement: Création et mise à jour des menus sur la cible
Le système SHALL créer chaque menu sur la boutique cible via la mutation GraphQL `menuCreate` avec le même `title` et `handle`. Si un menu avec le même handle existe déjà sur la cible, le système SHALL le mettre à jour via `menuUpdate` (avec `MenuItemUpdateInput`). Si `menuUpdate` échoue et que le menu est un menu par défaut non supprimable, la phase SHALL loguer un avertissement et passer au menu suivant sans erreur fatale. L'ID source et l'ID cible SHALL être enregistrés dans la table de correspondance (`menu_id`).

#### Scenario: Création d'un nouveau menu
- **WHEN** la boutique cible ne contient pas de menu avec le handle `main-menu`
- **THEN** le menu est créé via `menuCreate`, son ID est mappé source→cible

#### Scenario: Handle déjà existant sur la cible
- **WHEN** la boutique cible contient déjà un menu avec le handle `footer`
- **THEN** le système tente `menuUpdate` ; si le menu est non supprimable et la mise à jour échoue, un avertissement est loggé

### Requirement: Remapping des resourceId des items de menu
Pour chaque item de menu dont le `type` est `COLLECTION`, `PRODUCT`, `PAGE`, `BLOG`, ou `ARTICLE`, le système SHALL remplacer le `resourceId` (GID Shopify) par le GID cible correspondant construit depuis `id_map`. Si aucune correspondance n'est trouvée, l'item SHALL être converti en `type: FRONTPAGE` et l'incident SHALL être loggé dans le rapport. Les items de type `CustomerAccountPage` SHALL être passés tels quels (pages système identiques sur toutes les boutiques).

#### Scenario: Item pointant vers une collection existante
- **WHEN** un item de menu a `type: "COLLECTION"` et `resourceId: "gid://shopify/Collection/123"` (mappé vers 456)
- **THEN** l'item créé sur la cible a `resourceId: "gid://shopify/Collection/456"`

#### Scenario: Item orphelin (ressource non clonée)
- **WHEN** un item de menu pointe vers un `resourceId` absent de `id_map`
- **THEN** si une `url` est disponible, l'item est converti en `type: HTTP` avec l'URL remappée ; sinon converti en `type: FRONTPAGE` et l'incident est loggé

### Requirement: Remapping des items SHOP_POLICY
Pour chaque item de menu dont le `type` est `SHOP_POLICY`, le système SHALL utiliser l'`url` de l'item source (ex: `/policies/refund-policy`) comme lien `HTTP` avec remapping de domaine, car les GIDs de politiques diffèrent entre boutiques et ne sont pas accessibles via les APIs standard.

#### Scenario: Item politique de remboursement
- **WHEN** un item a `type: "SHOP_POLICY"` et `url: "https://source.myshopify.com/policies/refund-policy"`
- **THEN** l'item est créé avec `type: "HTTP"` et `url: "https://cible.myshopify.com/policies/refund-policy"`

### Requirement: Remapping des URLs dans les items HTTP
Pour chaque item de menu dont le `type` est `HTTP`, le système SHALL passer l'`url` par la fonction `domain.remap()` pour remplacer le domaine source par le domaine cible.

#### Scenario: Item http avec URL interne
- **WHEN** un item a `type: "HTTP"` et `url: "https://source.myshopify.com/pages/contact"`
- **THEN** l'URL est remappée vers `https://cible.myshopify.com/pages/contact` avant création

#### Scenario: Item http avec URL externe
- **WHEN** un item a `type: "HTTP"` et `url: "https://example.com"`
- **THEN** l'URL n'est pas modifiée

### Requirement: Préservation de la structure hiérarchique
Le système SHALL préserver les items enfants imbriqués de chaque menu en transmettant la liste `items` complète (avec sous-items) dans le payload de création. L'arborescence entière SHALL être créée en une seule requête.

#### Scenario: Menu avec sous-items
- **WHEN** un item de menu principal a 3 sous-items (collections enfants)
- **THEN** les 3 sous-items sont présents dans le menu cible avec les GIDs remappés
