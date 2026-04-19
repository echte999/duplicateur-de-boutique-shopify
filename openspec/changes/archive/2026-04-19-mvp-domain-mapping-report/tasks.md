## 1. Module domain.py — Remapping de domaine

- [x] 1.1 Créer `cloner/domain.py` avec la fonction `remap(text, source_domains, target_domain) -> str` utilisant `re.sub()` multi-patterns
- [x] 1.2 Gérer les cas limites : entrée `None`, entrée non-string, chaîne vide — retourner sans erreur
- [x] 1.3 Écrire un test rapide en console (snippet Python) pour valider le remplacement sur un HTML fictif

## 2. Module mapping.py — Table de correspondance IDs

- [x] 2.1 Créer `cloner/mapping.py` avec la classe `IDMap` et les méthodes `register(type, src_id, tgt_id)` et `resolve(src_id) -> int | None`
- [x] 2.2 Implémenter `IDMap.save()` : sérialise le dict interne en JSON dans `output/id_map.json` (créer le répertoire si nécessaire)
- [x] 2.3 Implémenter `IDMap.load()` : charge `output/id_map.json` si existant, initialise un dict vide sinon

## 3. Module report.py — Rapport post-clonage

- [x] 3.1 Créer `cloner/report.py` avec la classe `CloneReport` et la méthode `add_entry(type, src_id, tgt_id, status)`
- [x] 3.2 Implémenter `CloneReport.generate()` : écrit `output/clone_report.json` avec toutes les entrées accumulées
- [ ] 3.3 Ajouter l'endpoint `GET /api/report` dans `main.py` qui lit et retourne `output/clone_report.json` (liste vide si absent)

## 4. Intégration dans la phase Produits

- [x] 4.1 Modifier `cloner/phases/products.py` pour appeler `id_map.register("product", src_id, tgt_id)` après chaque création de produit
- [x] 4.2 Appeler `id_map.register("variant", src_id, tgt_id)` pour chaque variante créée
- [x] 4.3 Appeler `domain.remap()` sur `body_html` et les métafields de type `html`/`url` avant écriture
- [x] 4.4 Appeler `report.add_entry()` pour chaque produit cloné (succès ou échec)

## 5. Intégration dans la phase Collections

- [x] 5.1 Modifier `cloner/phases/collections.py` pour appeler `id_map.register("collection", src_id, tgt_id)` après chaque création
- [x] 5.2 Appeler `domain.remap()` sur les descriptions de collections avant écriture
- [x] 5.3 Appeler `report.add_entry()` pour chaque collection clonée

## 6. Intégration dans la phase Pages statiques

- [x] 6.1 Modifier `cloner/phases/pages.py` pour appeler `domain.remap()` sur `body_html` avant écriture
- [x] 6.2 Appeler `id_map.register("page", src_id, tgt_id)` après chaque création
- [x] 6.3 Appeler `report.add_entry()` pour chaque page clonée

## 7. Intégration dans la phase Blogs

- [x] 7.1 Modifier `cloner/phases/blogs.py` pour appeler `domain.remap()` sur `body_html` de chaque article avant écriture
- [x] 7.2 Appeler `id_map.register("blog", src_id, tgt_id)` et `id_map.register("article", src_id, tgt_id)`
- [x] 7.3 Appeler `report.add_entry()` pour chaque blog et article cloné

## 8. Intégration dans la phase Menus

- [x] 8.1 Modifier `cloner/phases/menus.py` pour appeler `domain.remap()` sur l'URL de chaque item de navigation avant écriture
- [x] 8.2 Appeler `report.add_entry()` pour chaque menu cloné

## 9. Intégration dans la phase Réductions / Politiques

- [x] 9.1 Modifier `cloner/phases/discounts.py` pour appeler `domain.remap()` sur tout contenu textuel des politiques avant écriture
- [x] 9.2 Appeler `report.add_entry()` pour chaque réduction et politique clonée

## 10. Intégration dans la phase Thème

- [x] 10.1 Modifier `cloner/phases/theme.py` pour appeler `domain.remap()` sur le contenu de `settings_data.json` avant upload
- [x] 10.2 Appeler `domain.remap()` sur les templates JSON du thème qui contiennent des URLs
- [x] 10.3 Appeler `report.add_entry()` pour le thème cloné

## 11. Orchestration dans main.py

- [x] 11.1 Instancier `IDMap` et `CloneReport` au démarrage du clonage, appeler `id_map.load()` pour reprendre un état existant
- [x] 11.2 Appeler `id_map.save()` après chaque phase terminée
- [x] 11.3 Appeler `report.generate()` dans un bloc `finally` à la fin du clonage (succès ou erreur partielle)
- [x] 11.4 Passer `id_map` et `domain_remapper` en paramètres à chaque fonction de phase (pas de globals)
