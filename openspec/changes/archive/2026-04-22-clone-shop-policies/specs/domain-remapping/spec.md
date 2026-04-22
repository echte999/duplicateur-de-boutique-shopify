## ADDED Requirements

### Requirement: Remplacement du nom de la boutique source dans les contenus textuels
Le système SHALL remplacer les occurrences exactes du nom de la boutique source (tel que retourné par `GET /shop.json` champ `name`) par le nom de la boutique cible dans tout contenu textuel passé à `domain.remap()`.

#### Scenario: Contenu contenant le nom exact de la boutique source
- **WHEN** le `body` HTML d'une politique contient le nom de la boutique source
- **THEN** la fonction `remap()` remplace ce nom par le nom de la boutique cible

#### Scenario: Contenu contenant un mot qui ressemble au nom de boutique mais n'est pas exact
- **WHEN** le contenu contient une sous-chaîne qui coïncide partiellement avec le nom de boutique
- **THEN** seul le nom exact (case-sensitive) est remplacé, les autres occurrences sont laissées intactes

#### Scenario: Nom de boutique source non fourni
- **WHEN** `remap()` est appelé sans nom de boutique source
- **THEN** seuls les domaines sont remplacés, sans erreur

## MODIFIED Requirements

### Requirement: Initialisation avec les deux domaines source
Le système SHALL être initialisé avec : le domaine `.myshopify.com` source, le domaine custom source (optionnel), le domaine cible de remplacement, le nom de la boutique source (optionnel), et le nom de la boutique cible (optionnel).

#### Scenario: Remapping sans domaine custom
- **WHEN** aucun domaine custom source n'est fourni
- **THEN** seul le domaine `.myshopify.com` source est remplacé

#### Scenario: Remapping sans nom de boutique
- **WHEN** aucun nom de boutique source n'est fourni
- **THEN** le remapping se limite aux domaines, sans erreur

### Requirement: Intégration du remapping dans toutes les phases de clonage
Le système SHALL appliquer `domain.remap()` sur toutes les valeurs textuelles avant écriture sur la boutique cible dans chacune des phases : `products.py`, `collections.py`, `pages.py`, `blogs.py`, `menus.py`, `policies.py`, `discounts.py`, et `theme.py`.

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
- **WHEN** la phase policies écrit le `body` HTML d'une politique
- **THEN** le contenu (domaines et nom de boutique) est passé par `domain.remap()` avant écriture sur la cible

#### Scenario: Remapping dans le JSON du thème
- **WHEN** la phase thème écrit `settings_data.json` ou un template JSON
- **THEN** le JSON entier est passé par `domain.remap()` avant upload
