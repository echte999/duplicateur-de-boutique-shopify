## 1. Fondations de l'audit

- [x] 1.1 Créer `cloner/health_audit.py` avec le modèle d'issue, le résumé d'audit, et l'écriture de `output/source_health_audit.json`
- [x] 1.2 Ajouter les helpers de collecte des IDs source nécessaires (`products`, `collections`, `pages`, `blogs`, `articles`) avec pagination adaptée aux APIs déjà utilisées
- [x] 1.3 Ajouter une fonction de haut niveau `run_source_health_audit(client, selected_phases)` qui orchestre les détecteurs selon les phases sélectionnées

## 2. Détecteurs d'objets orphelins

- [x] 2.1 Implémenter le détecteur de menus source en réutilisant la récupération GraphQL existante et en signalant les `resourceId` absents ou d'un type non supporté
- [x] 2.2 Implémenter le détecteur des réductions source pour `entitled_product_ids`, `entitled_collection_ids` et `prerequisite_product_ids` pointant vers des ressources absentes
- [x] 2.3 Implémenter le détecteur du thème source en scannant les assets JSON et en signalant les GIDs/IDs produit-collection qui ne correspondent à aucune ressource source existante

## 3. Intégration au flux de clonage

- [x] 3.1 Appeler l'audit dans `main.py` après chargement de la configuration et avant toute écriture sur la cible
- [x] 3.2 Afficher un résumé terminal de l'audit et demander confirmation à l'utilisateur si au moins une anomalie est détectée
- [x] 3.3 Interrompre proprement le run sans écriture cible ni état de reprise supplémentaire si l'utilisateur refuse de continuer

## 4. Vérifications manuelles

- [x] 4.1 Vérifier qu'un run sans anomalie génère un rapport vide ou sans issue et démarre le clonage sans prompt bloquant
- [x] 4.2 Vérifier qu'un menu pointant vers une ressource supprimée est détecté avant clonage et apparaît dans `source_health_audit.json`
- [x] 4.3 Vérifier qu'une réduction ciblant un produit ou une collection absente est détectée avant clonage
- [x] 4.4 Vérifier qu'un asset JSON de thème contenant un GID produit/collection inexistant est détecté et que l'utilisateur peut choisir d'abandonner le clonage
