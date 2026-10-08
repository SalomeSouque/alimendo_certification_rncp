-- Mesure de l'optimisation de la recherche par nom (critère C2-CR3).
--
-- Question : la recherche utilise-t-elle l'index trigramme ix_aliment_nom_trgm
-- créé par la migration 0001 ?
--   AVANT : forme actuelle du backend (aliment_repository.rechercher_par_nom),
--           filtre similarity(nom, terme) > 0.2
--   APRÈS : forme de sql/extract_aliments.sql, filtre nom % terme
-- Seule la clause WHERE change entre les deux : c'est la seule variable mesurée.
--
-- Exécution (depuis la racine du dépôt), lancer 3 fois et garder la valeur du milieu :
--   docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/explain_recherche.sql
--
-- À lire dans chaque plan : « Seq Scan » (toute la table est lue) ou
-- « Bitmap Index Scan on ix_aliment_nom_trgm » (l'index est utilisé), et « Execution Time ».

-- Même seuil que le backend : « % » renvoie vrai si similarity() dépasse ce seuil.
SET pg_trgm.similarity_threshold = 0.2;

\echo '1. AVANT : similarity() > 0.2 (choix libre du planificateur)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT a.id_aliment, a.nom
FROM aliment AS a
WHERE similarity(a.nom, 'saumon') > 0.2 OR a.nom ILIKE '%saumon%'
ORDER BY similarity(a.nom, 'saumon') DESC, a.nom
LIMIT 20;

\echo '2. APRÈS : opérateur % (choix libre du planificateur)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT a.id_aliment, a.nom
FROM aliment AS a
WHERE a.nom % 'saumon' OR a.nom ILIKE '%saumon%'
ORDER BY similarity(a.nom, 'saumon') DESC, a.nom
LIMIT 20;

-- Sur ~3 200 lignes, le planificateur peut juger qu'une lecture complète coûte moins
-- cher que l'index. Pour vérifier que l'index est UTILISABLE, on interdit la lecture
-- complète le temps d'une transaction annulée (rien n'est modifié durablement).
-- jit = off : évite que la compilation JIT fausse le temps mesuré.
BEGIN;
SET LOCAL enable_seqscan = off;
SET LOCAL jit = off;

\echo '3. AVANT avec lecture complète interdite : l index reste inutilisable'
EXPLAIN (ANALYZE, BUFFERS)
SELECT a.id_aliment, a.nom
FROM aliment AS a
WHERE similarity(a.nom, 'saumon') > 0.2 OR a.nom ILIKE '%saumon%'
ORDER BY similarity(a.nom, 'saumon') DESC, a.nom
LIMIT 20;

\echo '4. APRÈS avec lecture complète interdite : l index est utilisé'
EXPLAIN (ANALYZE, BUFFERS)
SELECT a.id_aliment, a.nom
FROM aliment AS a
WHERE a.nom % 'saumon' OR a.nom ILIKE '%saumon%'
ORDER BY similarity(a.nom, 'saumon') DESC, a.nom
LIMIT 20;

ROLLBACK;
