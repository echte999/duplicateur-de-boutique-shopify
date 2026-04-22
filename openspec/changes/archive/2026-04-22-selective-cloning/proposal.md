## Why

Actuellement, le clonage lance toujours l'intégralité des phases (produits, collections, pages, articles, menus, politiques, réductions, thème). L'utilisateur n'a aucun moyen de n'exécuter qu'une partie du clonage — ce qui est bloquant quand on veut juste mettre à jour le thème, ou recopier uniquement les produits après une modification.

## What Changes

- Ajout d'une interface de sélection des ressources dans l'UI web, avant le lancement du clonage
- Le backend accepte une liste de phases activées en paramètre du endpoint `/api/start`
- Les phases désactivées sont ignorées dans l'orchestrateur de clonage
- La sélection est mémorisée dans `config.json` pour le prochain lancement

## Capabilities

### New Capabilities

- `selective-cloning` : Permettre à l'utilisateur de choisir précisément quelles phases cloner (produits, collections, pages, articles, menus, politiques, réductions, thème) via des cases à cocher dans l'UI avant de lancer le clonage

### Modified Capabilities

- `clone-state` : Le state du clone doit maintenant stocker et respecter la liste des phases sélectionnées, et n'exécuter/suivre que celles-ci

## Impact

- `main.py` : endpoint `/api/start` accepte un paramètre `phases` (liste de strings)
- `static/index.html` : ajout des cases à cocher de sélection avant le bouton "Lancer"
- `cloner/` : l'orchestrateur filtre les phases selon la sélection
- `config.json` : sauvegarde de la dernière sélection de phases
