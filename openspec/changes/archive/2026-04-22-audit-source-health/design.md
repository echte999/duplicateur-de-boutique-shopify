## Context

Le flux actuel charge la configuration, construit les helpers de remapping, puis exécute les phases de clonage directement dans `main.py`. Plusieurs parties du clone gèrent déjà des cas d'objets orphelins, mais uniquement pendant l'exécution :

- `cloner/phases/menus.py` convertit certains items non remappables en `HTTP` ou `FRONTPAGE`
- `cloner/phases/theme.py` laisse inchangées les références produit/collection introuvables dans les JSON du thème
- `cloner/phases/discounts.py` recopie les IDs source quand aucun mapping n'existe, ce qui peut produire des règles incohérentes sur la cible

Le besoin V2 est de détecter ces incohérences sur la boutique source avant d'écrire quoi que ce soit sur la cible, afin de rendre l'opération plus sûre et plus explicable.

## Goals / Non-Goals

**Goals:**
- Exécuter un audit préflight avant la première écriture cible
- Détecter les références orphelines structurées les plus risquées pour le clone : menus, réductions, thème
- Produire un rapport JSON dédié avec un résumé exploitable par l'opérateur
- Permettre à l'utilisateur d'abandonner le clonage si l'audit trouve des anomalies
- Respecter les phases sélectionnées pour éviter les audits inutiles

**Non-Goals:**
- Corriger automatiquement la boutique source
- Auditer les liens HTML libres dans les descriptions, pages ou articles
- Couvrir les ressources applicatives tierces ou les namespaces d'app non clonés
- Ajouter une UI web spécifique à l'audit dans ce changement

## Decisions

### D1 : Audit préflight centralisé dans `cloner/health_audit.py`

**Choix** : créer un module dédié exposant une fonction de haut niveau de type `run_source_health_audit(client, selected_phases)` qui retourne un résumé et la liste normalisée des anomalies.

**Alternatives considérées** :
- Ajouter une sous-fonction dans chaque phase de clonage : duplique la logique de collecte et ne garantit pas un point d'entrée unique avant les écritures
- Réutiliser `clone_*` en mode dry-run : trop couplé aux écritures cible et aux effets de bord existants

**Rationale** : un module préflight séparé garde une frontière claire entre audit source et clonage effectif, tout en permettant de mutualiser les index d'objets source et le format du rapport.

### D2 : Format de rapport structuré et autonome

**Choix** : écrire `output/source_health_audit.json` avec un objet contenant `summary` et `issues`. Chaque issue contient au minimum : `resource_type`, `resource_id`, `resource_title`, `reference_path`, `referenced_type`, `referenced_id`, `code`, `severity`, `message`.

**Alternatives considérées** :
- Réutiliser `clone_report.json` : mélange préflight et exécution réelle, et contredit la séparation conceptuelle entre audit avant clone et rapport après clone
- Affichage terminal uniquement : insuffisant pour réviser les anomalies sur une boutique volumineuse

**Rationale** : un rapport dédié est plus lisible, persistant, et peut être exploité plus tard sans polluer le reporting post-clonage.

### D3 : Détecteurs phase-aware avec index source partagés

**Choix** : construire une fois les ensembles d'IDs source nécessaires (`products`, `collections`, `pages`, `blogs`, `articles`) puis exécuter seulement les détecteurs utiles selon `selected_phases`.

**Alternatives considérées** :
- Requêtes indépendantes par détecteur : plus simple mais redondant et plus coûteux en appels Shopify
- Audit systématique de tout le périmètre, même si la phase n'est pas sélectionnée : ajoute du bruit et des faux positifs pour les runs partiels

**Rationale** : cette stratégie garde l'audit rapide, cohérent avec le clonage sélectif, et évite de qualifier d'orpheline une référence qui n'est même pas concernée par le run courant.

### D4 : Confirmation explicite avant poursuite si des anomalies existent

**Choix** : si l'audit retourne au moins une anomalie, afficher un résumé dans le terminal et demander une confirmation explicite avant de lancer les phases de clonage. En cas de refus, le processus s'arrête sans écrire sur la cible.

**Alternatives considérées** :
- Continuer toujours automatiquement : trop risqué pour une feature dont le but est justement de prévenir les clones dégradés
- Bloquer systématiquement dès qu'une anomalie est trouvée : trop rigide pour un outil personnel où l'utilisateur peut accepter un clone partiel en connaissance de cause

**Rationale** : la confirmation explicite donne une sécurité utile sans rendre l'outil inutilisable sur des boutiques imparfaites.

### D5 : Périmètre de détection initial volontairement limité

**Choix** : couvrir trois familles d'anomalies à forte valeur :
- items de menus pointant vers des ressources absentes ou d'un type non supporté
- règles de réduction pointant vers des produits ou collections absents
- assets JSON du thème contenant des IDs ou GIDs produit/collection absents

**Alternatives considérées** :
- Audit exhaustif de tout le contenu textuel et HTML : très coûteux, ambigu, et peu fiable sans moteur d'analyse spécifique
- Audit des collections manuelles via `collects` : faible valeur immédiate car les collectes exposées par Shopify sont déjà filtrées par les ressources existantes dans la plupart des cas

**Rationale** : ce périmètre cible exactement les endroits où le clone dispose déjà de références structurées et où les conséquences d'une ressource manquante sont les plus directes.

## Risks / Trade-offs

- **[Risque] Coût API supplémentaire avant chaque clonage** → Mitigation : mutualiser les index d'IDs source, n'auditer que les phases sélectionnées, et réutiliser les helpers existants de pagination/parsing quand possible
- **[Trade-off] Audit non exhaustif** → Mitigation : documenter explicitement le périmètre couvert et laisser les autres contrôles à des évolutions ultérieures
- **[Risque] Faux positifs dans le thème** si certains IDs numériques sont du contenu libre et non des références Shopify → Mitigation : limiter la détection thème aux clés et patterns déjà utilisés pour le remapping, et privilégier les GIDs quand ils sont présents
- **[Risque] Expérience terminal plus verbeuse** → Mitigation : afficher un résumé compact, puis détailler uniquement les premières anomalies avec renvoi vers le fichier JSON complet

## Migration Plan

1. Ajouter `cloner/health_audit.py` et `output/source_health_audit.json` comme artefact runtime non versionné.
2. Brancher l'audit dans `main.py` avant le premier appel de phase.
3. Déployer sans migration de données : si aucun problème n'est détecté, le flux reste identique à l'existant à une étape préflight près.
4. En cas de besoin de rollback, retirer simplement l'appel préflight ; aucune donnée persistée critique n'est introduite.

## Open Questions

- Faut-il, dans une itération ultérieure, exposer le rapport d'audit dans l'interface web en plus du terminal et du fichier JSON ? Pas dans ce changement.
