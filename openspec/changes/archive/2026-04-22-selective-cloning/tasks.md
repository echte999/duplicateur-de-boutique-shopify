## 1. Backend — Paramètre `phases` dans `/api/start`

- [x] 1.1 Modifier le modèle Pydantic du body de `/api/start` dans `main.py` pour accepter un champ optionnel `phases: list[str]` (défaut : toutes les phases)
- [x] 1.2 Valider que la liste n'est pas vide et que chaque valeur est un nom de phase connu ; retourner une erreur HTTP 400 sinon
- [x] 1.3 Passer la liste `selected_phases` à l'orchestrateur de clonage

## 2. Orchestrateur — Filtrage des phases

- [x] 2.1 Dans l'orchestrateur (`main.py` ou module dédié), modifier la boucle d'exécution pour ne lancer que les phases présentes dans `selected_phases`, tout en respectant l'ordre de dépendance fixe
- [x] 2.2 Vérifier que les phases non sélectionnées sont bien ignorées (ni exécutées, ni marquées comme complétées)

## 3. `clone_state.json` — Ajout de `selected_phases`

- [x] 3.1 Lors de l'écriture initiale de `clone_state.json`, inclure la clé `selected_phases` avec la liste des phases choisies
- [x] 3.2 Au chargement d'un état existant sans `selected_phases`, utiliser la liste complète des phases (compatibilité ascendante)
- [x] 3.3 La logique de reprise doit n'exécuter que les phases dans `selected_phases` ET absentes de `completed_phases`
- [x] 3.4 La suppression de `clone_state.json` après succès se déclenche quand toutes les phases de `selected_phases` sont dans `completed_phases`

## 4. `config.json` — Mémorisation de la sélection

- [x] 4.1 Après un lancement réussi, sauvegarder `selected_phases` dans `config.json` sous la clé `"selected_phases"`
- [x] 4.2 Au chargement de la config, exposer `selected_phases` dans l'endpoint `GET /api/config` (ou équivalent) pour que l'UI puisse pré-remplir le formulaire

## 5. Interface web — Cases à cocher de sélection

- [x] 5.1 Dans `static/index.html`, ajouter un groupe de 8 cases à cocher (une par phase) au-dessus du bouton "Lancer le clonage", avec des libellés lisibles en français
- [x] 5.2 Ajouter un bouton "Tout sélectionner / Tout désélectionner" pour basculer toutes les cases en un clic
- [x] 5.3 Pré-cocher les phases selon `selected_phases` retourné par le backend (toutes cochées si absent)
- [x] 5.4 Bloquer le bouton "Lancer" et afficher un message si aucune phase n'est cochée
- [x] 5.5 Implémenter les avertissements de dépendances manquantes :
  - "Collections" cochée sans "Produits" → avertissement
  - "Menus" cochée sans "Collections" ou "Pages" → avertissement
- [x] 5.6 Inclure la liste des phases cochées dans le body du POST `/api/start`
