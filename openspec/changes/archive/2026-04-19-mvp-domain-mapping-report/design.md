## Context

Les trois modules manquants (`domain.py`, `mapping.py`, `report.py`) sont des cross-cutting concerns : ils sont appelés par toutes les phases de clonage existantes (products, collections, theme). Sans eux, le clone produit une boutique avec des liens cassés et des IDs source invalides dans le thème.

État actuel : les fichiers `domain.py` et `mapping.py` n'existent pas encore, ou sont vides. Les phases existantes ne font aucun remapping. `report.py` n'existe pas.

## Goals / Non-Goals

**Goals:**
- `domain.py` : fonction `remap(text, source_domains, target_domain)` applicable à n'importe quelle chaîne (HTML, JSON sérialisé, plain text)
- `mapping.py` : classe `IDMap` avec méthodes `register(type, src_id, tgt_id)`, `resolve(src_id)`, `save()`, `load()` — persistée dans `output/id_map.json`
- `report.py` : fonction `add_entry(type, src_id, tgt_id, status)` + `generate()` qui écrit `output/clone_report.json`
- Intégration dans products.py, collections.py, theme.py sans modifier leur logique métier

**Non-Goals:**
- Remapping de domaine dans les phases V1 (pages, blogs, menus, politiques) — hors périmètre MVP
- Interface web pour consulter le rapport (déjà prévu dans main.py via `/report`)
- Nettoyage automatique de tmp_images/ (V2)

## Decisions

### 1. `domain.py` : regex multi-domaines, pas de parsing HTML

Approche : `re.sub()` sur la chaîne brute avec les deux patterns source (myshopify + custom domain). Pas de parsing BeautifulSoup.

**Pourquoi** : les contenus Shopify sont des chaînes JSON ou HTML stockées en texte — un remplacement regex est suffisant, prévisible et sans dépendance externe. BeautifulSoup casserait les attributs Liquid et les templates partiels.

Alternative rejetée : parser le HTML et ne remplacer que href/src. Trop fragile sur les templates Shopify qui mélangent Liquid et HTML.

### 2. `mapping.py` : dict en mémoire + persistance JSON après chaque phase

La table est un dict Python `{ str(src_id): str(tgt_id) }` chargé au démarrage et sauvegardé après chaque phase via `save()`.

**Pourquoi** : simple, sans dépendance, compatible avec la reprise sur erreur (V2). Le fichier `output/id_map.json` est la source de vérité entre les phases.

Alternative rejetée : SQLite. Surdimensionné pour quelques milliers d'IDs.

### 3. `report.py` : liste d'entrées accumulées en mémoire, flush en fin de clonage

Chaque phase appelle `report.add_entry()`. En fin de clonage, `main.py` appelle `report.generate()` qui écrit tout d'un coup.

**Pourquoi** : écrire entrée par entrée générerait des I/O inutiles. Le flush unique garantit un fichier cohérent même si une phase échoue partiellement.

### 4. Intégration : les phases appellent domain/mapping explicitement

Chaque phase reçoit les instances `id_map` et `domain_remapper` via paramètres (pas de globals).

**Pourquoi** : testabilité et clarté — on voit exactement ce que chaque phase utilise.

## Risks / Trade-offs

- [Regex trop large] Le remplacement peut affecter des URLs externes qui contiendraient par hasard le domaine source → Mitigation : les domaines Shopify (`.myshopify.com`) sont suffisamment uniques pour que le risque soit négligeable
- [IDMap incomplète] Si une phase échoue à mi-chemin, les IDs non enregistrés ne seront pas résolus dans les phases suivantes → Mitigation : la reprise sur erreur (V2) rechargera `id_map.json` depuis le disque
- [Rapport partiel] Si `generate()` n'est pas appelé (crash), le rapport est absent → Mitigation : appel dans un bloc `finally` dans `main.py`
