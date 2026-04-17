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
