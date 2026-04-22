## Why

Le clone découvre aujourd'hui certains objets orphelins trop tard, au moment où une phase tente déjà d'écrire sur la boutique cible. Cela produit des fallbacks silencieux dans les menus, des réductions potentiellement reliées à de mauvais IDs, ou des références cassées dans le thème, alors qu'un audit préflight permettrait de signaler ces incohérences avant le clonage.

## What Changes

- Ajout d'un audit de santé préflight exécuté avant la première écriture sur la boutique cible
- Détection des références orphelines structurées dans les menus source, les règles de réduction source, et les assets JSON du thème source
- Génération d'un rapport d'audit dédié dans `output/source_health_audit.json`, avec résumé lisible dans le terminal
- Demande de confirmation à l'utilisateur avant de poursuivre le clonage si des anomalies sont détectées

## Capabilities

### New Capabilities

- `source-health-audit`: Auditer la boutique source avant clonage pour détecter les références structurées vers des produits, collections, pages, blogs ou articles absents, produire un rapport exploitable, et laisser l'utilisateur annuler le clonage avant toute écriture cible

### Modified Capabilities

<!-- None -->

## Impact

- `main.py`: déclenchement de l'audit avant les phases de clonage et arrêt propre si l'utilisateur refuse de continuer
- `cloner/health_audit.py`: nouveau module centralisant la collecte, la détection et la persistance du rapport
- `cloner/phases/theme.py`: réutilisation possible des helpers de parsing JSON/GID pour détecter les références cassées dans le thème
- `output/source_health_audit.json`: nouveau rapport de préflight, séparé du rapport post-clonage
- Aucune nouvelle dépendance externe
