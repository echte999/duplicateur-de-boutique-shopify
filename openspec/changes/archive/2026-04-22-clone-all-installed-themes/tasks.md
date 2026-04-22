## 1. Inventaire et orchestration des themes

- [x] 1.1 Refactorer `cloner/phases/theme.py` pour recuperer l'inventaire complet des themes source et identifier le theme `main`
- [x] 1.2 Extraire ou introduire un helper de clonage unitaire par theme afin de reutiliser le pipeline d'assets existant pour chaque theme source
- [x] 1.3 Ordonner l'execution pour cloner d'abord les themes non principaux, puis publier seulement le theme cible correspondant au `main` source en fin de phase
- [x] 1.4 Gerer les collisions de noms sur la cible avec une strategie de nommage deterministe sans ecraser de theme existant

## 2. Mapping, reporting et robustesse de phase

- [x] 2.1 Enregistrer une correspondance `theme` source -> cible pour chaque theme clone dans `IDMapping`
- [x] 2.2 Etendre les entrees produites par la phase `theme` pour conserver un contexte explicite par theme dans le rapport final
- [x] 2.3 Verifier que les traitements existants de remapping de domaine, remapping d'IDs JSON et migration des `shopify://shop_images/` s'appliquent correctement a chaque theme de l'inventaire
- [x] 2.4 Conserver le comportement de reprise au niveau de la phase complete, avec des logs suffisamment precis pour diagnostiquer un echec au milieu de plusieurs themes

## 3. Verification ciblee

- [x] 3.1 Mettre a jour l'outillage de verification du theme (`test_theme.py` ou equivalent) pour couvrir un inventaire contenant plusieurs themes et un seul theme `main`
- [x] 3.2 Verifier qu'aucun changement n'est necessaire dans `main.py`, `cloner/phase_selector.py` et la selection de phases cote utilisateur au-dela de l'elargissement de portee de la phase `theme`
- [x] 3.3 Executer la verification ciblee de la phase theme et confirmer que le rapport distingue bien chaque theme clone et le theme publie final
