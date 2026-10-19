-- Requêtes de tri des données personnelles (RGPD).
--
-- Mode d'emploi complet : docs/rgpd/procedure_tri.md.
-- Données personnelles visées : table utilisateur uniquement (voir docs/rgpd/README.md et le registre docs/rgpd/registre-traitement-alimendo.ods).
--
-- Règle de conservation : un compte est supprimé après 3 ans sans connexion.
-- La date de référence est la dernière connexion (last_login, migration 0003).
-- Pour un compte qui ne s'est jamais connecté depuis la migration, on prend
-- la date de création : COALESCE(last_login, created_at).
--
-- Les comptes admin sont exclus de la purge automatique : leur suppression est
-- décidée à la main lors de la revue annuelle du registre.
--
-- ATTENTION : ne jamais exécuter ce fichier en entier (il contient des DELETE).
-- Copier une requête à la fois dans psql, dans l'ordre décrit par la procédure.
-- Toujours détecter (requête 1) avant de supprimer (requête 2).


-- name: detecter_comptes_inactifs
-- But : lister les comptes qui ont dépassé la durée de conservation.
-- Ne modifie rien. Le nombre de lignes est à noter dans le journal de tri.
SELECT
    u.id_utilisateur,
    u.email,
    u.created_at,
    u.last_login,
    COALESCE(u.last_login, u.created_at) AS derniere_activite
FROM utilisateur AS u
JOIN role AS r ON r.id_role = u.id_role
WHERE r.libelle <> 'admin'
  AND COALESCE(u.last_login, u.created_at) < now() - interval '3 years'
ORDER BY derniere_activite;


-- name: supprimer_comptes_inactifs
-- But : supprimer les comptes listés par la requête précédente.
-- Même condition que detecter_comptes_inactifs : les deux requêtes doivent
-- rester identiques. RETURNING affiche ce qui a été supprimé.
-- À lancer dans une transaction (BEGIN ... COMMIT) pour pouvoir annuler.
DELETE FROM utilisateur AS u
USING role AS r
WHERE r.id_role = u.id_role
  AND r.libelle <> 'admin'
  AND COALESCE(u.last_login, u.created_at) < now() - interval '3 years'
RETURNING u.id_utilisateur, u.email;


-- name: supprimer_compte_sur_demande
-- But : droit à l'effacement. Supprimer le compte d'une personne qui le demande.
-- :email = adresse du compte, en minuscules (l'application normalise les emails).
-- Vérifier d'abord que la demande vient bien de la titulaire du compte.
DELETE FROM utilisateur
WHERE email = lower(trim(:'email'))
RETURNING id_utilisateur, email;


-- name: controler_apres_tri
-- But : vérifier qu'il ne reste aucun compte hors durée de conservation.
-- Résultat attendu : 0.
SELECT count(*) AS comptes_hors_delai
FROM utilisateur AS u
JOIN role AS r ON r.id_role = u.id_role
WHERE r.libelle <> 'admin'
  AND COALESCE(u.last_login, u.created_at) < now() - interval '3 years';
