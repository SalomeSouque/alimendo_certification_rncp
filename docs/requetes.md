# Requêtes SQL d'extraction

Ce document décrit les requêtes SQL qui extraient les données de la base PostgreSQL d'Alimendo :
ce qu'elles récupèrent, pourquoi elles sont écrites ainsi, et comment elles ont été optimisées
(critères C2-CR1, C2-CR2, C2-CR3).

## 1. Objectifs de collecte

La base PostgreSQL contient deux familles de données (voir [`specs_extraction.md`](specs_extraction.md)) :

| Données | Tables | Remplies par | Besoin de l'application |
|---|---|---|---|
| Aliments CIQUAL 2020 | `aliment`, `categorie` | `scripts/import_aliments.py` | Retrouver un aliment, proposer des alternatives de la même catégorie, contrôler la qualité des données |
| Journal du VLM | `log_vlm` | le backend, à chaque analyse photo | Suivre la qualité de la reconnaissance dans le temps (monitoring C11 / C20) |

Système big data : aucun, choix argumenté dans [`specs_extraction.md`](specs_extraction.md), § 6.
Les requêtes sont donc écrites dans le langage de requête du seul système du projet : le SQL de PostgreSQL.

## 2. Fichiers et exécution

| Fichier | Contenu |
|---|---|
| `sql/extract_aliments.sql` | 3 requêtes : `recherche_par_nom`, `aliments_par_categorie`, `couverture_par_categorie` |
| `sql/extract_logs_vlm.sql` | 2 requêtes : `bilan_vlm_par_jour`, `labels_non_rapproches` |
| `sql/demo_log_vlm.sql` | 30 analyses fictives pour tester les requêtes sur `log_vlm` en local (base de développement uniquement) |
| `sql/explain_recherche.sql` | Mesure avant / après de l'optimisation (§ 4.1) |
| `scripts/run_extractions.py` | Exécute les 5 requêtes et affiche les résultats |

Convention : dans un fichier `.sql`, chaque requête commence par une ligne `-- name: nom_de_la_requete`.
Le script découpe le fichier sur ces lignes et exécute chaque requête avec SQLAlchemy (`text()`),
comme le reste du projet. Les paramètres sont nommés (`:terme`, `:categorie`, `:jours`), ce qui garde
les requêtes lisibles et protège des injections SQL : la valeur saisie n'est jamais collée dans le
texte de la requête, elle est envoyée à part.

```bash
# Depuis la racine du dépôt, base démarrée et aliments importés
uv run python scripts/run_extractions.py
uv run python scripts/run_extractions.py --terme "brocolli" --categorie "lait" --jours 7
```

| Option | Défaut | Utilisée par |
|---|---|---|
| `--terme` | `saumon` | `recherche_par_nom` |
| `--categorie` | `poissons` | `aliments_par_categorie` |
| `--jours` | `30` | requêtes sur `log_vlm` |
| `--lignes` | `10` | nombre de lignes affichées par requête |
| `--host` / `--port` | `localhost` / `POSTGRES_PORT` du `.env` | connexion |

Le script se connecte **en lecture seule** : une requête d'extraction qui tenterait d'écrire
échouerait (`cannot execute DELETE in a read-only transaction`).

## 3. Les requêtes et leurs choix

### 3.1 `recherche_par_nom` : retrouver un aliment

| Élément | Choix | Pourquoi |
|---|---|---|
| Sélection | `id_aliment`, `nom`, nom de la catégorie, similarité arrondie | Ce qu'affiche une liste de résultats ; les 23 colonnes nutritionnelles ne servent qu'à la fiche détaillée |
| Jointure | `LEFT JOIN categorie` | Un aliment sans catégorie (1 cas dans CIQUAL) doit quand même être trouvé |
| Filtre | `nom % :terme OR nom ILIKE '%' \|\| :terme \|\| '%'` | `%` tolère les fautes de frappe (similarité trigramme au dessus de 0,2) ; `ILIKE` rattrape un mot court contenu dans un nom long (« riz » dans « Riz blanc, cuit ») |
| Tri | similarité décroissante, puis nom | Le plus proche d'abord ; le nom départage les ex aequo pour un ordre stable |
| Limite | `LIMIT 20` | Une liste de résultats n'a pas besoin de plus |

### 3.2 `aliments_par_categorie` : base des alternatives

| Élément | Choix | Pourquoi |
|---|---|---|
| Sélection | identifiant, nom, catégorie, `fibres`, `omega3`, `graisses_saturees` | Quelques nutriments du score, lisibles dans une capture ; NULL = non mesuré, jamais 0 |
| Jointure | `JOIN categorie` (jointure interne) | On veut uniquement les aliments rattachés à une catégorie |
| Filtre | `c.nom ILIKE '%' \|\| :categorie \|\| '%'` | Les noms CIQUAL sont longs (« viandes, œufs, poissons et assimilés ») : un mot suffit |
| Tri / limite | `ORDER BY a.nom LIMIT 20` | Ordre alphabétique, liste bornée |

### 3.3 `couverture_par_categorie` : contrôle qualité

| Élément | Choix | Pourquoi |
|---|---|---|
| Sélection | nombre d'aliments, nombre de valeurs mesurées pour 3 nutriments | Mesure si le score pourra être calculé dans chaque catégorie |
| Jointure | `categorie LEFT JOIN aliment` | Une catégorie vide apparaît avec 0 au lieu de disparaître |
| Agrégation | `GROUP BY c.nom`, `count(a.omega3)`... | `count(colonne)` ignore les NULL : on compte donc exactement les valeurs mesurées |

### 3.4 `bilan_vlm_par_jour` : qualité de la reconnaissance photo

| Élément | Choix | Pourquoi |
|---|---|---|
| Sélection | jour, nombre d'analyses, nombre par statut, confiance moyenne | Les indicateurs du futur monitoring du VLM |
| Filtre | `"timestamp" >= now() - CAST(:jours AS integer) * interval '1 day'` | Période glissante ; écrit sur la colonne brute pour utiliser son index (§ 4.2) |
| Agrégation | `GROUP BY jour` + `count(*) FILTER (WHERE statut = ...)` | Une seule lecture de la table pour les trois statuts (§ 4.3) |

### 3.5 `labels_non_rapproches` : aliments à ajouter en priorité

| Élément | Choix | Pourquoi |
|---|---|---|
| Conditions | `statut = 'non_rapproche'`, label non NULL, période | Seuls les aliments reconnus par le VLM mais absents de la base |
| Agrégation | `GROUP BY lower(label_identifie)` | « Kimchi » et « kimchi » comptent pour le même aliment |
| Condition après regroupement | `HAVING count(*) >= 2` | Un label vu une seule fois n'est pas une tendance |
| Tri / limite | occurrences décroissantes, `LIMIT 10` | Les priorités d'abord |

## 4. Optimisations

### 4.1 Recherche par nom : écrire le filtre pour que l'index soit utilisable (mesuré)

La migration `0001` crée un index trigramme `ix_aliment_nom_trgm` (GIN, extension `pg_trgm`).
Le backend actuel filtre avec `similarity(nom, terme) > 0.2`. Or PostgreSQL ne peut utiliser un index
que si la condition porte sur un **opérateur** que l'index connaît. `similarity()` est une fonction :
pour connaître son résultat, il faut la calculer sur chaque ligne, donc lire toute la table.
L'opérateur `%` donne le même résultat (vrai si la similarité dépasse le seuil réglé par
`pg_trgm.similarity_threshold`) et, lui, est pris en charge par l'index.

Mesure : `sql/explain_recherche.sql`, avec `EXPLAIN (ANALYZE, BUFFERS)`, terme « saumon ». Seule la
clause `WHERE` change entre AVANT et APRÈS.

| # | Requête | Lecture choisie | Pages lues | Temps d'exécution |
|---|---|---|---|---|
| 1 | AVANT, planificateur libre | `Seq Scan` (toute la table) | 159 | 13,9 ms |
| 2 | APRÈS, planificateur libre | `Seq Scan` (toute la table) | 153 | 13,4 ms |
| 3 | AVANT, lecture complète interdite | `Seq Scan` (index inutilisable) | 153 | 13,5 ms |
| 4 | APRÈS, lecture complète interdite | `Bitmap Index Scan on ix_aliment_nom_trgm` | 102 | **4,2 ms** |

*Mesures sur la base Docker du projet (PostgreSQL 17, 3 184 aliments CIQUAL), le 08/10/2026.
Temps : médiane de 3 exécutions (plan 4 : 7,0 / 3,9 / 4,2 ms, la première exécution lit l'index
à froid). « Pages lues » : ligne `Buffers: shared hit` du plan, en pages de 8 Ko. Les quatre plans
trouvent 24 aliments (`rows=24`) : les deux filtres sont équivalents, seule la façon de lire change.*

**Lecture des résultats.**

- La forme AVANT ne peut **jamais** utiliser l'index, même quand on interdit la lecture complète
  (ligne 3 : toujours `Seq Scan`, les 3 184 lignes sont lues et 3 160 écartées).
- La forme APRÈS **peut** l'utiliser, et elle est alors **3,2 fois plus rapide** que la forme AVANT
  dans les mêmes conditions (4,2 ms contre 13,5 ms, ligne 4 contre ligne 3) en lisant un tiers de
  pages en moins (102 contre 153). L'index présélectionne 663 aliments candidats, PostgreSQL vérifie
  ensuite le seuil exact sur ces seuls candidats et en garde 24.
- Sur 3 184 lignes, le planificateur choisit pourtant la lecture complète (ligne 2) : la table tient
  en 153 pages (environ 1,2 Mo) déjà en mémoire, et il estime qu'un parcours complet coûte moins cher
  que l'index. C'est une décision normale à ce volume. L'optimisation prépare la montée en volume
  (ajout de CIQUAL 2025, de produits Open Food Facts) sans changer la requête.
- Gain secondaire : l'estimation du nombre de lignes est bien plus juste avec `%` (96 estimées contre
  1 104 avec `similarity()`, pour 24 réelles), ce qui aide le planificateur à faire les bons choix.

### 4.2 Filtre sur la date du journal : laisser la colonne indexée intacte

`log_vlm` a un index sur `timestamp` (`ix_log_vlm_timestamp`). Le filtre compare la colonne brute
à une valeur calculée une fois : `"timestamp" >= now() - 30 jours`. Écrire `"timestamp"::date >= ...`
ou `date_trunc('day', "timestamp") >= ...` appliquerait une transformation à chaque ligne et rendrait
l'index inutilisable, pour le même résultat. La conversion en date n'est faite que dans le `SELECT`
et le `GROUP BY`, après filtrage. Non mesuré : en local la table ne contient que les 30 lignes de démonstration,
trop peu pour une mesure significative.

### 4.3 Une seule lecture de table pour plusieurs comptages

`count(*) FILTER (WHERE statut = 'reconnu')` compte les trois statuts en une seule lecture de
`log_vlm`, là où trois sous-requêtes `(SELECT count(*) ... WHERE statut = ...)` la liraient trois fois.

### 4.4 Ne demander que ce qui sert

Les requêtes sélectionnent des colonnes nommées (jamais `SELECT *` : la table `aliment` a 30 colonnes)
et bornent les listes avec `LIMIT`. Moins de données lues, transférées et affichées.

## 5. Vérification

```bash
# 1. Données de démonstration du journal (base de développement uniquement)
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/demo_log_vlm.sql

# 2. Exécution des 5 requêtes : chaque bloc affiche son nombre de lignes
uv run python scripts/run_extractions.py

# 3. Mesure de l'optimisation (lancer 3 fois)
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/explain_recherche.sql

# 4. Tests sans base (découpage des fichiers, paramètres, affichage)
uv run --group dev pytest scripts/tests -q
```

Résultat attendu de l'étape 2 sur CIQUAL : `couverture_par_categorie` renvoie 11 lignes dont la
somme de `nb_aliments` fait 3 183 (le 3 184e aliment n'a pas de catégorie) ; `bilan_vlm_par_jour`
renvoie 7 lignes après chargement de la démonstration.

## 6. Limites et suite

- Le backend (`aliment_repository.rechercher_par_nom`) utilise encore `similarity() > 0.2`.
  Sa correction vers `%` est prévue dans le lot « API REST des données (C5) », qui reprend la
  recherche : il faudra régler `pg_trgm.similarity_threshold` pour chaque connexion du backend.
- Le test de `scripts/tests` n'est pas lancé par la CI (elle ne couvre que `backend/`), comme les
  tests existants de l'import.