## 1. Structure de base du projet

- [x] 1.1 Créer `cloner/__init__.py` (vide)
- [x] 1.2 Créer `cloner/phases/__init__.py` (vide)
- [x] 1.3 Créer les répertoires `output/` et `tmp_images/` (avec `.gitkeep`)
- [x] 1.4 Créer `requirements.txt` avec `httpx`, `fastapi`, `uvicorn`

## 2. Client HTTP Shopify (`cloner/client.py`)

- [x] 2.1 Définir les exceptions `ShopifyAPIError` et `ShopifyRateLimitError`
- [x] 2.2 Implémenter la classe `ShopifyClient` avec `httpx.AsyncClient`, headers d'auth et URL de base
- [x] 2.3 Ajouter méthodes `get_source`, `post_source`, `get_target`, `post_target` avec `asyncio.Semaphore(20)`
- [x] 2.4 Implémenter le retry backoff exponentiel (1s, 2s, 4s) sur HTTP 429
- [x] 2.5 Implémenter `graphql_source` et `graphql_target` avec vérification du budget de coût GraphQL

## 3. Table de correspondance IDs (`cloner/mapping.py`)

- [x] 3.1 Implémenter la classe `IDMapping` avec chargement depuis `output/id_map.json` au démarrage
- [x] 3.2 Implémenter `set(resource_type, source_id, target_id)` avec sauvegarde disque immédiate
- [x] 3.3 Implémenter `get(resource_type, source_id)` avec `KeyError` si absent
- [x] 3.4 Initialiser la structure vide avec toutes les clés de type (`product`, `variant`, `collection`, etc.)

## 4. Remapping de domaine (`cloner/domain.py`)

- [x] 4.1 Implémenter la classe `DomainRemapper` initialisée avec domaine source myshopify, domaine custom source (optionnel) et domaine cible
- [x] 4.2 Implémenter `remap(text)` qui remplace les deux domaines source par le domaine cible
- [x] 4.3 Couvrir les cas : URLs brutes, attributs `href="..."`, attributs `src="..."`

## 5. Cache images (`cloner/image_cache.py`)

- [x] 5.1 Implémenter `download_image(url, product_id)` qui retourne le chemin local (skip si déjà en cache)
- [x] 5.2 Extraire le `filename` depuis l'URL CDN Shopify (segment avant `?`)
- [x] 5.3 Créer `tmp_images/{product_id}/` automatiquement si absent

## 6. Clonage des produits (`cloner/phases/products.py`)

- [x] 6.1 Implémenter `fetch_all_products(client)` avec pagination par curseur (pages de 250)
- [x] 6.2 Implémenter `clone_product(client, mapping, remapper, image_cache, product)` :
    - Copier `title`, `body_html` (remappé), `vendor`, `product_type`, `status`, `tags`
    - Inclure les variantes avec `price`, `sku`, `option1/2/3`, `inventory_policy`
- [x] 6.3 Implémenter `clone_product_images(client, mapping, image_cache, source_product_id, target_product_id, images)` : download + upload + préservation des positions
- [x] 6.4 Implémenter `fetch_caracteristiques_metafield(client, product_id)` via GraphQL
- [x] 6.5 Implémenter `write_caracteristiques_metafield(client, target_product_id, value, type)` via GraphQL
- [x] 6.6 Implémenter `clone_all_products(client, mapping, remapper)` qui orchestre les étapes 6.1→6.5 pour chaque produit

## 7. Point d'entrée minimal (`main.py`)

- [x] 7.1 Créer `main.py` avec une fonction `run_clone(config)` qui instancie client, mapping, remapper et appelle `clone_all_products`
- [x] 7.2 Charger la config depuis `config.json` (tokens, domaines source et cible)
- [x] 7.3 Ajouter un `if __name__ == "__main__"` qui lance `asyncio.run(run_clone(config))`
