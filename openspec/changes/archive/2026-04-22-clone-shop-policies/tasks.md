## 1. Extension du remapping de domaine (domain.py)

- [x] 1.1 Ajouter les paramètres `source_shop_name: str | None` et `target_shop_name: str | None` à la fonction `remap()` dans `cloner/domain.py`
- [x] 1.2 Implémenter le remplacement du nom de boutique source dans `remap()` (remplacement exact, case-sensitive, après le remplacement de domaines)
- [x] 1.3 Récupérer le nom de boutique source ET cible via `GET /admin/api/2024-01/shop.json` dans `main.py` lors de l'initialisation du clonage, et passer ces noms à `domain.remap()`

## 2. Implémentation de la phase policies

- [x] 2.1 Créer `cloner/phases/policies.py` avec une fonction `clone_policies(src_client, dst_client, remapper)` async
- [x] 2.2 Implémenter la lecture de toutes les politiques via `GET /admin/api/2024-01/policies.json` sur la boutique source
- [x] 2.3 Implémenter le remapping du `body` HTML de chaque politique via `domain.remap()`
- [x] 2.4 Implémenter l'écriture de chaque politique sur la boutique cible (itération sur la liste et PUT ou méthode disponible)
- [x] 2.5 Gérer les erreurs 422 (politique non modifiable) : logger et marquer `skipped` sans bloquer

## 3. Intégration dans l'orchestrateur

- [x] 3.1 Importer et appeler `clone_policies` dans `main.py` à la position 6 de l'ordre de clonage (après menus, avant réductions)
- [x] 3.2 Passer les noms de boutiques source et cible au remapper utilisé par `policies.py`

## 4. Rapport post-clonage

- [x] 4.1 Ajouter les politiques dans le rapport généré par `cloner/report.py` avec les champs `type`, `title`, `statut` (`ok` ou `skipped`), et `error` si applicable
- [x] 4.2 Mettre à jour `PRD.md` pour cocher la feature V1 correspondante
