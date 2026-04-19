## ADDED Requirements

### Requirement: Remplacement des domaines source dans les contenus textuels
Le système SHALL remplacer toutes les occurrences du domaine `.myshopify.com` source ET du domaine custom source par le domaine cible dans tout contenu textuel (HTML ou JSON) avant écriture sur la boutique cible.

#### Scenario: Remplacement dans une description HTML
- **WHEN** `body_html` contient `https://source.myshopify.com/products/t-shirt`
- **THEN** la valeur écrite contient `https://target.myshopify.com/products/t-shirt`

#### Scenario: Remplacement du domaine custom source
- **WHEN** le contenu contient `https://www.ancienne-boutique.fr/pages/contact`
- **THEN** la valeur écrite contient `https://www.nouvelle-boutique.fr/pages/contact`

#### Scenario: URLs externes non modifiées
- **WHEN** le contenu contient `https://www.google.com/maps`
- **THEN** l'URL est copiée telle quelle sans modification

### Requirement: Remplacement dans les attributs href et src
Le système SHALL détecter et remplacer les domaines dans les attributs `href="..."` et `src="..."` des balises HTML, y compris quand le domaine apparaît dans une URL encodée.

#### Scenario: Attribut href avec domaine source
- **WHEN** HTML contient `<a href="https://source.myshopify.com/collections/all">`
- **THEN** HTML résultant contient `<a href="https://target.myshopify.com/collections/all">`

### Requirement: Initialisation avec les deux domaines source
Le système SHALL être initialisé avec : le domaine `.myshopify.com` source, le domaine custom source (optionnel), et le domaine cible de remplacement.

#### Scenario: Remapping sans domaine custom
- **WHEN** aucun domaine custom source n'est fourni
- **THEN** seul le domaine `.myshopify.com` source est remplacé

### Requirement: Exposer une fonction remap() générique
Le système SHALL exposer une fonction `remap(text: str, source_domains: list[str], target_domain: str) -> str` dans `cloner/domain.py`, utilisable sur n'importe quelle chaîne sans connaissance du format.

#### Scenario: Appel avec une chaîne vide
- **WHEN** la fonction est appelée avec une chaîne vide
- **THEN** elle retourne une chaîne vide sans erreur

#### Scenario: Appel avec None ou valeur non-string
- **WHEN** la fonction est appelée avec `None` ou un type non-string
- **THEN** elle retourne la valeur telle quelle sans lever d'exception

#### Scenario: Remplacement dans un JSON de thème sérialisé
- **WHEN** une valeur JSON contient `"url": "https://source.myshopify.com/collections/all"`
- **THEN** la fonction retourne la valeur avec l'URL remplacée par le domaine cible

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
