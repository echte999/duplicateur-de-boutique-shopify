## Context

Le projet clone déjà le thème actif via `cloner/phases/theme.py`, en créant un thème cible, en recopiant ses assets et en appliquant le remapping de domaine et d'IDs décrit dans `PRD.md` et `ARCHITECTURE.md`. La V2 demande maintenant de cloner tous les thèmes installés, tout en gardant la phase `theme` comme phase unique dans l'orchestrateur et dans la sélection de phases.

La contrainte principale est de réutiliser le pipeline existant sans introduire de nouvelle dépendance ni casser les mécanismes V2 déjà en place: clonage sélectif, rate limiting REST/GraphQL, mapping des IDs et rapport final. Le changement porte donc surtout sur l'orchestration de la phase thème et sur la façon de représenter plusieurs thèmes dans le mapping et le reporting.

## Goals / Non-Goals

**Goals:**
- Cloner tous les thèmes retournés par l'API Shopify source pendant la phase `theme`.
- Préserver la sémantique de publication: un seul thème cible publié, correspondant au thème source `main`.
- Réutiliser la logique existante de clonage d'assets, remapping de domaine, remapping d'IDs JSON et migration des `shopify://shop_images/`.
- Produire un mapping et un rapport exploitables pour plusieurs thèmes dans une seule phase.

**Non-Goals:**
- Introduire une nouvelle phase utilisateur ou modifier l'interface de sélection de phases.
- Ajouter une reprise sur erreur au niveau de chaque thème individuel; la granularité de reprise reste la phase `theme`.
- Valider visuellement le rendu des thèmes clonés sur la boutique cible.
- Couvrir la dernière fonctionnalité V2 sur les paramètres de compte Shopify.

## Decisions

### 1. Remplacer la logique "thème actif" par une orchestration d'inventaire

**Décision** : remplacer `fetch_active_theme()` par une récupération de l'inventaire complet des thèmes source, puis itérer sur cet inventaire via un helper dédié de type `clone_single_theme(...)`.

**Pourquoi** : cela garde le comportement unitaire de clonage d'un thème dans un bloc réutilisable, tout en ajoutant un niveau d'orchestration pour le multi-thème. Le remapping de domaine, le remapping JSON et la migration des shop images restent inchangés à l'échelle d'un thème.

**Alternative considérée** : dupliquer toute la logique existante dans une boucle externe monolithique. Rejetée car cela rendrait `theme.py` plus difficile à maintenir et compliquerait les tests.

### 2. Créer tous les thèmes cibles comme non publiés puis publier le correspondant du `main` source en dernier

**Décision** : chaque thème source est d'abord créé sur la cible avec `role: "unpublished"`. Le thème correspondant au `main` source n'est publié qu'après la fin réussie du clonage de tous les thèmes.

**Pourquoi** : cela évite de basculer trop tôt la vitrine cible sur un thème partiellement migré et garde une transition atomique vers le thème principal cloné.

**Alternative considérée** : publier immédiatement le thème cloné dès que le `main` source est traité. Rejetée car l'ordre de traitement deviendrait sensible et la boutique cible pourrait changer d'apparence avant la fin de la phase.

### 3. Préserver un contexte explicite par thème dans le mapping et le reporting

**Décision** : enregistrer un mapping `theme` source → cible pour chaque thème cloné et conserver, dans le rapport généré pendant la phase, une entrée de synthèse par thème ainsi que des entrées d'assets rattachées à ce thème.

**Pourquoi** : avec plusieurs thèmes, un simple flux d'assets sans contexte rend le diagnostic et les reprises manuelles beaucoup plus difficiles. Le rapport doit permettre d'identifier rapidement quel thème a été cloné, publié ou interrompu.

**Alternative considérée** : ne garder qu'une entrée globale de phase thème. Rejetée car insuffisante pour investiguer une erreur sur une boutique contenant plusieurs thèmes.

### 4. Garder la reprise sur erreur au niveau de la phase complète

**Décision** : ne pas modifier `clone_state.json` dans ce change. Si la phase `theme` échoue après avoir cloné une partie de l'inventaire, la reprise relance la phase thème complète.

**Pourquoi** : le besoin prioritaire ici est la couverture fonctionnelle "tous les thèmes installés". Étendre la persistance d'état à une granularité intra-phase élargirait le scope au-delà de la fonctionnalité visée.

**Alternative considérée** : persister l'avancement thème par thème. Rejetée pour ce change car cela touche `clone-state`, la sémantique de reprise et potentiellement la stratégie de nettoyage.

### 5. Rendre les noms cibles déterministes en cas de collision

**Décision** : si la cible contient déjà un thème du même nom, le système crée un nom dérivé et stable, par exemple en suffixant le nom source avec l'ID source ou un index déterministe.

**Pourquoi** : le clonage complet de l'inventaire augmente la probabilité de collisions de noms, en particulier sur des reruns partiels ou des boutiques déjà préparées.

**Alternative considérée** : écraser un thème existant portant le même nom. Rejetée car trop risquée et non alignée avec la stratégie actuelle de création de nouveaux thèmes.

## Risks / Trade-offs

- [Inventaire volumineux] → La phase `theme` peut devenir significativement plus longue. Mitigation: journaliser la progression par thème puis par asset.
- [Échec en milieu d'inventaire] → La reprise redémarre l'ensemble de la phase. Mitigation: garder des entrées de rapport et de mapping par thème pour comprendre où l'échec s'est produit.
- [Collisions de noms sur la cible] → Plusieurs thèmes peuvent finir avec des noms proches. Mitigation: appliquer une stratégie de suffixe déterministe et la documenter dans les logs.
- [Publication du thème principal conditionnée à la réussite globale] → Un échec sur un thème non principal retarde la publication du `main`. Mitigation: ne publier qu'après un clonage complet cohérent, ce qui privilégie l'intégrité à la vitesse.

## Migration Plan

- Refactorer `cloner/phases/theme.py` pour isoler le clonage d'un thème unitaire derrière un helper.
- Ajouter la récupération de l'inventaire des thèmes source et l'ordonnancement "non-main d'abord, main en dernier".
- Étendre les entrées de rapport et le mapping pour plusieurs thèmes sans changer l'interface publique de la phase `theme`.
- Vérifier qu'aucun changement n'est requis côté UI ou dans la liste des phases sélectionnables.

## Open Questions

- Aucune à ce stade. Le périmètre fonctionnel est suffisamment défini par `PRD.md`, `ARCHITECTURE.md` et la capability existante `theme-cloning`.
