# SaaS de clonage Shopify — Spécification projet

## Contexte

Outil personnel (usage propre) permettant de copier entièrement une boutique Shopify d'un compte à un autre, en adaptant automatiquement le maillage interne au nouveau nom de domaine fourni à l'avance.

---

## Périmètre fonctionnel

### Ce qui est copié

- Fiches produits : titre, description, images, prix, variantes, statut, **tous les métafields** (dont le champ personnalisé `caracteristiques`)
- Fiches de collections (manuelles et automatiques) avec assignation des produits
- Articles de blog + collections de blog
- Pages statiques (À propos, Contact, pages custom)
- Tous les menus (navigation principale, footer, menus custom)
- Politiques du site (remboursement, confidentialité, CGV…)
- Réductions
- Thème de la boutique (actif uniquement en MVP, tous les thèmes en V2)
- Paramètres du compte Shopify (dans la mesure de ce qu'expose l'API)

### Ce qui est exclu

- Historique des commandes
- Applications tierces
- Données clients (emails, adresses)
- Synchronisation continue source → cible
- Multi-cibles en parallèle

---

## Règles métier fondamentales

### 1. Remapping d'IDs dynamique

Shopify génère des IDs internes différents entre la boutique source et la boutique cible. Le moteur doit maintenir une **table de correspondance** `{ id_source: id_cible }` construite en temps réel pendant le clonage.

L'ordre de clonage doit respecter les dépendances :

```
1. Produits + variantes
2. Collections → assignation des produits (IDs remappés)
3. Pages statiques / Articles de blog
4. Menus → pointent vers collections, pages, produits (IDs remappés)
5. Réductions → peuvent cibler des produits/collections spécifiques (IDs remappés)
6. Thème → injection des IDs remappés dans le JSON des sections
```

### 2. Remapping de domaine

Remplacement **chirurgical** du domaine source par le domaine cible fourni à l'avance, sans toucher aux URLs externes.

Remplacer :
- `ancien-domaine.myshopify.com`
- Le domaine custom source (ex : `www.ancienne-boutique.fr`)

Par :
- Le nouveau domaine cible prédéfini

**Endroits où le domaine peut apparaître :**
- Descriptions produits (HTML riche)
- Contenu des articles de blog
- Pages statiques
- JSON du thème (`settings_data.json`, templates)
- Métafields de type URL ou HTML
- Attributs `href` et `src` dans tout contenu HTML stocké
- Politiques du site (également remplacer le nom de la boutique source)

### 3. Gestion des images

Flux : téléchargement depuis le CDN Shopify source → **stockage local temporaire** → re-upload vers la boutique cible → mise à jour des références.

- Le stockage local sert de cache pour permettre de relancer un clone raté sans tout re-télécharger
- Nettoyage automatique du répertoire temporaire après succès du clonage complet (V2)

### 4. Réductions

- Copie brute de la configuration
- Remise à zéro des compteurs d'utilisation

---

## Roadmap

### MVP — Le clone fonctionnel de base

> Objectif : une boutique cible navigable, avec le catalogue et le visuel corrects.

- [X] Produits : titre, description, images (stockage local + re-upload), prix, variantes, statut, métafield `caracteristiques`
- [X] Collections : manuelles et automatiques, avec assignation des produits remappés
- [X] Thème actif : fichiers, assets, settings — avec injection des IDs remappés dans le JSON
- [X] Remapping de domaine : remplacement chirurgical dans tous les contenus HTML/JSON
- [X] Table de correspondance IDs : construite en temps réel, utilisée pour toutes les références croisées
- [X] Rapport post-clonage : fichier JSON/CSV `{ id_source, id_cible, type, statut }` par ressource

---

### V1 — La boutique complète

> Objectif : tout ce qu'un visiteur ou un admin verrait au quotidien est en place.

- [X] Tous les métafields (pas seulement produits — collections, pages, variantes)
- [X] Pages statiques avec remapping domaine
- [X] Articles de blog + collections de blog
- [X] Menus (navigation principale, footer, menus custom) avec remapping des cibles
- [X] Politiques du site : remplacement du nom de boutique + domaine
- [X] Réductions : copie config + remise à zéro des compteurs d'utilisation

---

### V2 — Robustesse et confort d'utilisation

> Objectif : rendre le process fiable et agréable à opérer, même sur des boutiques complexes.

- [X] Reprise sur erreur : relancer depuis le point d'échec sans tout recommencer
- [X] Nettoyage automatique du stockage local temporaire après succès
- [X] Clonage sélectif : choisir quelles ressources copier (ex : thème uniquement, produits uniquement)
- [X] Gestion des rate limits Shopify : file d'attente avec backoff automatique
- [X] Audit de santé : détection des objets orphelins dans la boutique source avant clonage
- [ ] Tous les thèmes installés (pas seulement le thème actif)
- [ ] Paramètres du compte Shopify (devise, taxes, shipping zones dans la mesure de ce qu'expose l'API)

---

## Points d'attention techniques

| Sujet | Détail |
|---|---|
| **Rate limits Shopify** | L'API Shopify impose des limites de requêtes. À gérer avec une file d'attente et un backoff exponentiel (V2 en priorité, à anticiper dès le MVP) |
| **Objets sans équivalent API** | Certaines configs Shopify ne sont pas exposées via l'API Admin REST/GraphQL — cartographier ces limites avant de commencer |
| **Thème : assets custom** | Les fonts, JS et CSS additionnels du thème sont inclus dans le scope de copie |
| **Métafields** | Présents sur plusieurs types d'objets : produits, variantes, collections, pages — ne pas se limiter aux produits |
| **Rapport post-clonage** | Essentiel même en MVP pour débugger les liens cassés ou collections vides |

---

## Décisions de conception actées

- **Pas de synchronisation continue** : le clonage est un acte one-shot
- **Usage personnel uniquement** : pas de gestion multi-utilisateurs, pas de système de pricing
- **Stockage d'images en local temporaire** : suffisant pour l'usage prévu
- **Commandes exclues** : trop contraignantes légalement et techniquement
- **Apps tierces exclues** : non reproductibles via API

---

*Document généré à partir de la session de spécification — à utiliser comme brief pour un agent IA de codage.*