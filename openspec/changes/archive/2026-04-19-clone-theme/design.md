## Context

Les phases produits et collections sont complètes. Il reste à cloner le thème actif, qui contient des fichiers Liquid, des assets binaires (images, fonts, JS/CSS) et des fichiers JSON de configuration (`settings_data.json`, templates de sections). Certains de ces fichiers JSON contiennent des références à des IDs Shopify (produits, collections) qui ont changé entre boutiques et doivent être remappés.

L'API Shopify REST expose les thèmes via :
- `GET /admin/api/2024-01/themes.json` — liste les thèmes
- `GET /admin/api/2024-01/themes/{id}/assets.json` — liste tous les assets
- `GET /admin/api/2024-01/themes/{id}/assets.json?asset[key]=<key>` — télécharge un asset
- `PUT /admin/api/2024-01/themes/{id}/assets.json` — crée ou met à jour un asset

Les assets sont soit textuels (Liquid, JSON, CSS, JS) soit binaires (images, fonts). L'API retourne les textuels comme `value` (string), les binaires comme `attachment` (base64).

## Goals / Non-Goals

**Goals:**
- Cloner le thème actif de la boutique source vers la boutique cible
- Injecter les IDs remappés dans `settings_data.json` et les templates JSON
- Appliquer le remapping de domaine sur tous les contenus textuels
- Conserver les assets binaires fidèlement (base64 round-trip)
- Intégrer la phase dans l'orchestrateur principal

**Non-Goals:**
- Cloner les thèmes non-actifs (V2)
- Modifier la structure ou le design du thème
- Tester le rendu visuel du thème cloné

## Decisions

### 1. Créer un nouveau thème sur la cible plutôt que modifier le thème existant

**Décision** : Créer un nouveau thème vide sur la cible via `POST /themes`, puis uploader tous les assets dedans.

**Pourquoi** : Modifier le thème actif en place risque de rendre la boutique cible inutilisable pendant le clonage. Créer un thème séparé permet de publier (`role: main`) seulement à la fin, une fois tous les assets uploadés.

**Alternative** : Overwrite direct du thème actif — rejeté car l'upload partiel laisserait une boutique cassée.

### 2. Remapping des IDs dans le JSON du thème par regex sur les Global IDs Shopify

**Décision** : Parcourir récursivement les valeurs string dans les JSON du thème. Chercher les patterns `gid://shopify/(Product|Collection)/\d+` et les IDs numériques bruts via la table `id_map`.

**Pourquoi** : Le JSON des sections Shopify peut contenir des IDs sous forme de GID GraphQL (`gid://shopify/Product/123`) ou d'entier brut. La table `id_map` (construite en phases 1 et 2) contient les deux formes.

**Alternative** : Parser le JSON section par section en connaissant le schéma — trop fragile car le schéma varie par thème.

### 3. Upload séquentiel des assets (pas de parallélisme)

**Décision** : Uploader les assets un par un, en respectant le rate limiting existant du `client.py`.

**Pourquoi** : L'API Shopify impose un bucket de 40 requêtes REST. Les thèmes ont souvent 200-500 assets. Le semaphore du client gère déjà la concurrence — inutile d'ajouter de la complexité.

## Risks / Trade-offs

- **Thème avec assets lourds** → Upload long (plusieurs minutes). Mitigation : logs de progression asset par asset.
- **Asset inaccessible sur la source** (asset listé mais supprimé) → L'API retourne 404. Mitigation : attraper l'erreur, logger dans le rapport, continuer.
- **IDs dans des structures JSON imbriquées inconnues** → Remapping partiel possible. Mitigation : parcours récursif de tout le JSON, pas seulement les champs connus.
- **Thème avec des blocks `{% schema %}` Liquid** → Les schémas Liquid embedded ne sont pas du JSON pur. Mitigation : appliquer uniquement le remapping de domaine sur les fichiers `.liquid`, pas le remapping d'IDs (les IDs dans les schémas Liquid sont des defaults de template, pas des références réelles).
