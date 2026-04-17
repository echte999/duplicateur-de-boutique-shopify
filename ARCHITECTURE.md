# Architecture — Copieur de boutique Shopify

## Stack technique

| Couche | Choix | Rôle |
|---|---|---|
| Langage | Python 3.11+ | |
| Client HTTP | `httpx` | Appels API Shopify, async, multipart upload |
| Serveur web | `fastapi` + `uvicorn` | Interface web locale, async-natif |
| Frontend | HTML + JS vanilla | Formulaire de config, suivi de progression |
| Stdlib | `asyncio`, `json`, `csv`, `pathlib`, `re` | Rate limiting, persistance, remapping |

**Dépendances externes : 3** (`httpx`, `fastapi`, `uvicorn`)

---

## API Shopify

Mix REST et GraphQL selon la ressource :

| API | Utilisée pour |
|---|---|
| **REST** | Produits, collections, pages, articles de blog, menus, politiques, réductions, thème |
| **GraphQL** | Métafields sur tous types d'objets (produits, variantes, collections, pages) |

L'API GraphQL est nécessaire pour les métafields car elle permet de les lire et écrire sur plusieurs types d'objets en une seule requête, ce que l'API REST ne supporte pas complètement.

---

## Structure des fichiers

```
shopify-cloner/
├── main.py                  # App FastAPI — routes et état du clone
├── config.json              # Tokens API sauvegardés (jamais commité)
├── cloner/
│   ├── client.py            # Client httpx + rate limiting
│   ├── mapping.py           # Table de correspondance IDs
│   ├── domain.py            # Remapping de domaine
│   ├── phases/
│   │   ├── products.py      # Produits + variantes + métafields
│   │   ├── collections.py   # Collections + assignation produits
│   │   ├── pages.py         # Pages statiques + métafields
│   │   ├── blogs.py         # Articles de blog + collections de blog
│   │   ├── menus.py         # Menus avec IDs remappés
│   │   ├── discounts.py     # Réductions
│   │   └── theme.py         # Thème actif + injection IDs
│   └── report.py            # Génération du rapport final
├── static/
│   └── index.html           # Interface web (page unique)
├── tmp_images/              # Cache images temporaire (jamais commité)
└── output/
    ├── id_map.json          # Table de correspondance IDs (persistée)
    └── clone_report.json    # Rapport post-clonage
```

---

## Ordre de clonage

L'ordre respecte les dépendances entre ressources :

```
1. Produits + variantes (REST) → métafields (GraphQL)
2. Collections → assignation des produits avec IDs remappés (REST + GraphQL)
3. Pages statiques (REST) → métafields (GraphQL)
4. Articles de blog + collections de blog (REST) → métafields (GraphQL)
5. Menus → cibles remappées (REST)
6. Politiques du site (REST)
7. Réductions → compteurs remis à zéro (REST)
8. Thème actif → injection des IDs remappés dans le JSON (REST)
```

La table `id_map.json` est mise à jour et persistée après chaque phase.

---

## Gestion des images

```
CDN Shopify source
    → téléchargement via httpx
    → stockage dans tmp_images/{resource_id}/filename.jpg
    → re-upload vers boutique cible (multipart via httpx)
    → mise à jour des références avec le nouvel URL
```

Le dossier `tmp_images/` sert de cache : si le clonage est interrompu, les images déjà téléchargées ne sont pas re-téléchargées au redémarrage.

---

## Rate limiting

L'API Shopify impose deux types de limites :

- **REST** : bucket de 40 appels, récupération de 2/seconde → `asyncio.Semaphore` + retry avec backoff exponentiel sur erreur 429
- **GraphQL** : quota basé sur le coût de chaque requête → vérification du champ `extensions.cost` dans chaque réponse, pause si le budget est épuisé

---

## Remapping de domaine

Remplacement effectué dans tous les contenus textuels avant écriture sur la cible :

- Descriptions produits (HTML)
- Contenu des articles de blog et pages statiques
- Politiques du site
- JSON du thème (`settings_data.json`, templates)
- Métafields de type `url` ou `html`
- Attributs `href` et `src` dans tout HTML stocké

Domaines remplacés : `ancien-domaine.myshopify.com` et le domaine custom source → domaine cible.

---

## Interface web

**Formulaire de configuration (`/`)**
- Token API + domaine `.myshopify.com` source
- Token API + domaine `.myshopify.com` cible
- Domaine custom source (ex : `www.ancienne-boutique.fr`)
- Domaine cible
- Bouton "Lancer le clonage"

**Suivi de progression (`/status`)**
- Polling toutes les 2 secondes sur l'endpoint `GET /api/status`
- Affichage de la phase en cours + logs des dernières actions
- Barre de progression par phase

**Rapport final (`/report`)**
- Tableau `{ ressource, id_source, id_cible, statut }` chargé depuis `clone_report.json`

---

## Configuration sauvegardée

Les tokens et domaines sont sauvegardés dans `config.json` après le premier lancement :

```json
{
  "source": {
    "shop": "source-boutique.myshopify.com",
    "custom_domain": "www.ancienne-boutique.fr",
    "token": "shpat_xxx"
  },
  "target": {
    "shop": "target-boutique.myshopify.com",
    "custom_domain": "www.nouvelle-boutique.fr",
    "token": "shpat_yyy"
  }
}
```

`config.json`, `tmp_images/` et `output/` sont exclus du contrôle de version (`.gitignore`).
