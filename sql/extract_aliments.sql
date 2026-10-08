-- Requêtes d'extraction sur les aliments (tables aliment et categorie).
--
-- Objectif de collecte : récupérer, depuis la base remplie par l'import CIQUAL,
-- les données dont l'application a besoin pour ses trois usages principaux :
--   1. retrouver un aliment à partir de ce que tape l'utilisatrice ;
--   2. lister les aliments d'une catégorie (base des alternatives proposées) ;
--   3. vérifier la couverture des données par catégorie (contrôle qualité).
--
-- Exécution : scripts/run_extractions.py lit ce fichier, découpe les requêtes
-- sur les lignes « -- name: » et les exécute une par une.
-- Les paramètres s'écrivent :nom (ex. :terme), la valeur est fournie par le script.
-- Documentation complète des choix : docs/requetes.md


-- name: recherche_par_nom
-- But : retrouver un aliment malgré une faute de frappe ou un nom incomplet.
-- :terme = texte saisi (ex. « saumon »).
-- Prérequis : le script règle pg_trgm.similarity_threshold à 0.2 à la connexion (même seuil que le backend).
SELECT
    a.id_aliment,
    a.nom,
    c.nom AS categorie,
    round(similarity(a.nom, :terme)::numeric, 3) AS similarite
FROM aliment AS a
-- LEFT JOIN : un aliment sans catégorie (1 cas dans CIQUAL) doit quand même être trouvé.
LEFT JOIN categorie AS c ON c.id_categorie = a.id_categorie
-- « % » = similarité trigramme au dessus du seuil. Contrairement à similarity() > 0.2,
-- cet opérateur peut utiliser l'index ix_aliment_nom_trgm (voir docs/requetes.md § 4).
-- Le ILIKE rattrape les noms courts contenus dans un nom long (« riz » dans « riz blanc cuit »).
WHERE a.nom % :terme
   OR a.nom ILIKE '%' || :terme || '%'
-- Le plus proche d'abord, puis le nom pour un ordre stable entre deux appels.
ORDER BY similarite DESC, a.nom
LIMIT 20;


-- name: aliments_par_categorie
-- But : lister les aliments d'une catégorie avec les nutriments affichés dans la fiche.
-- C'est la base de la recherche d'alternatives (même catégorie que l'aliment consulté).
-- :categorie = mot contenu dans le nom de la catégorie (ex. « poissons »).
SELECT
    a.id_aliment,
    a.nom,
    c.nom AS categorie,
    a.fibres,
    a.omega3,
    a.graisses_saturees
FROM aliment AS a
-- INNER JOIN : ici on veut uniquement les aliments rattachés à une catégorie.
JOIN categorie AS c ON c.id_categorie = a.id_categorie
WHERE c.nom ILIKE '%' || :categorie || '%'
ORDER BY a.nom
LIMIT 20;


-- name: couverture_par_categorie
-- But : contrôle qualité. Combien d'aliments par catégorie, et pour combien
-- les nutriments clés sont réellement mesurés (NULL = non mesuré, jamais 0).
-- Pas de paramètre.
SELECT
    c.nom AS categorie,
    count(a.id_aliment) AS nb_aliments,
    -- count(colonne) ignore les NULL : on compte donc les valeurs mesurées.
    count(a.omega3) AS omega3_mesure,
    count(a.fibres) AS fibres_mesure,
    count(a.vitamine_d) AS vitamine_d_mesure
FROM categorie AS c
-- LEFT JOIN depuis categorie : une catégorie vide apparaît avec 0 au lieu de disparaître.
LEFT JOIN aliment AS a ON a.id_categorie = c.id_categorie
GROUP BY c.nom
ORDER BY nb_aliments DESC;
