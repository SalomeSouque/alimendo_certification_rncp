-- Données de démonstration pour la table log_vlm : BASE DE DÉVELOPPEMENT UNIQUEMENT.
--
-- Pourquoi : en local, le VLM tourne peu, la table log_vlm est vide et les requêtes
-- de sql/extract_logs_vlm.sql ne renverraient rien. Ce fichier insère 30 analyses
-- fictives réparties sur les 7 derniers jours pour pouvoir les tester.
--
-- Exécution (depuis la racine du dépôt) :
--   docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/demo_log_vlm.sql
--
-- Pour revenir à une table vide (ne jamais le faire sur une base de production) :
--   DELETE FROM log_vlm;

INSERT INTO log_vlm ("timestamp", label_identifie, score_confiance, statut, id_aliment)
SELECT
    -- Répartition sur 7 jours : g % 7 donne le jour, g donne quelques minutes d'écart.
    now() - (g % 7) * interval '1 day' - g * interval '7 minutes',
    d.label,
    d.confiance,
    d.statut,
    -- Pour un statut « reconnu », on rattache le premier aliment dont le nom commence par le label.
    CASE WHEN d.statut = 'reconnu' THEN (
        SELECT a.id_aliment FROM aliment AS a
        WHERE a.nom ILIKE d.label || '%'
        ORDER BY a.id_aliment
        LIMIT 1
    ) END
FROM generate_series(1, 30) AS g
CROSS JOIN LATERAL (
    -- Environ 60 % reconnu, 27 % non rapproché, 13 % échec.
    SELECT
        CASE
            WHEN g % 15 IN (0, 7) THEN 'echec'
            WHEN g % 15 IN (1, 4, 9, 12) THEN 'non_rapproche'
            ELSE 'reconnu'
        END AS statut,
        CASE
            WHEN g % 15 IN (0, 7) THEN NULL
            WHEN g % 15 IN (1, 4, 9, 12) THEN (ARRAY['Kimchi', 'Tempeh', 'kimchi', 'Kombucha'])[1 + g % 4]
            ELSE (ARRAY['Saumon', 'Tomate', 'Pomme', 'Brocoli', 'Lentille'])[1 + g % 5]
        END AS label,
        CASE
            WHEN g % 15 IN (0, 7) THEN NULL
            ELSE round((0.60 + (g % 10) * 0.035)::numeric, 4)
        END AS confiance
) AS d;
