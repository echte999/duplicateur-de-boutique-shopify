## Why

Les politiques du site (remboursement, confidentialité, CGV, etc.) contiennent du contenu HTML qui référence le nom et le domaine de la boutique source. Sans cette phase, la boutique cible affiche des politiques pointant vers la mauvaise boutique, ce qui est visible par les visiteurs et peut poser des problèmes légaux.

## What Changes

- Ajout d'une phase `policies` dans l'ordre de clonage (phase 6)
- Lecture de toutes les politiques depuis la boutique source via l'API REST Shopify
- Application du remapping de domaine sur le contenu HTML de chaque politique
- Remplacement du nom de la boutique source par le nom de la boutique cible dans le corps des politiques
- Écriture des politiques remappées sur la boutique cible
- Ajout des politiques au rapport post-clonage

## Capabilities

### New Capabilities
- `policy-cloning`: Lecture, remapping (domaine + nom de boutique) et écriture des politiques du site

### Modified Capabilities
- `domain-remapping`: Ajout du remplacement du nom de boutique source (pas seulement le domaine)

## Impact

- Nouveau fichier `cloner/phases/policies.py`
- `main.py` : ajout de l'appel à la phase policies dans l'orchestrateur
- `cloner/domain.py` : extension pour remplacer aussi le nom de la boutique source
- `cloner/report.py` : inclusion des politiques dans le rapport
- API REST utilisée : `GET /admin/api/2024-01/policies.json` (lecture seule — Shopify n'a pas d'endpoint d'écriture direct, les politiques se mettent à jour via `PUT /admin/api/2024-01/policies/<type>.json`)
