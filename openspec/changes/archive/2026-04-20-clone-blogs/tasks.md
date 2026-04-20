## 1. Module blogs.py — Clonage des blogs

- [x] 1.1 Créer `cloner/phases/blogs.py` avec la fonction `clone_blogs(src_client, tgt_client, id_map, domain_map)`
- [x] 1.2 Implémenter le fetch des blogs source via `GET /blogs.json?limit=250`
- [x] 1.3 Implémenter la création de chaque blog sur la cible via `POST /blogs.json` et enregistrer les IDs dans `id_map`

## 2. Module blogs.py — Clonage des articles

- [x] 2.1 Implémenter le fetch des articles par blog via `GET /blogs/{id}/articles.json?limit=250`
- [x] 2.2 Appliquer le remapping de domaine sur le contenu HTML des articles avant création
- [x] 2.3 Implémenter le re-upload de l'image mise en avant (`image.src`) via le cache `tmp_images/article_{id}/`
- [x] 2.4 Implémenter la création de chaque article sur la cible via `POST /blogs/{target_blog_id}/articles.json` et enregistrer les IDs dans `id_map`

## 3. Métafields — Extension pour blogs et articles

- [x] 3.1 Appeler la fonction de clonage de métafields existante pour chaque blog créé (owner type `Blog`)
- [x] 3.2 Appeler la fonction de clonage de métafields existante pour chaque article créé (owner type `Article`)

## 4. Rapport et orchestration

- [x] 4.1 Ajouter les entrées blogs et articles dans le rapport `clone_report.json`
- [x] 4.2 Brancher la phase `clone_blogs` dans `main.py` à l'étape 4 (après `clone_pages`, avant `clone_menus`)
- [x] 4.3 Persister `id_map.json` après la phase blogs
