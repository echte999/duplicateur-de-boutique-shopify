## Why

Les menus de navigation (principale, footer, menus custom) sont absents de la boutique cible après clonage, rendant la navigation entièrement cassée. C'est un prérequis V1 pour avoir une boutique cible pleinement fonctionnelle.

## What Changes

- Ajout de `cloner/phases/menus.py` : clonage de tous les menus Shopify via l'API REST
- Les cibles des items de menu (collections, produits, pages, articles) sont remappées via `id_map` pour pointer vers les objets cibles
- Les URLs internes dans les handles et liens de menu sont remappées au nouveau domaine
- Les menus assignés dans le thème (`settings_data.json`, templates) sont synchronisés pour utiliser les handles/IDs corrects
- Intégration dans `main.py` comme phase 5 de l'ordre de clonage

## Capabilities

### New Capabilities
- `menu-cloning`: Clonage de tous les menus Shopify avec remapping des cibles (IDs, handles, domaine) et synchronisation avec le thème

### Modified Capabilities
- `theme-cloning`: Les références de menus dans `settings_data.json` doivent être vérifiées/mises à jour après clonage des menus

## Impact

- Nouveau fichier : `cloner/phases/menus.py`
- Modification : `main.py` — ajout de la phase menus dans l'orchestrateur
- Modification : `cloner/phases/theme.py` — vérification des handles de menus injectés dans le JSON du thème
- API REST Shopify : endpoints `GET /admin/api/.../menus.json` et `POST /admin/api/.../menus.json`
