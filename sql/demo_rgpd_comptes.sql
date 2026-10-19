-- Comptes fictifs pour tester la procédure de tri RGPD (sql/rgpd_tri.sql).
--
-- À n'utiliser qu'en local, sur une base de développement.
-- Cinq cas, un par situation à vérifier :
--   ancienne@example.com : dernière connexion il y a 4 ans      : doit être supprimé
--   jamais@example.com   : créé il y a 4 ans, jamais connecté   : doit être supprimé
--   active@example.com   : créé il y a 5 ans, connecté récemment : doit rester
--   admin@example.com    : admin inactif depuis 5 ans           : doit rester (exclu de la purge)
--   demande@example.com  : compte récent                        : sert au test de suppression sur demande
--
-- Le mot de passe est un faux hash : ces comptes ne peuvent pas se connecter.
-- Relançable : ON CONFLICT évite les doublons sur l'email.

INSERT INTO utilisateur (email, password, id_role, created_at, last_login)
VALUES
    ('ancienne@example.com', repeat('x', 60),
     (SELECT id_role FROM role WHERE libelle = 'user'),
     now() - interval '5 years', now() - interval '4 years'),
    ('jamais@example.com', repeat('x', 60),
     (SELECT id_role FROM role WHERE libelle = 'user'),
     now() - interval '4 years', NULL),
    ('active@example.com', repeat('x', 60),
     (SELECT id_role FROM role WHERE libelle = 'user'),
     now() - interval '5 years', now() - interval '2 days'),
    ('admin@example.com', repeat('x', 60),
     (SELECT id_role FROM role WHERE libelle = 'admin'),
     now() - interval '5 years', NULL),
    ('demande@example.com', repeat('x', 60),
     (SELECT id_role FROM role WHERE libelle = 'user'),
     now(), now())
ON CONFLICT (email) DO NOTHING;
