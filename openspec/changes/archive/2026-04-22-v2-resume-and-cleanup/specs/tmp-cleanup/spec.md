## ADDED Requirements

### Requirement: Nettoyage automatique de `tmp_images/` après succès complet
Après un clonage entièrement réussi, le système SHALL supprimer le dossier `tmp_images/` et tout son contenu.

#### Scenario: Clonage complet réussi avec images présentes
- **WHEN** toutes les phases de clonage se terminent avec succès et que le dossier `tmp_images/` existe
- **THEN** le système supprime récursivement `tmp_images/` et logue la confirmation de suppression

#### Scenario: Clonage complet réussi sans dossier `tmp_images/`
- **WHEN** toutes les phases de clonage se terminent avec succès et que `tmp_images/` n'existe pas
- **THEN** le système ne lève pas d'erreur et continue normalement

### Requirement: Pas de nettoyage en cas d'échec
En cas d'échec d'une ou plusieurs phases, le système SHALL conserver `tmp_images/` intact pour permettre la reprise sans re-téléchargement.

#### Scenario: Clonage interrompu par une erreur
- **WHEN** une phase échoue (exception, erreur API)
- **THEN** le système NE supprime PAS `tmp_images/` et laisse les images déjà téléchargées disponibles pour un prochain lancement

### Requirement: Le dossier `tmp_images/` sert de cache entre tentatives
Le système SHALL réutiliser les images déjà présentes dans `tmp_images/` lors d'une reprise, sans les re-télécharger.

#### Scenario: Image déjà présente en cache lors d'une reprise
- **WHEN** une phase de clonage tente de télécharger une image déjà présente dans `tmp_images/{resource_id}/filename`
- **THEN** le système utilise le fichier local existant sans effectuer de requête HTTP vers le CDN source
