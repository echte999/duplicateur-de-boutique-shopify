## Why

Les trois dernières features du MVP manquantes rendent l'outil inutilisable en production : sans remapping de domaine les liens internes pointent vers la boutique source, sans table de correspondance IDs les références croisées (menus, thème) sont cassées, et sans rapport post-clonage il est impossible de diagnostiquer les erreurs.

## What Changes

- Implémentation de `cloner/domain.py` : remplacement chirurgical du domaine source par le domaine cible dans tout contenu HTML/JSON (descriptions produits, pages, articles, politiques, JSON du thème, métafields url/html, attributs href/src)
- Implémentation complète de `cloner/mapping.py` : table `{ id_source: id_cible }` construite et persistée en temps réel dans `output/id_map.json` après chaque phase de clonage
- Implémentation de `cloner/report.py` : génération du fichier `output/clone_report.json` avec `{ id_source, id_cible, type, statut }` par ressource clonée
- Intégration du remapping de domaine dans toutes les phases existantes (products.py, collections.py, theme.py)
- Intégration de la table de correspondance dans toutes les phases existantes

## Capabilities

### New Capabilities

- `domain-remapping`: Remplacement chirurgical du domaine source par le domaine cible dans tous les contenus textuels et JSON du clone
- `id-mapping`: Table de correspondance IDs construite en temps réel et persistée, utilisée pour résoudre les références croisées entre ressources
- `clone-report`: Génération du rapport post-clonage JSON listant chaque ressource avec son id source, id cible, type et statut

### Modified Capabilities

<!-- Aucune capability existante avec spec déjà écrite -->

## Impact

- `cloner/domain.py` : nouveau module (actuellement vide ou absent)
- `cloner/mapping.py` : nouveau module (actuellement vide ou absent)
- `cloner/report.py` : nouveau module (actuellement vide ou absent)
- `cloner/phases/products.py` : ajout des appels domain.remap() et mapping.register()
- `cloner/phases/collections.py` : ajout des appels domain.remap() et mapping.register()
- `cloner/phases/theme.py` : ajout des appels domain.remap() et injection des IDs remappés dans le JSON des sections
- `main.py` : appel à report.generate() en fin de clonage, persistance de id_map.json
- `output/` : fichiers id_map.json et clone_report.json générés automatiquement
