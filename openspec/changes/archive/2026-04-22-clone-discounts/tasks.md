## 1. Correction du payload price_rule

- [x] 1.1 Ajouter `usage_count` à la liste des champs exclus du payload dans `cloner/phases/discounts.py` (ligne où `id`, `admin_graphql_api_id`, `created_at`, `updated_at` sont exclus)

## 2. Vérification de l'intégration

- [x] 2.1 Vérifier que `clone_discounts` est bien appelé à l'étape 7 dans `main.py` et que son résultat est ajouté au `report` — confirmer sans modification si déjà correct
- [x] 2.2 Vérifier que `mapping.save()` est appelé après la phase discounts dans `main.py`

## 3. Validation manuelle

- [ ] 3.1 Lancer un clone de test et vérifier dans `output/clone_report.json` que des entrées de type `price_rule` apparaissent avec `statut: "ok"`
- [ ] 3.2 Vérifier sur la boutique cible que les price rules créées ont `usage_count = 0`
- [ ] 3.3 Vérifier que les discount codes associés sont bien présents sur la boutique cible
