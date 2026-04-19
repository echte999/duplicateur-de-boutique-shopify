## ADDED Requirements

### Requirement: Remplacer le domaine source par le domaine cible dans tout contenu textuel
Le système SHALL remplacer toutes les occurrences du domaine myshopify source et du domaine custom source par le domaine cible, dans n'importe quelle chaîne de texte passée en entrée (HTML, JSON sérialisé, plain text).

#### Scenario: Remplacement dans une description HTML produit
- **WHEN** une description produit contient `href="https://source.myshopify.com/products/foo"`
- **THEN** la fonction retourne la description avec `href="https://target.myshopify.com/products/foo"`

#### Scenario: Remplacement du domaine custom dans un contenu HTML
- **WHEN** un contenu contient `href="https://www.ancienne-boutique.fr/pages/contact"`
- **THEN** la fonction retourne le contenu avec `href="https://www.nouvelle-boutique.fr/pages/contact"`

#### Scenario: Pas de modification des URLs externes
- **WHEN** un contenu contient `href="https://www.exemple-externe.com/page"`
- **THEN** la fonction retourne le contenu sans modification de cette URL

#### Scenario: Remplacement dans un JSON de thème sérialisé
- **WHEN** une valeur JSON contient `"url": "https://source.myshopify.com/collections/all"`
- **THEN** la fonction retourne la valeur avec l'URL remplacée par le domaine cible

### Requirement: La fonction de remapping est applicable à tout type de contenu textuel
Le système SHALL exposer une fonction `remap(text: str, source_domains: list[str], target_domain: str) -> str` dans `cloner/domain.py`, utilisable sur n'importe quelle chaîne sans connaissance du format.

#### Scenario: Appel avec une chaîne vide
- **WHEN** la fonction est appelée avec une chaîne vide
- **THEN** elle retourne une chaîne vide sans erreur

#### Scenario: Appel avec None ou valeur non-string
- **WHEN** la fonction est appelée avec None ou un type non-string
- **THEN** elle retourne la valeur telle quelle sans lever d'exception

### Requirement: Intégration du remapping dans toutes les phases de clonage
Le système SHALL appliquer `domain.remap()` sur toutes les valeurs textuelles avant écriture sur la boutique cible dans chacune des phases : `products.py`, `collections.py`, `pages.py`, `blogs.py`, `menus.py`, `discounts.py`, et `theme.py`.

#### Scenario: Remapping dans la phase produits
- **WHEN** la phase produits écrit une description ou un métafield de type html/url
- **THEN** le contenu est passé par `domain.remap()` avant l'appel API vers la boutique cible

#### Scenario: Remapping dans les pages statiques
- **WHEN** la phase pages écrit le contenu `body_html` d'une page statique
- **THEN** le contenu est passé par `domain.remap()` avant écriture sur la cible

#### Scenario: Remapping dans les articles de blog
- **WHEN** la phase blogs écrit le contenu `body_html` d'un article
- **THEN** le contenu est passé par `domain.remap()` avant écriture sur la cible

#### Scenario: Remapping dans les menus
- **WHEN** la phase menus écrit les URLs des items de navigation
- **THEN** chaque URL est passée par `domain.remap()` avant écriture sur la cible

#### Scenario: Remapping dans les politiques du site
- **WHEN** la phase discounts/policies écrit le contenu textuel des politiques
- **THEN** le contenu est passé par `domain.remap()` avant écriture sur la cible

#### Scenario: Remapping dans le JSON du thème
- **WHEN** la phase thème écrit `settings_data.json` ou un template JSON
- **THEN** le JSON entier est passé par `domain.remap()` avant upload
