-- Rôle de connexion en lecture seule pour l'accès direct à la base (critère C5).
--
-- Usage : voir docs/acces_base.md. Le mot de passe n'est jamais écrit ici,
-- il est passé à psql par la variable mdp_lecture.
--
-- Le rôle lit uniquement les tables sans donnée personnelle :
-- aliment, categorie et log_vlm. Les tables utilisateur et role restent
-- inaccessibles (RGPD : minimisation des accès).

CREATE ROLE alimendo_lecture LOGIN PASSWORD :'mdp_lecture';

-- Toute transaction de ce rôle est en lecture seule, même si on oublie de le préciser.
ALTER ROLE alimendo_lecture SET default_transaction_read_only = on;

GRANT CONNECT ON DATABASE :"DBNAME" TO alimendo_lecture;
GRANT USAGE ON SCHEMA public TO alimendo_lecture;
GRANT SELECT ON aliment, categorie, log_vlm TO alimendo_lecture;

-- Pour retirer le rôle :
-- REVOKE ALL ON aliment, categorie, log_vlm FROM alimendo_lecture;
-- REVOKE USAGE ON SCHEMA public FROM alimendo_lecture;
-- REVOKE CONNECT ON DATABASE alimendo FROM alimendo_lecture;
-- DROP ROLE alimendo_lecture;
