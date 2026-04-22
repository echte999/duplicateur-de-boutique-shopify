## Context

Le clonage actuel exécute toujours les 8 phases dans l'ordre fixe : produits → collections → pages → articles → menus → politiques → réductions → thème. Il n'existe aucun moyen de n'en exécuter qu'une partie. L'UI ne propose qu'un bouton "Lancer le clonage" sans options.

Le mécanisme de reprise sur erreur (`clone_state.json`) suit déjà quelles phases sont complétées — le clonage sélectif s'appuie sur cette même logique en ajoutant la notion de phases "activées" vs "désactivées".

## Goals / Non-Goals

**Goals:**
- Permettre à l'utilisateur de cocher/décocher chaque phase avant de lancer
- Le backend n'exécute que les phases sélectionnées, dans l'ordre de dépendance habituel
- La sélection est mémorisée dans `config.json` pour le prochain lancement
- Compatible avec le mécanisme de reprise : une phase non sélectionnée est traitée comme "à ignorer" (distincte de "déjà complétée")

**Non-Goals:**
- Réordonner les phases (l'ordre reste contraint par les dépendances)
- Sélectionner un sous-ensemble de produits ou de collections (la granularité reste la phase entière)
- Interface de sélection avancée (profils de sélection sauvegardés, etc.)

## Decisions

### 1. Représentation de la sélection : liste de noms de phases

La sélection est une liste de strings (`["products", "collections", "theme"]`) passée dans le body du POST `/api/start`. C'est la forme la plus simple à sérialiser, valider et persister.

Alternative rejetée : bitmask ou dict `{phase: bool}` — plus verbeux, pas de gain réel pour 8 phases.

### 2. Où filtrer les phases : dans l'orchestrateur central (`main.py`)

L'orchestrateur dans `main.py` reçoit la liste des phases activées et ne lance que celles-ci, dans l'ordre de dépendance fixe. Les modules de phase eux-mêmes ne changent pas.

Alternative rejetée : chaque phase se "décide" elle-même — couplage plus fort, logique dispersée.

### 3. Interaction avec la reprise sur erreur

Une phase non sélectionnée ne doit pas bloquer la reprise. Dans `clone_state.json`, on distingue :
- `completed_phases` : phases qui ont été exécutées et réussies
- `selected_phases` : phases que l'utilisateur a choisies pour ce run

Au démarrage d'un run, l'orchestrateur exécute les phases qui sont à la fois dans `selected_phases` ET pas encore dans `completed_phases`.

### 4. Persistance dans `config.json`

La dernière sélection est sauvegardée sous la clé `"selected_phases"` dans `config.json`, pré-remplie dans le formulaire au prochain chargement.

### 5. UI : cases à cocher groupées, toutes cochées par défaut

8 cases à cocher, une par phase, libellées en français, affichées avant le bouton "Lancer". Toutes cochées par défaut (= comportement actuel). Groupées visuellement avec un "Tout sélectionner / Tout désélectionner".

## Risks / Trade-offs

- **Dépendances entre phases non vérifiées** → L'UI ne bloquera pas de cocher "Collections" sans cocher "Produits", même si cela produit un clone incohérent. Mitigation : avertissement dans l'UI si une phase dépendante est sélectionnée sans sa dépendance.
- **Compatibilité `clone_state.json` existant** → Un état sauvegardé avant cette feature n'a pas de `selected_phases`. Mitigation : si absent, considérer toutes les phases comme sélectionnées (comportement identique à avant).
