## 1. Inventaire et orchestration des thèmes

- [ ] 1.1 Refactorer `cloner/phases/theme.py` pour récupérer l'inventaire complet des thèmes source et identifier le thème `main`
- [ ] 1.2 Extraire ou introduire un helper de clonage unitaire par thème afin de réutiliser le pipeline d'assets existant pour chaque thème source
- [ ] 1.3 Ordonner l'exécution pour cloner d'abord les thèmes non principaux, puis publier seulement le thème cible correspondant au `main` source en fin de phase
- [ ] 1.4 Gérer les collisions de noms sur la cible avec une stratégie de nommage déterministe sans écraser de thème existant

## 2. Mapping, reporting et robustesse de phase

- [ ] 2.1 Enregistrer une correspondance `theme` source → cible pour chaque thème cloné dans `IDMapping`
- [ ] 2.2 Étendre les entrées produites par la phase `theme` pour conserver un contexte explicite par thème dans le rapport final
- [ ] 2.3 Vérifier que les traitements existants de remapping de domaine, remapping d'IDs JSON et migration des `shopify://shop_images/` s'appliquent correctement à chaque thème de l'inventaire
- [ ] 2.4 Conserver le comportement de reprise au niveau de la phase complète, avec des logs suffisamment précis pour diagnostiquer un échec au milieu de plusieurs thèmes

## 3. Vérification ciblée

- [ ] 3.1 Mettre à jour l'outillage de vérification du thème (`test_theme.py` ou équivalent) pour couvrir un inventaire contenant plusieurs thèmes et un seul thème `main`
- [ ] 3.2 Vérifier qu'aucun changement n'est nécessaire dans `main.py`, `cloner/phase_selector.py` et la sélection de phases côté utilisateur au-delà de l'élargissement de portée de la phase `theme`
- [ ] 3.3 Exécuter la vérification ciblée de la phase thème et confirmer que le rapport distingue bien chaque thème cloné et le thème publié final
