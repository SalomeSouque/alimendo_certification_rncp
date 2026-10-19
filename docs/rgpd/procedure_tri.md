# Procédure de tri des données personnelles

Projet Alimendo, projet étudiant. Version 1.0 du 12/10/2026.

Cette procédure applique les durées de conservation fixées dans le registre des traitements (docs/rgpd/registre-traitement-alimendo.ods, fiche ref-001). Elle concerne la seule table qui contient des données personnelles : `utilisateur`.

## 1. Règles de conservation

| Donnée | Règle |
|---|---|
| Compte utilisateur inactif | Supprimé quand la dernière activité date de plus de 3 ans (durée recommandée par la CNIL pour un compte inactif). |
| Compte dont la personne demande la suppression | Supprimé dès que la demande est vérifiée, au plus tard un mois après la réception (article 12.3 du RGPD). |
| Compte administrateur | Exclu de la suppression automatique, revu à la main chaque année. |

La dernière activité est la date de dernière connexion (`last_login`). Si un compte ne s'est jamais connecté depuis l'ajout de cette colonne, on retient sa date de création (`created_at`).

## 2. Traitements de conformité et fréquence

| N° | Traitement | Manuel ou automatisé | Fréquence | Requête |
|---|---|---|---|---|
| 1 | Enregistrer la date de dernière connexion | Automatisé (code de l'API, à chaque connexion réussie) | En continu | Aucune |
| 2 | Détecter les comptes inactifs depuis plus de 3 ans | Manuel | Une fois par mois | `detecter_comptes_inactifs` |
| 3 | Supprimer les comptes détectés | Manuel | Une fois par mois, juste après le traitement 2 | `supprimer_comptes_inactifs` |
| 4 | Vérifier qu'il ne reste aucun compte hors délai | Manuel | Une fois par mois, juste après le traitement 3 | `controler_apres_tri` |
| 5 | Supprimer un compte à la demande de la personne | Manuel | À chaque demande, sous un mois | `supprimer_compte_sur_demande` |
| 6 | Revue du registre et des données stockées : vérifier qu'aucune nouvelle donnée personnelle n'a été ajoutée sans être inscrite au registre, et revoir les comptes admin | Manuel | Une fois par an, et à chaque migration qui modifie la table `utilisateur` | Lecture du schéma (`\d utilisateur`) |

Les traitements 2 à 4 restent manuels par choix : le volume de comptes est très faible, et une relecture humaine avant toute suppression évite d'effacer un compte par erreur.

## 3. Mode opératoire mensuel

Les requêtes sont dans `sql/rgpd_tri.sql`. Ce fichier contient des suppressions : il ne faut jamais l'exécuter en entier. On copie une requête à la fois.

1. Ouvrir une session psql sur la base :

   ```bash
   docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
   ```

2. Copier et lancer la requête `detecter_comptes_inactifs`. Noter le nombre de lignes. Si le résultat est vide, passer directement à l'étape 5.
3. Relire la liste. Si un compte ne doit pas être supprimé, arrêter et noter la raison dans le journal.
4. Ouvrir une transaction, lancer la suppression, vérifier que le nombre de lignes supprimées est le même qu'à l'étape 2, puis valider :

   ```sql
   BEGIN;
   -- coller ici la requête supprimer_comptes_inactifs
   COMMIT;   -- ou ROLLBACK; si le nombre ne correspond pas
   ```

5. Lancer `controler_apres_tri`. Le résultat attendu est 0.
6. Remplir une ligne du journal de tri (section 5).

## 4. Mode opératoire pour une demande de suppression

1. Vérifier que la demande vient de l'adresse email du compte (répondre à cette adresse pour confirmer).
2. Lancer la requête en passant l'email en variable psql :

   ```bash
   docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v email=adresse@exemple.fr'
   ```

   puis copier la requête `supprimer_compte_sur_demande`. Une ligne doit être renvoyée.
3. Confirmer la suppression à la personne et noter la demande dans le journal (date, sans recopier l'email).

## 5. Journal de tri

| Date | Traitement | Comptes détectés | Comptes supprimés | Contrôle (0 attendu) | Remarque |
|---|---|---|---|---|---|
| | | | | | |

## 6. Limites connues

Le projet n'est pas ouvert au public : aucune adresse de contact n'est publiée, les demandes sont adressées directement à l'administratrice. En cas d'ouverture au public, une adresse dédiée devra être ajoutée au registre et à la mention d'information. L'application n'envoie pas d'email : la personne n'est pas prévenue avant la suppression de son compte inactif. Si des sauvegardes de la base sont mises en place, leur durée de rétention devra être ajoutée à ce document : un compte supprimé reste présent dans les sauvegardes jusqu'à leur expiration.
