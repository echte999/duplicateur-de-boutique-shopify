## 1. Vérification de l'implémentation existante

- [x] 1.1 Vérifier que le GID GraphQL utilisé dans `pages.py` (`gid://shopify/Page/{id}`) est correct pour l'API Admin Shopify — confirmer que la query `page(id:)` retourne des métafields
- [x] 1.2 Vérifier que `_LINK_RE` (regex pagination) dans `pages.py` couvre bien le format du header `Link` Shopify (même regex que `collections.py` — cohérence à confirmer)
- [x] 1.3 Vérifier que `clone_pages` dans `main.py` est bien appelé en position 3 (après collections, avant blogs) ✓ déjà le cas
- [x] 1.4 Vérifier que `report.py` inclut les entrées de type `"page"` dans la sortie finale

## 2. Tests manuels

- [ ] 2.1 Lancer le clone sur une boutique de test et vérifier que les pages apparaissent sur la boutique cible
- [ ] 2.2 Vérifier que le remapping de domaine est appliqué dans `body_html` (inspecter une page avec des liens internes)
- [ ] 2.3 Vérifier que les métafields de pages sont copiés (tester avec une page ayant au moins un métafield custom)
- [ ] 2.4 Vérifier que le rapport `clone_report.json` contient les entrées `type: "page"` avec les bons IDs

## 3. Mise à jour de la documentation

- [x] 3.1 Cocher `[X] Pages statiques avec remapping domaine` dans `PRD.md` (section V1)
