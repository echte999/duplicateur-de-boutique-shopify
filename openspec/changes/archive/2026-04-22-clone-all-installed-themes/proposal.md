## Why

La V2 doit cloner l'ensemble d'une boutique exploitable, pas seulement sa vitrine publiée. Limiter la copie au thème actif laisse de côté les thèmes de travail, saisonniers ou de secours, ce qui empêche une migration fidèle et complique les reprises côté cible.

## What Changes

- Faire évoluer la phase `theme` pour lister tous les thèmes installés sur la boutique source et cloner chacun d'eux vers la cible.
- Réutiliser le pipeline existant de clonage d'assets, remapping de domaine et remapping d'IDs JSON pour chaque thème cloné.
- Préserver la sémantique de publication: le thème source `main` devient le thème publié sur la cible, les autres restent non publiés.
- Enregistrer un mapping et des entrées de rapport par thème cloné, ainsi que les statuts des assets associés, afin de garder la reprise et le diagnostic cohérents.
- Garder l'orchestration et la sélection de phase inchangées côté utilisateur: la phase `theme` couvre désormais tous les thèmes installés.

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `theme-cloning`: la capability ne doit plus se limiter au thème `main`; elle doit cloner tous les thèmes installés, préserver le rôle publié/non publié, et produire un rapport par thème.

## Impact

- Modifié: `cloner/phases/theme.py` pour itérer sur tous les thèmes source, cloner chaque ensemble d'assets et publier uniquement le thème cible correspondant au `main` source.
- Modifié: `main.py` pour conserver la phase `theme` comme phase unique V2 sans changement d'interface, mais avec une portée élargie.
- Impact probable sur `cloner/report.py`, `cloner/mapping.py` et la persistance d'état si des métadonnées supplémentaires par thème sont nécessaires pour le reporting ou la reprise.
- API Shopify REST concernée: `GET /themes`, `POST /themes`, `PUT /themes/{id}`, `GET /themes/{id}/assets`, `PUT /themes/{id}/assets`.
- Pas de nouvelle dépendance externe prévue.
