# CLAUDE.md — Copieur de boutique Shopify

## Objectif

Outil personnel (usage propre) qui clone entièrement une boutique Shopify source vers une boutique cible, en remappant automatiquement les IDs internes et le domaine.

---

## Stack technique

- **Python 3.11+** — langage unique
- **httpx** — client HTTP async, multipart upload
- **fastapi + uvicorn** — interface web locale
- **Frontend** — HTML + JS vanilla (page unique)
- **Stdlib uniquement** : `asyncio`, `json`, `csv`, `pathlib`, `re`

Pas d'autres dépendances externes.

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

## API Shopify

- **REST** : produits, collections, pages, articles de blog, menus, politiques, réductions, thème
- **GraphQL** : métafields sur tous types d'objets (produits, variantes, collections, pages)

---

## Ordre de clonage (respecter les dépendances)

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

## Règles métier critiques

### Remapping d'IDs

Shopify génère des IDs différents entre boutiques. Maintenir une table `{ id_source: id_cible }` construite en temps réel dans `mapping.py`. Tous les modules `phases/` utilisent cette table pour résoudre les références croisées.

### Remapping de domaine

Remplacer chirurgicalement dans tous les contenus textuels :
- `ancien-domaine.myshopify.com`
- Le domaine custom source (ex : `www.ancienne-boutique.fr`)

Par le domaine cible. Endroits concernés : descriptions produits (HTML), articles, pages, politiques, JSON du thème, métafields `url`/`html`, attributs `href` et `src`.

### Gestion des images

Flux : CDN Shopify source → `tmp_images/{resource_id}/filename.jpg` → re-upload vers cible → mise à jour des références. Le dossier `tmp_images/` est un cache : ne pas re-télécharger les images déjà présentes.

### Rate limiting

- **REST** : bucket 40 appels, récupération 2/s → `asyncio.Semaphore` + retry avec backoff exponentiel sur 429
- **GraphQL** : quota par coût → vérifier `extensions.cost` dans chaque réponse, pause si budget épuisé

---

## Périmètre MVP (priorité actuelle)

- Produits : titre, description, images, prix, variantes, statut, métafield `caracteristiques`
- Collections : manuelles et automatiques, avec assignation des produits remappés
- Thème actif : fichiers, assets, settings — avec injection des IDs remappés
- Remapping de domaine dans tous les contenus HTML/JSON
- Table de correspondance IDs construite en temps réel
- Rapport post-clonage : `clone_report.json` avec `{ id_source, id_cible, type, statut }`

## Hors périmètre

- Historique des commandes, données clients, applications tierces
- Synchronisation continue, multi-cibles en parallèle

---

## Fichiers exclus du contrôle de version

`config.json`, `tmp_images/`, `output/` — voir `.gitignore`.
