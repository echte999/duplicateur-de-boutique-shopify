## 1. Persistance de l'état (`clone-state`)

- [x] 1.1 Créer `cloner/state.py` avec les fonctions `load_state(source_shop)`, `save_phase_completed(phase_name)`, `clear_state()` et la constante `STATE_PATH = output/clone_state.json`
- [x] 1.2 Implémenter `load_state` : lire et parser `clone_state.json`, vérifier la cohérence de la boutique source, retourner la liste des phases complétées (liste vide si fichier absent, corrompu ou boutique différente)
- [x] 1.3 Implémenter `save_phase_completed` : ajouter la phase à `completed_phases` et persister le fichier JSON (créer `output/` si absent)
- [x] 1.4 Implémenter `clear_state` : supprimer `clone_state.json` s'il existe
- [x] 1.5 Ajouter `output/clone_state.json` au `.gitignore` (déjà couvert par `output/` existant)

## 2. Intégration dans l'orchestrateur (`main.py`)

- [x] 2.1 Au démarrage du clonage, appeler `load_state(source_shop)` pour récupérer les phases déjà complétées
- [x] 2.2 Entourer chaque appel de phase dans une condition : sauter si le nom de la phase est dans `completed_phases`
- [x] 2.3 Appeler `save_phase_completed(phase_name)` immédiatement après le retour sans erreur de chaque phase
- [x] 2.4 Loguer un message clair quand une phase est sautée (ex : `[REPRISE] Phase 'products' déjà complétée, sautée`)
- [x] 2.5 Après succès complet de toutes les phases, appeler `clear_state()` pour réinitialiser l'état

## 3. Nettoyage automatique de `tmp_images/` (`tmp-cleanup`)

- [x] 3.1 Créer la fonction `cleanup_tmp_images()` dans `cloner/state.py` (ou `cloner/cleanup.py` si préféré) : supprimer récursivement `tmp_images/` via `shutil.rmtree` si le dossier existe, loguer le résultat
- [x] 3.2 Appeler `cleanup_tmp_images()` dans `main.py` après `clear_state()`, uniquement en cas de succès complet de toutes les phases
- [x] 3.3 Vérifier que l'absence de `tmp_images/` ne lève pas d'erreur (guard `if path.exists()`)

## 4. Tests manuels

- [ ] 4.1 Lancer un clonage complet et vérifier que `clone_state.json` est créé et mis à jour après chaque phase
- [ ] 4.2 Interrompre un clonage à mi-parcours (Ctrl+C après une phase), relancer et vérifier que les phases déjà complétées sont sautées
- [ ] 4.3 Vérifier qu'après un clonage complet réussi, `clone_state.json` et `tmp_images/` sont supprimés
- [ ] 4.4 Modifier manuellement `clone_state.json` pour corrompre le JSON, relancer et vérifier que le clonage repart de zéro sans erreur
