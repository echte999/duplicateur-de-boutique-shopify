### Requirement: Clonage des blogs (collections de blog)
Le système SHALL récupérer tous les blogs de la boutique source via `GET /blogs.json?limit=250` et créer les blogs correspondants sur la boutique cible via `POST /blogs.json`. L'ID source et l'ID cible SHALL être enregistrés dans la table de correspondance (`blog_id`).

#### Scenario: Clonage d'un blog simple
- **WHEN** la boutique source contient un blog "Actualités" avec `commentable: "moderate"`
- **THEN** un blog "Actualités" est créé sur la cible avec les mêmes attributs, et les IDs source/cible sont mappés

#### Scenario: Boutique sans blogs
- **WHEN** la boutique source n'a aucun blog
- **THEN** la phase se termine sans erreur et aucun appel de création n'est effectué

### Requirement: Clonage des articles de blog
Le système SHALL récupérer tous les articles de chaque blog source via `GET /blogs/{id}/articles.json?limit=250` et les créer sur la boutique cible via `POST /blogs/{target_blog_id}/articles.json`, en utilisant l'ID blog remappé. L'ID article source et cible SHALL être enregistrés dans la table de correspondance (`article_id`).

Le contenu HTML des articles SHALL être passé par le remapping de domaine avant écriture sur la cible.

#### Scenario: Article dans un blog existant
- **WHEN** un blog source contient 3 articles publiés
- **THEN** 3 articles sont créés dans le blog cible correspondant (ID remappé), avec le même titre, contenu, auteur et statut

#### Scenario: Article avec lien interne dans le corps
- **WHEN** un article contient `href="https://source.myshopify.com/pages/contact"`
- **THEN** le lien est remappé vers le domaine cible avant écriture

#### Scenario: Article brouillon
- **WHEN** un article source a `published: false`
- **THEN** l'article est créé en brouillon sur la cible (`published: false`)

### Requirement: Re-upload des images mise en avant des articles
Le système SHALL télécharger l'image mise en avant de chaque article source (`image.src`) vers le cache local `tmp_images/article_{id}/`, puis la re-uploader vers la boutique cible. Si l'image est déjà présente dans le cache local, elle ne SHALL pas être re-téléchargée.

#### Scenario: Article avec image mise en avant
- **WHEN** un article source a une image mise en avant
- **THEN** l'image est téléchargée dans le cache local, re-uploadée vers la cible, et l'URL est mise à jour dans le payload de création

#### Scenario: Article sans image mise en avant
- **WHEN** un article source n'a pas d'image mise en avant (`image` est null)
- **THEN** aucun téléchargement n'est tenté et l'article est créé sans image

#### Scenario: Image déjà dans le cache
- **WHEN** une image a déjà été téléchargée lors d'un clonage précédent interrompu
- **THEN** l'image est lue depuis le cache local sans nouveau téléchargement
