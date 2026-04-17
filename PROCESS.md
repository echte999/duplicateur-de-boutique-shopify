# PROCESS.md — Manipulations techniques du projet

Ce fichier documente les décisions techniques, corrections de bugs et configurations effectuées sur le projet.

---

## 1. Structure du projet

```
shopify-cloner/
├── main.py                  # Point d'entrée — charge .env, instancie les classes, lance le clone
├── cloner/
│   ├── client.py            # Client HTTP async (httpx) — REST + GraphQL, rate limiting, retries
│   ├── mapping.py           # Table de correspondance IDs source→cible (persistée dans output/id_map.json)
│   ├── domain.py            # Remapping de domaine dans les contenus HTML/URL
│   ├── image_cache.py       # Cache local d'images (tmp_images/{product_id}/filename)
│   └── phases/
│       └── products.py      # Clonage complet des produits
├── output/                  # id_map.json généré à l'exécution (gitignored)
└── tmp_images/              # Cache images temporaire (gitignored)
```

---

## 2. Configuration d'environnement

### Fichier `.env` (jamais commité)

```
SOURCE_SHOP=source-boutique.myshopify.com
SOURCE_TOKEN=shpat_XXXX
TARGET_SHOP=cible-boutique.myshopify.com
TARGET_TOKEN=shpat_XXXX
SOURCE_CUSTOM_DOMAIN=www.source.fr       # optionnel
TARGET_CUSTOM_DOMAIN=www.cible.fr        # optionnel
```

### Chargement du `.env`

`main.py` charge le `.env` via stdlib uniquement (pas de `python-dotenv`) :
```python
def load_env(path=".env") -> None:
    for line in Path(path).read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())
```

**Décision** : `config.json` initialement prévu a été supprimé — le `.env` existait déjà avec les tokens.

---

## 3. Client Shopify (`cloner/client.py`)

- **API version** : `2024-01`
- **Concurrence** : `asyncio.Semaphore(20)` sur tous les appels REST et GraphQL
- **Retry sur 429** : backoff exponentiel `[1s, 2s, 4s]` puis `ShopifyRateLimitError`
- **GraphQL throttle** : vérifie `extensions.cost.throttleStatus`, dort si budget insuffisant
- **Méthodes REST** : `get_source`, `post_source`, `get_target`, `post_target`, `put_target`

**Bug corrigé** : `put_target` manquait au départ — `_assign_variant_images` appelait `post_target` (POST) au lieu de PUT, ce qui créait une nouvelle ressource plutôt que de mettre à jour la variante.

---

## 4. Clonage des produits (`cloner/phases/products.py`)

### Flux d'exécution

```
clone_all_products()
  ├── _sync_metafield_definitions()     # Copie et épingle les définitions
  ├── fetch_all_products()              # Pagination curseur REST (250/page)
  └── pour chaque produit :
        clone_product()
          ├── _fetch_product_extra()    # GraphQL : catégorie + métafields
          ├── POST products.json        # Création REST du produit
          ├── productUpdate GraphQL     # Définit la catégorie (REST l'ignore en POST)
          ├── clone_product_images()    # Download CDN → base64 → re-upload
          ├── _assign_variant_images()  # PUT variant avec image_id
          └── _write_metafields()       # metafieldsSet GraphQL
```

### Bugs corrigés et raisons

#### Catégorie produit absente
- **Cause** : Shopify ignore `product_category` dans le POST REST de création.
- **Fix** : appel séparé à `productUpdate` GraphQL après création :
  ```graphql
  productUpdate(input: { id: $id, category: { id: $categoryId } })
  ```
- **Note** : `category_gid` est fetché via `GetProductExtra` GraphQL (plus fiable que le champ REST `product_category`).

#### Métafields personnalisés absents ("Aucun champ méta épinglé")
- **Cause 1** : `metafieldsSet` écrit des valeurs mais ne crée pas les définitions si elles n'existent pas sur la cible.
- **Fix** : `_sync_metafield_definitions()` appelé une fois avant le clone, utilise `metafieldDefinitionCreate` pour recréer toutes les définitions.
- **Cause 2** : Les définitions créées par API ne sont pas épinglées → Shopify affiche "Tout voir" au lieu des champs.
- **Fix** : après création, `metafieldDefinitionPin` est appelé sur toutes les définitions présentes sur la cible.

#### Métafields de type référence ignorés
- Types skippés (IDs non transférables entre boutiques) :
  ```python
  _SKIP_TYPES = {"metaobject_reference", "file_reference", "product_reference",
                 "variant_reference", "page_reference", "collection_reference", ...}
  ```

#### Images de variantes manquantes
- **Cause** : `_assign_variant_images` utilisait `post_target` (POST) au lieu de `put_target` (PUT).
- **Fix** : ajout de `put_target` dans `ShopifyClient` + correction de l'appel.
- **Comportement** : la première image du carousel est assignée à toutes les variantes.

#### SEO et métafield `caracteristiques` non remplis
- **Fix global** : remplacement de l'ancienne approche ciblée (une mutation par métafield) par `metafieldsSet` qui envoie tous les métafields en un seul appel — couvre automatiquement `caracteristiques`, couleur native, SEO title/description, et tout futur métafield.

---

## 5. Table de correspondance IDs (`cloner/mapping.py`)

- Persistée dans `output/id_map.json` après chaque `set()`
- Ressources trackées : `product`, `variant`, `collection`, `page`, `blog`, `article`, `menu`
- `has()` permet de skipper les ressources déjà clonées (reprise en cas d'erreur)

---

## 6. Remapping de domaine (`cloner/domain.py`)

Remplace dans tous les contenus textuels :
- `source.myshopify.com` → `cible.myshopify.com`
- `www.source.fr` → `www.cible.fr` (si `SOURCE_CUSTOM_DOMAIN` défini)

Appliqué sur : `body_html` des produits, et métafields de type `html`, `url`, `json_string`.

---

## 7. Cache images (`cloner/image_cache.py`)

- Stockage : `tmp_images/{product_id}/{filename}`
- Skip si le fichier existe déjà (reprise idempotente)
- Filename extrait de l'URL CDN Shopify avant le `?` (paramètres de query ignorés)

---

## 8. MCP Shopify (outillage Claude Code)

Le serveur MCP `@shopify/dev-mcp` a été installé et ajouté à la config locale de Claude Code :

```bash
# Test d'installation
npx -y @shopify/dev-mcp@latest
# → "Shopify Dev MCP Server v1.12.0 running on stdio"

# Ajout à Claude Code (config locale)
claude mcp add shopify -s local -- npx -y @shopify/dev-mcp@latest
```

**Périmètre du MCP** : documentation Shopify, validation GraphQL/Liquid. Pour accès direct à l'Admin API d'une boutique, un token `SHOPIFY_ADMIN_API_TOKEN` peut être configuré dans `~/.claude/settings.json`.

---

## 9. Passage en SaaS — actions manuelles requises

Cette section documente ce que l'opérateur (toi) et chaque utilisateur final devront faire manuellement lors d'une future version SaaS.

---

### 9.1 Actions one-time pour l'opérateur (à faire une seule fois)

#### Créer un compte Shopify Partner
- Aller sur [partners.shopify.com](https://partners.shopify.com) et créer un compte
- Ce compte est nécessaire pour créer une app publique pouvant s'installer sur n'importe quelle boutique

#### Créer une app publique dans le Partner Dashboard
1. **Apps → Create app → Public app**
2. Renseigner le nom, l'URL de l'app (ton domaine HTTPS)
3. Configurer les **Redirect URLs** pour l'OAuth :
   ```
   https://ton-saas.com/auth/callback
   ```
4. Copier le **Client ID** et le **Client Secret** → variables d'env du backend

#### Définir les scopes OAuth requis
Les scopes minimum nécessaires pour le clonage complet :
```
read_products, write_products
read_product_listings, write_product_listings
read_collections, write_collections
read_content, write_content
read_themes, write_themes
read_price_rules, write_price_rules
read_discounts, write_discounts
read_metaobjects, write_metaobjects
```

#### Héberger le backend avec HTTPS obligatoire
- Shopify OAuth exige une **URL de callback HTTPS** — localhost ne fonctionne pas en production
- Options : Railway, Render, Fly.io, VPS avec Nginx + Let's Encrypt
- La FastAPI actuelle (`main.py`) devra être étendue pour gérer les sessions OAuth

#### Soumettre l'app pour review Shopify (si distribution publique)
- Obligatoire pour apparaître sur l'App Store Shopify
- Shopify inspecte les scopes, la politique de confidentialité, les CGU
- Si usage privé / bêta fermée : pas nécessaire, les utilisateurs peuvent installer via lien direct

---

### 9.2 Actions par utilisateur final (à chaque nouvel utilisateur)

#### Connecter la boutique source
1. L'utilisateur clique "Connecter ma boutique source" dans l'interface SaaS
2. Il est redirigé vers le flow OAuth Shopify → il autorise les permissions
3. Le token est stocké côté serveur (jamais exposé côté client)

#### Connecter la boutique cible
- Même flow OAuth, mais pour la boutique de destination
- Les deux tokens sont associés à la session de l'utilisateur en base de données

#### Ce que l'utilisateur N'aura plus à faire (vs la version actuelle)
| Version actuelle (outil perso) | Version SaaS |
|---|---|
| Créer manuellement une Custom App Shopify | Automatique via OAuth |
| Copier le token dans `.env` | Automatique |
| Lancer `python main.py` en terminal | Bouton dans l'interface web |
| Surveiller la console pour les erreurs | Dashboard avec statut en temps réel |

---

### 9.3 Changements techniques nécessaires dans le code

| Composant | Aujourd'hui | SaaS |
|---|---|---|
| **Auth** | Tokens fixes dans `.env` | OAuth par utilisateur, tokens en DB |
| **`ShopifyClient`** | Instancié une fois au démarrage | Instancié par session utilisateur |
| **`IDMapping`** | Fichier local `output/id_map.json` | Table en base de données par job |
| **`ImageCache`** | Dossier local `tmp_images/` | Stockage objet (S3, Cloudflare R2) |
| **`main.py`** | Script CLI | Routes FastAPI + job async (Celery ou asyncio task) |
| **Logs** | `print()` console | Stockés en DB, affichés dans le dashboard |

---

## 10. Lancement

```bash
# Installer les dépendances
pip install -r requirements.txt

# Créer le .env avec les 4 variables requises
# Lancer le clone
python main.py
```

Les produits clonés s'affichent en console avec `source_id → target_id`. En cas d'erreur API, les warnings sont préfixés `[WARN]`.
