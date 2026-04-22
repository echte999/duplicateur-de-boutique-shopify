## Why

Le processus de clonage peut échouer en milieu de parcours sur des boutiques volumineuses (rate limits, erreurs réseau, timeouts), forçant aujourd'hui à tout recommencer depuis zéro et à re-télécharger toutes les images. Ces deux fonctionnalités V2 rendent le processus fiable et économe en ressources.

## What Changes

- **Reprise sur erreur** : l'outil persiste l'état d'avancement après chaque phase réussie et permet de relancer le clonage depuis la dernière phase complétée, sans rejouer les phases antérieures ni re-télécharger les ressources déjà traitées.
- **Nettoyage automatique** : une fois le clonage entièrement terminé avec succès, le dossier `tmp_images/` est supprimé automatiquement pour libérer l'espace disque.

## Capabilities

### New Capabilities

- `clone-state`: Persistance et lecture de l'état d'avancement du clonage (phase courante, phases complétées) dans un fichier `output/clone_state.json`, avec logique de reprise depuis la dernière phase complétée.
- `tmp-cleanup`: Nettoyage automatique du dossier `tmp_images/` à la fin d'un clonage réussi.

### Modified Capabilities

- `image-cache`: Le comportement de cache images existant (ne pas re-télécharger si déjà présent) reste inchangé dans ses exigences — seule l'implémentation s'enrichit d'un déclencheur de nettoyage post-succès, déjà couvert par `tmp-cleanup`.

## Impact

- `main.py` : l'orchestrateur du clone doit vérifier l'état persisté au démarrage et sauter les phases déjà complétées ; il déclenche le nettoyage en fin de succès.
- `output/clone_state.json` : nouveau fichier de persistance (exclu du contrôle de version).
- `tmp_images/` : suppression automatique post-succès (comportement opt-out possible).
- Aucune nouvelle dépendance externe.
