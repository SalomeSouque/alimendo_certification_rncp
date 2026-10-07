# Scripts

| Script | Rôle |
|---|---|
| `ciqual_clean.py` | Nettoyage reproductible de la table CIQUAL 2020 → jeu d'aliments prêt pour PostgreSQL |
| `import_aliments.py` | Import du jeu CIQUAL nettoyé dans PostgreSQL, relançable sans doublon (doc : README racine, « Import des données ») |
| `smoke_test_mistral.py` | Test de connectivité vers Mistral La Plateforme (C8) |

---

# `ciqual_clean.py` — nettoyage de la table CIQUAL

Transforme le fichier brut CIQUAL 2020 (ANSES) en un jeu d'aliments propre, aligné sur la table
`aliment` du backend (`backend/app/db/models/aliment.py`).

Chaque règle a été établie et **mesurée** dans le notebook
[`03_nettoyage_ciqual.ipynb`](https://github.com/SalomeSouque/alimendo_data_science) (dépôt
`alimendo_data_science`), qui sert de justification. Le script applique ces décisions en une commande.
L'équivalence est vérifiée : le CSV produit par le script est identique à celui du notebook
(`pd.testing.assert_frame_equal`, cellule 6.2).

## 1. Dépendances

| Élément | Version / détail |
|---|---|
| Python | ≥ 3.13 (voir `pyproject.toml`) |
| Groupe de dépendances `data` | `pandas`, `numpy`, `xlrd` (lecture `.xls`), `openpyxl` (lecture `.xlsx`), `requests` |
| Tests | groupe `dev` (`pytest`) |
| Source | **CIQUAL 2020**, ANSES — data.gouv.fr — Licence Ouverte / Etalab 2.0. Citation : *Anses. 2020. Table de composition nutritionnelle des aliments Ciqual.* |

Installation :

```bash
uv sync --group data --group dev
```

> **Pourquoi CIQUAL 2020 et pas 2025 ?** Une version 2025 existe (publiée le 19/11/2025, 3 484 aliments).
> Le référentiel de score v1.0 est calibré sur la version 2020 ; changer de version imposerait de recalibrer
> les repères et de passer en v2.0. La version est une constante (`CIQUAL_VERSION`) du script.

## 2. Commandes

Depuis la racine du dépôt :

```bash
# Nettoyage complet (télécharge CIQUAL si absent) + test de non-régression des repères v1.0
uv run --group data python scripts/ciqual_clean.py --landmarks backend/app/domain/score/landmarks_v1.json

# Tests unitaires des règles (sans réseau ni données, < 1 s)
uv run --group data --group dev pytest scripts/tests -q
```

| Option | Défaut | Effet |
|---|---|---|
| `--raw` | `data/ciqual/raw/ciqual_2020.xls` | Fichier source (téléchargé s'il est absent) |
| `--out` | `data/ciqual/clean/` | Dossier des sorties |
| `--force-download` | non | Re-télécharge la source même si elle est présente |
| `--landmarks` | aucun | Active le test de non-régression contre `landmarks_v1.json` |

**Codes de sortie** : `0` succès ; `1` erreur (téléchargement impossible, colonne introuvable ou ambiguë,
unité inattendue, catégorie ambiguë…). Le script préfère s'arrêter plutôt que produire un jeu faux.

**Sorties** (dossier `data/ciqual/clean/`, non versionné — `data/ciqual/` est dans `.gitignore`) :

| Fichier | Contenu |
|---|---|
| `aliments_ciqual_2020_clean.csv` | Jeu nettoyé : `code_ciqual`, `nom`, `categorie`, `source`, `energie` + 23 paramètres du score (pleine précision, NULL = vide) |
| `categories_ciqual_2020.csv` | Les 11 catégories (groupes CIQUAL) |
| `rejets_ciqual_2020.csv` | Chaque ligne écartée avec son motif |
| `rapport_nettoyage_ciqual_2020.json` | Rapport : empreinte SHA-256 de la source, comptages par étape, formats, règles, contrôles |
| `ciqual_clean.log` | Journal d'exécution |

## 3. Enchaînement logique

Résultats obtenus sur CIQUAL 2020 (exécution du 07/10/2026, pandas 3.0.5) :

| # | Étape | Résultat |
|---|---|---|
| 1 | Téléchargement (idempotent) et chargement **brut** : toutes les cellules lues comme du texte | 3 186 lignes × 76 colonnes, format `.xls (OLE2)` |
| 2 | Identification des formats non normalisés sur les 67 colonnes nutritionnelles | voir tableau §4.1 |
| 3 | Conversion en nombres selon le référentiel v1.0 | 148 210 valeurs, 65 252 NULL |
| 4 | Dictionnaire de données : 1 mot-clé = 1 colonne, unité contrôlée | 27 colonnes, toutes dans l'unité attendue |
| 5 | Test de non-régression : repères recalculés vs `landmarks_v1.json` | **identiques** (écart 0) |
| 6 | Doublons d'`alim_code` : fusion si aucune contradiction | 1 doublon fusionné → **3 185 lignes** |
| 7 | Construction de la table : noms logiques, oméga, catégorie réparée, noms normalisés | 44 catégories réparées, 1 aliment sans catégorie |
| 8 | Règles d'entrée corrompue | 1 entrée rejetée → **3 184 lignes** |
| 9 | Contrôle du schéma PostgreSQL, puis export | 1 avertissement (`beta_carotene`, voir §4.5) |

## 4. Choix de nettoyage et d'homogénéisation

### 4.1 Formats des valeurs (notebook § 2)

| Format brut | Cellules | Conversion | Justification |
|---|---|---|---|
| Nombre à virgule (`12,5`) | 83 057 (38,9 %) | `12.5` | Décimale française |
| Nombre à point (`12.5`) | 46 619 (21,8 %) | inchangé | Cellule numérique Excel |
| Tiret `-` | 63 688 (29,8 %) | **NULL** | « Teneur non connue » (doc. ANSES) — **jamais 0** |
| Cellule vide | 1 564 (0,7 %) | **NULL** | Signature des aliments moyens (115/116 en ont) ; même sens que `-` |
| `< X` | 16 630 (7,8 %) | `0` | Convention du référentiel v1.0 (« lower bound » EFSA) |
| `traces` | 1 904 (0,9 %) | `0` | Convention du référentiel v1.0 |
| Autre texte (`#REF!`…) | 0 | NULL | Règle du référentiel conservée par sécurité |

Garde-fous : 16 630 / 16 630 « < X » bien formés, une seule graphie de « traces », 0 espace parasite.
La règle « non mesuré ≠ 0 » est essentielle : confondre les deux biaiserait le score vers le neutre.

**Limite documentée** : la convention `< X → 0` pèse fortement sur le sélénium (29,9 % des aliments),
le DHA (24,9 %), l'EPA (22,8 %), l'acide arachidonique (18,5 %) et la vitamine D (18,0 %).
Elle est conservée car figée dans le référentiel v1.0 (piste V2 : analyse de sensibilité avec X/2).

### 4.2 Unités et noms (notebook § 3)

- Les 27 colonnes utilisées sont retrouvées par mot-clé, avec la garantie qu'un mot-clé ne désigne
  **qu'une seule** colonne (sinon arrêt).
- **Aucune conversion d'unité** n'est nécessaire : toutes les colonnes sont déjà dans l'unité du référentiel
  (g, mg ou µg pour 100 g ; kcal pour l'énergie). Le contrôle arrête le script si une version future change
  d'unité. La conversion g → mg/µg relève de l'ETL Open Food Facts, qui exprime tout en grammes.
- **Oméga** : `omega3` = ALA + EPA + DHA, `omega6` = linoléique + arachidonique ; NULL si aucun constituant
  n'est mesuré (`min_count=1`).
- **Noms** : espaces multiples ramenés à un seul (5 noms modifiés). 0 caractère d'encodage suspect.
  Longueurs max : 149 (limite 255) et 43 pour les catégories (limite 100).

### 4.3 Doublons et catégories (notebook § 1)

- **Doublon `alim_code` 9621 (Son de blé)** : 2 lignes dans deux sous-groupes, **0 valeur contradictoire**
  (l'une porte 63 valeurs, l'autre 1 absente de la première) → fusion sans perte. Règle générale du script :
  fusion si aucune contradiction, rejet de toutes les lignes du code sinon.
- **Catégorie = groupe CIQUAL** (11 valeurs), comme le suppose `CATEGORIES_EXCLUES` du backend.
- **44 aliments du groupe `03`** (farines, amidons, pâtes) ont un nom de groupe vide alors que le code est
  présent : nom réparé depuis le code (correspondance code → nom vérifiée univoque).
- **« Dessert (aliment moyen) »** (code `00`, sans groupe) : conservé avec une catégorie NULL
  (`id_categorie` est nullable) ; il n'est pas corrompu.

### 4.4 Entrées corrompues (notebook § 4)

Une entrée corrompue est ici une entrée **physiquement impossible**. Les aliments simplement non scorables
(complétude < 50 %, apport < 1 g) sont **conservés** : ils relèvent du calcul du score à la volée, et
l'application doit pouvoir afficher « Score indisponible ».

| Règle | Seuil | Aliments | Justification |
|---|---|---|---|
| Valeur négative | < 0 | 0 | Impossible physiquement |
| Teneur > 100 g/100 g | toutes unités ramenées en g | 0 | Impossible physiquement |
| Sous-ensemble > ensemble (AG saturés, AG totaux, oméga > lipides ; sucres > glucides) | + 1 g | 0 | Écarts observés ≤ 0,6 g = arrondis ou convention `< X` |
| Somme de composition | > 105 g | 1 | Plafond observé ≈ 103,1 g (constituants analysés séparément) |
| Énergie déclarée vs recalculée (Règlement UE 1169/2011, annexe XIV) | > 20 % **et** > 20 kcal | 1 | Le % seul pénalise les aliments peu énergétiques |

**Point de méthode** : dans CIQUAL, les « glucides » incluent les polyols (définition UE). Les deux derniers
contrôles retirent donc les polyols des glucides pour ne pas les compter deux fois (vérifié sur 174 aliments,
0 contre-exemple). Sans cette correction, 17 aliments (édulcorants, chewing-gums, fruits secs) auraient été
rejetés à tort.

**Entrée rejetée** : *Gnocchi, cuit (aliment moyen)* (25579) — somme de composition 106,45 g et énergie
déclarée 181 kcal pour 236 recalculées (−30 %) : deux contrôles indépendants.

### 4.5 Compatibilité avec la base (notebook § 5)

- **Débordement** : le bêta-carotène de 2 algues séchées (wakamé 104 000 µg, kombu 393 000 µg) dépassait
  `NUMERIC(8,3)`. La donnée est conservée ; c'est le schéma qui a évolué (migration 0002).
- **Précision** : à 3 décimales, 2 aliments changent de niveau de score (arrondi de l'oméga-3 près d'un seuil) ;
  à 4 décimales, aucun.
- -> **Migration Alembic 0002 appliquée** : colonnes nutritionnelles en `NUMERIC(10,4)` et
  `SCHEMA_NUTRIMENTS = (10, 4)` dans le script : plus d'avertissement de débordement.
- Le CSV garde la pleine précision de la source : l'arrondi est une décision du schéma, pas du nettoyage.

### 4.6 Non-régression avec le référentiel de score v1.0

Les repères (médiane, p10, p90) recalculés sur les 3 186 lignes converties sont **identiques** à
`backend/app/domain/score/landmarks_v1.json` : la conversion du script est exactement celle de la calibration.
Sur le jeu nettoyé (3 184 lignes), l'écart maximal est de 0,05 (p90 du magnésium) : les repères v1.0 sont
conservés tels quels.

## Tests

`scripts/tests/test_ciqual_clean.py` — 26 tests des règles, sans réseau ni données :
formats, conversion (dont « non mesuré → NULL, jamais 0 »), unicité des mots-clés, lecture des unités,
fusion et rejet des doublons, réparation et ambiguïté des catégories.
Les seuils des règles de corruption ne sont pas testés : ce sont des décisions mesurées, documentées
dans le notebook.

