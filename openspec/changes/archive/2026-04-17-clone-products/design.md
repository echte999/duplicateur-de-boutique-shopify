## Context

Le projet démarre de zéro. Aucun code n'existe encore. Cette première phase pose les fondations partagées par toutes les phases suivantes : client HTTP, table de correspondance IDs, remapping de domaine. Elle implémente ensuite le clonage des produits, ressource sans dépendances entrantes, qui doit être terminée avant collections, menus et thème.

L'API Shopify impose un rate limit REST (bucket de 40 requêtes, récupération à 2/s) et un rate limit GraphQL basé sur le coût de chaque requête. Les boutiques peuvent contenir des centaines de produits avec plusieurs images chacun.

## Goals / Non-Goals

**Goals:**
- Cloner fidèlement chaque produit (titre, description HTML, prix, variantes, statut publié/archivé, images)
- Cloner le métafield `caracteristiques` via GraphQL
- Remapper les domaines source dans les descriptions HTML
- Maintenir une table `id_source → id_cible` persistée sur disque après chaque produit
- Mettre en cache les images localement pour éviter les re-téléchargements
- Respecter les rate limits sans échec silencieux

**Non-Goals:**
- Clonage des collections, menus, thème, pages, blogs (phases ultérieures)
- Tous les métafields autres que `caracteristiques` (V1)
- Interface web (phase séparée)
- Rapport post-clonage (phase séparée)

## Decisions

### Client HTTP unique partagé (`cloner/client.py`)

**Décision** : Un seul client `httpx.AsyncClient` instancié une fois, injecté dans toutes les phases via paramètre.

**Pourquoi** : Partager les connexions TCP réduit la latence. Centraliser le rate limiting dans un seul endroit évite la duplication. Alternative rejetée : instancier un client par phase → connections TCP multipliées, semaphore non partagé.

### `asyncio.Semaphore` pour le rate limiting REST

**Décision** : Semaphore de 20 (moitié du bucket) + retry avec backoff exponentiel (1s, 2s, 4s, max 3 tentatives) sur erreur 429.

**Pourquoi** : Le bucket de 40 se récupère à 2/s. Garder 20 slots libres donne une marge de sécurité sans bloquer le throughput. Alternative rejetée : compteur manuel du bucket → complexité inutile, httpx ne lit pas les headers `X-Shopify-Shop-Api-Call-Limit` automatiquement.

### Pagination REST par page de 250

**Décision** : Récupérer les produits par pages de 250 (max Shopify) avec `page_info` pour la pagination basée sur curseur.

**Pourquoi** : Minimise le nombre d'appels API. La pagination par `page` (ancienne) est dépréciée par Shopify. Alternative rejetée : pagination par `page` entier → dépréciée, résultats incohérents sur grandes boutiques.

### Images : vérification cache avant téléchargement

**Décision** : Avant tout téléchargement, vérifier si `tmp_images/{product_id}/{filename}` existe déjà. Si oui, skip le téléchargement.

**Pourquoi** : Permet de relancer un clone interrompu sans tout re-télécharger. Le nom de fichier est extrait de l'URL CDN Shopify (dernier segment avant `?`).

### GraphQL pour les métafields uniquement

**Décision** : REST pour tout sauf les métafields, GraphQL pour lire/écrire `caracteristiques`.

**Pourquoi** : L'API REST expose les métafields produit via `GET /products/{id}/metafields.json` mais l'écriture est moins directe. GraphQL permet batch sur plusieurs objets (utile pour V1). Décision cohérente avec l'architecture définie.

### Table de correspondance persistée après chaque produit

**Décision** : Sauvegarder `id_map.json` sur disque après chaque produit créé avec succès (pas seulement à la fin de la phase).

**Pourquoi** : Si le clone s'interrompt au milieu, la table reste exploitable pour les phases suivantes ou pour reprendre. Coût : une écriture disque par produit, négligeable.

## Risks / Trade-offs

**[Rate limit GraphQL]** → Le coût d'une requête de métafields dépend du nombre de métafields. Sur boutiques avec de nombreux métafields custom, le budget peut s'épuiser rapidement. Mitigation : lire `extensions.cost.actualQueryCost` dans chaque réponse, pause de `throttleStatus.restoreRate` ms si `currentlyAvailable < requestedQueryCost`.

**[Images volumineux]** → Une boutique avec 500 produits × 5 images × 2 Mo = 5 Go de stockage temporaire. Mitigation : nettoyage manuel documenté (V2 automatisera). Pas de limite de taille imposée en MVP.

**[IDs Shopify GID vs numérique]** → GraphQL utilise des Global IDs (`gid://shopify/Product/123`) tandis que REST utilise des entiers. La table de correspondance stocke les IDs numériques (REST). Lors des appels GraphQL, convertir : `gid://shopify/Product/{id}`.

**[Variantes sans prix]** → Shopify peut avoir des variantes sans prix défini. Le clone copie `null` tel quel ; Shopify cible accepte ce cas.

## Migration Plan

Pas de migration nécessaire (nouveau projet from scratch). Lancer avec :
```
pip install httpx fastapi uvicorn
python main.py
```

## Open Questions

- Faut-il copier le statut `draft` / `active` / `archived` tel quel, ou forcer `draft` le temps du clonage pour éviter que les produits soient visibles avant que les collections soient prêtes ? → Décision : copier le statut tel quel (usage personnel, boutique cible non publique pendant le clonage).
