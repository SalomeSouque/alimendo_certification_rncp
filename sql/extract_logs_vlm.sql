-- Requêtes d'extraction sur le journal du VLM (table log_vlm).
--
-- Objectif de collecte : suivre la qualité de la reconnaissance photo dans le temps.
-- Ces chiffres serviront au monitoring du modèle (C11) et de l'application (C20).
--
-- Statuts possibles (voir backend/app/db/models/log_vlm.py) :
--   reconnu       = label identifié et rapproché d'un aliment en base ;
--   non_rapproche = label identifié mais absent de la base ;
--   echec         = le VLM n'a rien identifié.
--
-- En local la table est souvent vide : sql/demo_log_vlm.sql insère des logs fictifs.
-- Exécution : scripts/run_extractions.py (découpage sur les lignes « -- name: »).


-- name: bilan_vlm_par_jour
-- But : nombre d'analyses photo par jour, réparties par statut, et confiance moyenne.
-- :jours = nombre de jours à remonter (ex. 30).
SELECT
    l."timestamp"::date AS jour,
    count(*) AS analyses,
    -- FILTER compte seulement les lignes qui vérifient la condition :
    -- une seule lecture de la table au lieu de trois sous-requêtes.
    count(*) FILTER (WHERE l.statut = 'reconnu') AS reconnues,
    count(*) FILTER (WHERE l.statut = 'non_rapproche') AS non_rapprochees,
    count(*) FILTER (WHERE l.statut = 'echec') AS echecs,
    round(avg(l.score_confiance), 3) AS confiance_moyenne
FROM log_vlm AS l
-- Filtre écrit directement sur la colonne indexée (ix_log_vlm_timestamp) :
-- PostgreSQL peut lire seulement la période demandée (voir docs/requetes.md § 4).
WHERE l."timestamp" >= now() - CAST(:jours AS integer) * interval '1 day'
GROUP BY jour
ORDER BY jour;


-- name: labels_non_rapproches
-- But : aliments photographiés mais absents de la base, les plus fréquents d'abord.
-- Sert à décider quels aliments ajouter en priorité.
-- :jours = nombre de jours à remonter (ex. 30).
SELECT
    lower(l.label_identifie) AS label,
    count(*) AS occurrences,
    max(l."timestamp") AS derniere_fois
FROM log_vlm AS l
WHERE l.statut = 'non_rapproche'
  AND l.label_identifie IS NOT NULL
  AND l."timestamp" >= now() - CAST(:jours AS integer) * interval '1 day'
-- lower() regroupe « Kimchi » et « kimchi ».
GROUP BY lower(l.label_identifie)
-- HAVING filtre après le regroupement : on écarte les labels vus une seule fois.
HAVING count(*) >= 2
ORDER BY occurrences DESC, label
LIMIT 10;
