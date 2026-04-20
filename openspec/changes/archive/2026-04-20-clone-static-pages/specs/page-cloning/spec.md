## ADDED Requirements

### Requirement: Lecture de toutes les pages statiques de la boutique source
Le système SHALL récupérer toutes les pages de la boutique source via `GET /admin/api/2024-01/pages.json?limit=250` en paginant sur le header `Link: rel="next"` jusqu'à épuisement des résultats.

#### Scenario: Boutique avec plusieurs pages
- **WHEN** la boutique source a 5 pages statiques
- **THEN** les 5 pages sont récupérées avant de passer à la création sur la cible

#### Scenario: Pagination déclenchée
- **WHEN** la boutique source a plus de 250 pages
- **THEN** le système suit le header `Link` pour récupérer toutes les pages en plusieurs requêtes

#### Scenario: Boutique sans pages
- **WHEN** la boutique source n'a aucune page statique
- **THEN** la phase se termine sans erreur avec 0 pages clonées

### Requirement: Création des pages sur la boutique cible
Le système SHALL créer chaque page sur la boutique cible via `POST /admin/api/2024-01/pages.json` en préservant : `title`, `handle`, `body_html` (après remapping de domaine), `published`.

#### Scenario: Création d'une page standard
- **WHEN** la source a une page avec `title="Contact"`, `handle="contact"`, `published=true`
- **THEN** une page est créée sur la cible avec les mêmes champs

#### Scenario: Remapping de domaine dans body_html
- **WHEN** `body_html` contient `https://source.myshopify.com/products/t-shirt`
- **THEN** la page cible est créée avec `https://target.myshopify.com/products/t-shirt` dans son contenu

#### Scenario: Page non publiée
- **WHEN** la page source a `published=false`
- **THEN** la page cible est créée avec `published=false`

### Requirement: Mise à jour de la table de correspondance IDs
Le système SHALL enregistrer dans `id_map` la correspondance `page_id_source → page_id_cible` après chaque création réussie, et persister la table sur disque.

#### Scenario: Correspondance enregistrée
- **WHEN** une page source d'ID `111` est créée sur la cible avec l'ID `999`
- **THEN** `id_map["pages"][111]` vaut `999`

### Requirement: Clonage des métafields des pages
Le système SHALL cloner les métafields de chaque page via GraphQL en utilisant le GID `gid://shopify/OnlineStorePage/{id}`, en ignorant les types de référence croisée et en remappant les types `html`/`url`/`json_string`.

#### Scenario: Page avec métafield simple
- **WHEN** une page source a un métafield `custom.intro` de type `single_line_text_field`
- **THEN** le même métafield est écrit sur la page cible

#### Scenario: Page sans métafields
- **WHEN** une page source n'a aucun métafield
- **THEN** aucune mutation GraphQL `metafieldsSet` n'est effectuée

### Requirement: Inclusion des pages dans le rapport post-clonage
Le système SHALL inclure chaque page clonée dans `clone_report.json` avec les champs `type="page"`, `id_source`, `id_cible`, et `statut` (`ok` ou `error`).

#### Scenario: Page clonée avec succès
- **WHEN** une page est créée sur la cible sans erreur
- **THEN** le rapport contient une entrée `{ type: "page", id_source: X, id_cible: Y, statut: "ok" }`

#### Scenario: Erreur lors de la création d'une page
- **WHEN** l'API cible retourne une erreur pour une page
- **THEN** le rapport contient une entrée avec `statut: "error"` et le message d'erreur, et le clonage continue vers la page suivante
