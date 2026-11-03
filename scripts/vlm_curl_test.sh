#!/usr/bin/env bash
# Test d'inférence du VLM (Qwen3-VL via Ollama) sur une ou plusieurs photos.
#
# Envoie chaque photo à l'API Ollama avec le prompt et le format JSON candidats,
# puis affiche la réponse du modèle, les durées mesurées et la mémoire GPU occupée.
# Sert à fixer le prompt, le format de sortie et le timeout avant de brancher
# backend/app/services/vision_service.py (compétence C8, lot VLM).
#
# Usage :
#   scripts/vlm_curl_test.sh photo1.jpg [photo2.png ...]
#   scripts/vlm_curl_test.sh photos/*.jpg | tee docs/services/resultats_vlm_brut.txt
#
# Variables d'environnement (toutes optionnelles) :
#   VLM_TEST_URL   adresse d'Ollama vue depuis l'hôte (défaut : http://localhost:11434)
#   OLLAMA_MODEL   tag du modèle (défaut : qwen3-vl:4b-instruct-q4_K_M)
#   VLM_NUM_CTX    taille du contexte en tokens (défaut : 4096)
#   VLM_TIMEOUT    délai maximal d'un appel, en secondes (défaut : 120)
#
# Prérequis : curl, jq, base64 ; nvidia-smi pour la mesure mémoire (facultatif).
# Aucune photo n'est conservée : le script lit le fichier et l'envoie, rien d'autre.

set -euo pipefail

VLM_TEST_URL="${VLM_TEST_URL:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3-vl:4b-instruct-q4_K_M}"
VLM_NUM_CTX="${VLM_NUM_CTX:-4096}"
VLM_TIMEOUT="${VLM_TIMEOUT:-120}"

# Prompt candidat, version 2. Il sera recopié dans vision_service.py une fois validé.
# v1 (label + confidence seuls) : un assortiment de légumes donnait "laitue" et un
# plat cuisiné "riz", tous deux à 0,95. La v2 fait d'abord classer la photo
# (champ "contenu"), avant de nommer l'aliment.
PROMPT_SYSTEME="Tu identifies un aliment brut sur une photo, pour une application de nutrition. Tu réponds uniquement avec l'objet JSON demandé, sans aucun autre texte."

PROMPT_UTILISATEUR="Décris le contenu de cette photo selon ces règles.
- contenu : choisis exactement une valeur.
  \"aliment_unique\" : un seul aliment brut, ou plusieurs exemplaires du même aliment (trois pommes, une grappe de raisin).
  \"plusieurs_aliments\" : des aliments bruts différents, sans qu'un seul occupe l'essentiel de la photo.
  \"plat_prepare\" : un plat cuisiné, une assiette composée, un produit transformé.
  \"aucun_aliment\" : pas d'aliment visible.
- label : si contenu vaut \"aliment_unique\", nom générique de l'aliment en français, au singulier, en minuscules, sans marque ni préparation (exemples : \"tomate\", \"pomme\", \"brocoli\", \"saumon\", \"lentille\"). Sinon, chaîne vide \"\".
- confidence : ta confiance dans ta réponse, entre 0 et 1."

# Schéma imposé à la sortie (sorties structurées d'Ollama : champ "format").
# L'ordre des propriétés compte : le modèle écrit "contenu" avant "label".
# Volontairement simple : l'intervalle [0, 1] de confidence est revérifié côté backend.
SCHEMA='{
  "type": "object",
  "properties": {
    "contenu": {
      "type": "string",
      "enum": ["aliment_unique", "plusieurs_aliments", "plat_prepare", "aucun_aliment"]
    },
    "label": {"type": "string"},
    "confidence": {"type": "number"}
  },
  "required": ["contenu", "label", "confidence"]
}'

for outil in curl jq base64; do
  command -v "$outil" >/dev/null || { echo "Outil manquant : $outil" >&2; exit 1; }
done

if [[ $# -eq 0 ]]; then
  echo "Usage : $0 photo1.jpg [photo2.png ...]" >&2
  exit 1
fi

memoire_gpu() {
  # Mémoire GPU occupée (Mio), ou "n/a" si nvidia-smi est absent.
  if command -v nvidia-smi >/dev/null; then
    nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -n1
  else
    echo "n/a"
  fi
}

echo "Modèle : $OLLAMA_MODEL · contexte : $VLM_NUM_CTX tokens · timeout : ${VLM_TIMEOUT} s · $VLM_TEST_URL"
echo "Mémoire GPU avant le premier appel : $(memoire_gpu) Mio"
echo

for photo in "$@"; do
  if [[ ! -f "$photo" ]]; then
    echo "== $photo : fichier introuvable, ignoré" >&2
    continue
  fi

  taille_ko=$(( $(stat -c %s "$photo") / 1024 ))
  corps=$(mktemp)
  reponse=$(mktemp)

  # --rawfile plutôt que --arg : une photo encodée en base64 dépasse vite la
  # taille maximale d'un argument de commande sous Linux (128 Kio).
  jq -n \
    --arg model "$OLLAMA_MODEL" \
    --arg systeme "$PROMPT_SYSTEME" \
    --arg question "$PROMPT_UTILISATEUR" \
    --rawfile image <(base64 -w0 "$photo") \
    --argjson schema "$SCHEMA" \
    --argjson num_ctx "$VLM_NUM_CTX" \
    '{
      model: $model,
      stream: false,
      format: $schema,
      options: {temperature: 0, num_ctx: $num_ctx},
      messages: [
        {role: "system", content: $systeme},
        {role: "user", content: $question, images: [$image]}
      ]
    }' > "$corps"

  set +e
  code_http=$(curl -sS -o "$reponse" -w "%{http_code} %{time_total}" \
    --max-time "$VLM_TIMEOUT" \
    -H "Content-Type: application/json" \
    --data-binary @"$corps" \
    "$VLM_TEST_URL/api/chat")
  statut_curl=$?
  set -e

  echo "== $photo (${taille_ko} Kio)"
  if [[ $statut_curl -ne 0 ]]; then
    echo "   échec curl (code $statut_curl) : timeout ou Ollama injoignable"
  else
    read -r http duree_totale <<<"$code_http"
    if [[ "$http" != "200" ]]; then
      echo "   HTTP $http : $(head -c 300 "$reponse")"
    else
      contenu=$(jq -r '.message.content' "$reponse")
      echo "   sortie brute : $contenu"
      if echo "$contenu" | jq -e 'type == "object" and has("contenu") and has("label") and has("confidence")' >/dev/null 2>&1; then
        echo "   JSON valide  : $(echo "$contenu" | jq -r '"contenu=\(.contenu) label=\(.label) confidence=\(.confidence)"')"
      else
        echo "   JSON INVALIDE"
      fi
      # Durées renvoyées par Ollama, en nanosecondes, converties en secondes.
      jq -r --arg total "$duree_totale" '
        "   durées (s)   : curl=\($total) total=\(.total_duration/1e9*100|round/100) chargement=\(.load_duration/1e9*100|round/100) image+prompt=\(.prompt_eval_duration/1e9*100|round/100) génération=\(.eval_duration/1e9*100|round/100)",
        "   tokens       : entrée=\(.prompt_eval_count) sortie=\(.eval_count)"
      ' "$reponse"
    fi
  fi
  echo "   mémoire GPU  : $(memoire_gpu) Mio"
  echo

  rm -f "$corps" "$reponse"
done
