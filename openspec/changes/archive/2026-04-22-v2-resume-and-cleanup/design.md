## Context

Le clonage est orchestré dans `main.py` via une séquence de 8 phases (produits → collections → pages → blogs → menus → politiques → réductions → thème). Chaque phase est indépendante et ses résultats sont déjà persistés (`id_map.json`, `clone_report.json`). Si le processus s'interrompt, l'utilisateur doit aujourd'hui tout relancer depuis zéro.

Le dossier `tmp_images/` accumule les images téléchargées et n'est jamais supprimé, même après un clonage réussi.

## Goals / Non-Goals

**Goals:**
- Persister l'état d'avancement après chaque phase réussie dans `output/clone_state.json`.
- Au démarrage d'un nouveau clonage, détecter si un état partiel existe et proposer de reprendre depuis la dernière phase complétée.
- Supprimer automatiquement `tmp_images/` une fois toutes les phases terminées avec succès.

**Non-Goals:**
- Reprise au niveau d'un item individuel au sein d'une phase (ex : reprendre au 50ème produit) — la granularité reste la phase complète.
- Interface graphique pour gérer les états de reprise.
- Sauvegarde de l'état en cas d'interruption brutale (SIGKILL) — seules les phases complètes sont persistées.

## Decisions

### D1 : Fichier `clone_state.json` comme point de vérité

**Choix** : un fichier JSON simple dans `output/` avec la liste des phases complétées et les métadonnées du clonage en cours (boutique source, date).

**Alternatives considérées** :
- Déduire l'état depuis `clone_report.json` : fragile car le rapport peut être partiel ou corrompu.
- Base de données SQLite : overkill pour un outil personnel one-shot.

**Rationale** : le JSON est lisible, éditable manuellement si besoin de forcer une reprise, et cohérent avec le reste de la persistance du projet.

### D2 : Vérification de cohérence au démarrage

**Choix** : au démarrage, comparer la boutique source configurée avec celle enregistrée dans `clone_state.json`. Si elles diffèrent, ignorer l'état et repartir de zéro.

**Rationale** : évite de reprendre un état orphelin d'un clone précédent vers une autre boutique.

### D3 : Nettoyage synchrone post-succès

**Choix** : supprimer `tmp_images/` via `shutil.rmtree` juste après la confirmation que toutes les phases ont réussi, avant de fermer le rapport.

**Alternatives considérées** :
- Nettoyage en tâche de fond asynchrone : risque de laisser des fichiers si le processus est tué.
- Option opt-in dans l'UI : complexifie l'interface pour un cas d'usage simple.

**Rationale** : le nettoyage synchrone est déterministe et s'intègre naturellement dans le flux existant.

## Risks / Trade-offs

- **[Risque] Corruption de `clone_state.json`** → Mitigation : wrapper les écritures dans un try/except ; en cas d'erreur de lecture, ignorer l'état et repartir de zéro avec un avertissement dans les logs.
- **[Trade-off] Granularité phase** : si une phase échoue à mi-chemin, les items déjà créés dans la cible ne sont pas rollbackés. La reprise relance toute la phase depuis le début, ce qui peut créer des doublons. → Mitigation : acceptable pour un usage personnel one-shot ; l'utilisateur peut vider la boutique cible manuellement si besoin.
- **[Risque] Suppression prématurée de `tmp_images/`** si l'utilisateur relance un clone partiel après nettoyage → les images seront re-téléchargées, ce qui est le comportement normal du cache.

## Migration Plan

1. Ajouter `output/clone_state.json` au `.gitignore`.
2. Déployer : les utilisateurs existants n'ont pas d'état persisté → le premier lancement après mise à jour repart de zéro (comportement identique à l'existant).
3. Pas de rollback nécessaire : la fonctionnalité est additive et non-destructive.

## Open Questions

- Faut-il proposer une option dans l'UI pour désactiver le nettoyage automatique (pour les utilisateurs qui veulent conserver le cache entre plusieurs clones) ? → Pour l'instant : non, usage personnel simple.
