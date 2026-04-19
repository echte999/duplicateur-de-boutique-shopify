# Backlog — tâches reportées

## Endpoint GET /api/report

**Bloqué par** : interface FastAPI non encore construite (`main.py` est actuellement un script CLI).

**Tâche** : Ajouter un endpoint `GET /api/report` dans `main.py` (une fois converti en app FastAPI) qui lit `output/clone_report.json` et retourne son contenu JSON, ou une liste vide si le fichier n'existe pas encore.

**Contexte** : Tâche 3.3 du change `mvp-domain-mapping-report` (archivé le 2026-04-19). La spec correspondante est dans `openspec/specs/clone-report/spec.md`.
