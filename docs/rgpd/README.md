# Conformité RGPD de la base de données

Projet Alimendo, projet étudiant (certification RNCP37827, compétence C4).

## Contenu du dossier

| Fichier | Rôle |
|---|---|
| `registre-traitement-alimendo.ods` | Registre des traitements, rempli dans le modèle de registre simplifié de la CNIL. C'est le document de référence. |
| `registre-traitement-alimendo.pdf` | Export lisible du registre (onglets 2 et 3), pour l'annexe du rapport. |
| `procedure_tri.md` | Procédure de tri des données personnelles : règles de conservation, traitements, fréquence, mode opératoire, journal. |
| `../../sql/rgpd_tri.sql` | Requêtes de la procédure de tri. |
| `../../sql/demo_rgpd_comptes.sql` | Comptes fictifs pour tester la procédure. |

## Périmètre du registre

Le registre couvre les traitements de données personnelles réalisés dans la base PostgreSQL. Chaque table a été examinée.

| Table | Données personnelles | Conclusion |
|---|---|---|
| utilisateur | Oui : email, mot de passe haché, rôle, dates de création et de dernière connexion | Fiche ref-001 « Gestion des comptes utilisateurs » |
| role | Non : deux libellés techniques (user, admin) | Hors registre |
| aliment | Non : données nutritionnelles ouvertes (CIQUAL) | Hors registre |
| categorie | Non : catégories d'aliments | Hors registre |
| log_vlm | Non : label reconnu, score de confiance, statut, horodatage. Aucun identifiant d'utilisateur, aucune adresse IP, aucune photo | Hors registre |

Les photos envoyées à la reconnaissance d'aliments sont traitées en mémoire et ne sont jamais enregistrées. Les questions posées au chatbot ne sont pas stockées en base.

## Choix assumés

**Coordonnées du responsable non publiées.** Le projet n'a pas vocation à être ouvert au public : il sert de support de certification. Publier une adresse email personnelle dans un dépôt public exposerait inutilement les données de la responsable du projet. Les champs de contact indiquent donc « Non publiée ». En cas d'ouverture au public, une adresse de contact dédiée serait ajoutée au registre et à la mention d'information de la page Connexion.

**Base légale.** Le modèle simplifié de la CNIL n'a pas de rubrique dédiée. Elle est indiquée dans la fiche ref-001, ligne « Sous-finalité 3 » : exécution d'un contrat (article 6.1.b du RGPD).

**Exemple CNIL retiré.** L'onglet d'exemple du modèle (traitement fictif « Gestion de la paie ») a été supprimé pour éviter toute confusion. Les onglets Tutoriel et Listes sont conservés : les listes déroulantes en dépendent.

## Mettre à jour le registre et refaire le PDF

1. Modifier la fiche dans `registre-traitement-alimendo.ods` (LibreOffice Calc) et changer la date de « Mise à jour du traitement », sur l'onglet 2 et dans la fiche.
2. Fichier, Exporter au format PDF, cocher « PDF balisé ».

La mise en page est enregistrée dans le fichier : seuls les onglets 2 et 3 ont une zone d'impression (sans la colonne des liens vers le site de la CNIL), en paysage, ajustés à la largeur d'une page, sans commentaires ni pied de page. L'export donne 3 pages. Si une ligne ajoutée sort de la zone d'impression, l'étendre avec Format, Plages d'impression, Éditer.
