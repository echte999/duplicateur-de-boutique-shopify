# Copieur de boutique Shopify

Outil CLI personnel pour cloner entièrement une boutique Shopify vers une autre — produits, collections, thèmes, menus, pages, articles, politiques et réductions — en remappant automatiquement les IDs internes et les domaines.

## Prérequis

- Python 3.11+
- Deux boutiques Shopify avec des tokens d'accès privé (Admin API)

## Installation

```bash
pip install httpx
```

## Configuration

Copier `.env.example` en `.env` et remplir les valeurs :

```env
SOURCE_SHOP=source-boutique.myshopify.com
SOURCE_CUSTOM_DOMAIN=www.ancienne-boutique.fr   # optionnel
SOURCE_TOKEN=shpat_xxx

TARGET_SHOP=target-boutique.myshopify.com
TARGET_CUSTOM_DOMAIN=www.nouvelle-boutique.fr   # optionnel
TARGET_TOKEN=shpat_yyy
```

## Lancement

```bash
python main.py
```

Un menu interactif s'affiche pour choisir les phases à cloner :

```
  Choisissez les phases a cloner
  ----------------------------------------
▶ [●]  Produits + variantes
  [●]  Collections
  [●]  Pages statiques
  ...
  ↑↓ Naviguer   Espace Cocher/décocher   A Tout/rien   Entrée Confirmer
```

## Phases de clonage

| Phase | Contenu cloné |
|---|---|
| `products` | Produits, variantes, images, métafields |
| `collections` | Collections manuelles et automatiques + assignation produits |
| `pages` | Pages statiques + métafields |
| `blogs` | Articles de blog + collections de blog + métafields |
| `menus` | Menus avec cibles remappées |
| `policies` | Politiques du site (CGV, retours…) |
| `discounts` | Codes de réduction (compteurs remis à zéro) |
| `theme` | Tous les thèmes installés + injection des IDs remappés |

L'ordre respecte les dépendances : `products` est requis avant `collections`, et `collections`/`pages` avant `menus`.

## Fonctionnement interne

**Remapping d'IDs** — Shopify génère des IDs différents entre boutiques. Une table `output/id_map.json` est construite en temps réel et utilisée par toutes les phases pour résoudre les références croisées.

**Remapping de domaine** — Toutes les occurrences de l'ancien domaine (`.myshopify.com` et domaine custom) sont remplacées par le domaine cible dans les descriptions, articles, pages, politiques, métafields HTML/URL et le JSON du thème.

**Cache images** — Les images sont téléchargées depuis le CDN Shopify source vers `tmp_images/`, puis re-uploadées sur la boutique cible. Les images déjà présentes dans le cache ne sont pas re-téléchargées.

**Reprise sur erreur** — L'état d'avancement est persisté dans `output/clone_state.json`. En cas d'interruption, relancer `python main.py` reprend à la phase suivante sans refaire ce qui est déjà complété.

**Audit préalable** — Avant tout clonage, un audit de la boutique source détecte les objets orphelins (produits/collections référencés mais manquants). Un résumé est affiché avec possibilité d'annuler.

## Sorties

```
output/
├── id_map.json              # Table source_id → target_id
├── clone_report.json        # Rapport { type, id_source, id_cible, statut }
├── clone_state.json         # État de reprise (supprimé à la fin)
├── phase_selection.json     # Dernière sélection de phases (mémorisée)
└── source_health_audit.json # Rapport d'audit de la source
```

## Fichiers exclus du dépôt

`.env`, `config.json`, `tmp_images/`, `output/` — voir `.gitignore`.

## Hors périmètre

- Historique des commandes et données clients
- Applications tierces
- Synchronisation continue ou multi-cibles en parallèle
