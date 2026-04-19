## Why

Le thème actif est la couche visuelle de la boutique — sans lui, la boutique cible est vide de tout rendu. C'est la troisième et dernière phase du MVP, après les produits et les collections.

## What Changes

- Nouveau module `cloner/phases/theme.py` qui clone le thème actif (fichiers Liquid, assets, `settings_data.json`, `settings_schema.json`)
- Téléchargement de chaque asset du thème source et re-upload vers la boutique cible via l'API REST Shopify
- Injection des IDs remappés dans `settings_data.json` et les templates JSON du thème (blocs de sections qui référencent des produits ou collections)
- Remapping de domaine appliqué sur tous les contenus textuels du thème (fichiers Liquid, JSON)
- Intégration dans l'orchestrateur principal (`main.py`) comme phase 8 (dernière phase du MVP)
- Mise à jour du rapport de clonage avec les assets du thème

## Capabilities

### New Capabilities

- `theme-cloning`: Clonage complet du thème actif — téléchargement de tous les assets, re-upload vers la cible, remapping des IDs et du domaine dans les contenus JSON/Liquid

### Modified Capabilities

- `clone-collections`: Aucun changement de spec — les IDs de collections remappés produits par cette phase sont consommés ici, pas modifiés

## Impact

- Nouveau fichier : `cloner/phases/theme.py`
- Modifié : `main.py` — ajout de la phase thème dans l'orchestration
- Dépend de : `cloner/mapping.py` (table d'IDs), `cloner/domain.py` (remapping domaine), `cloner/client.py` (HTTP)
- API Shopify REST : `GET /themes`, `GET /themes/{id}/assets`, `PUT /themes/{id}/assets`
- Pas de nouvelles dépendances externes
