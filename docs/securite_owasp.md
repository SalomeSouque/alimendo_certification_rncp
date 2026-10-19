# Sécurité de l'API Alimendo : OWASP

Ce document relie chaque risque OWASP aux mesures appliquées dans le code.
Il sert de preuve pour les critères C9-CR3 (API qui expose les modèles IA) et
C17-CR8 (application).

Référentiels utilisés :

- OWASP API Security Top 10, édition 2023 (risques propres aux API)
- OWASP Top 10, édition 2021 (risques web généraux), en correspondance

Périmètre : l'API FastAPI du dossier `backend/`. Les routes IA (`/ai/chat`,
`/ai/vision`) sont les seules derrière un mur de connexion. La recherche
d'aliments et le score sont publics par choix : ils ne touchent à aucune
donnée personnelle.

## Tableau risque -> mesure

| Risque OWASP API 2023 | Web 2021 | Mesure appliquée | Où dans le code | Preuve |
|---|---|---|---|---|
| API1 Contrôle d'accès au niveau objet | A01 | Aucune route IA ne prend d'identifiant d'objet dans l'URL. L'identité de l'utilisatrice vient uniquement du jeton signé. | `app/routers/ai.py`, `get_current_user` | Lecture du code |
| API2 Authentification défaillante | A07 | Jeton JWT signé (HS256) avec expiration (60 min par défaut). Mots de passe hachés avec bcrypt. Même message d'erreur pour email inconnu et mot de passe faux. Mot de passe de 8 caractères minimum. | `app/core/security.py`, `app/services/auth_service.py`, `app/schemas/auth.py` | `tests/test_api_access.py`, `tests/test_security.py` |
| API3 Exposition de propriétés | A01 | Les routes IA et d'authentification déclarent un `response_model` Pydantic : seuls les champs prévus sortent de l'API. Le hash du mot de passe n'est jamais renvoyé. | `app/schemas/` | Lecture du code |
| API4 Consommation de ressources | A04 | Question limitée à 1000 caractères, image à 5 Mo et à trois formats. Réponse Mistral bornée (800 tokens, délai de 30 s). | `app/schemas/chat.py`, `app/routers/ai.py`, `app/core/config.py` | `tests/test_chat_schema.py` |
| API5 Contrôle d'accès au niveau fonction | A01 | Le routeur IA impose l'authentification à toutes ses routes d'un coup (dépendance au niveau du routeur), aucune route IA ne peut être oubliée. | `app/routers/ai.py` | `tests/test_api_access.py` (401 sans jeton et avec un jeton invalide) |
| API6 Accès sans limite à un flux métier sensible | A04 | Non applicable : pas d'achat, de réservation ni d'inscription en libre accès. | | |
| API7 Falsification de requête côté serveur (SSRF) | A10 | L'API n'appelle que des adresses fixées dans la configuration (Mistral, Ollama, Open Food Facts). Aucune URL ne vient de la requête de l'utilisatrice. | `app/core/config.py` | Lecture du code |
| API8 Mauvaise configuration de sécurité | A05 | CORS limité aux origines déclarées et aux méthodes utilisées. Documentation `/docs` désactivée hors environnement local. Secrets lus dans `.env`, jamais dans le code. Secrets masqués dans les logs. Caractères de contrôle retirés de la question avant le classifieur et le prompt. | `app/main.py`, `app/core/config.py`, `app/core/logging_config.py`, `app/schemas/chat.py` | `tests/test_chat_schema.py` |
| API9 Inventaire mal géré | A05 | Une seule API, une seule version en service. Les routes sont listées par l'OpenAPI générée en local. | `app/main.py` | `/docs` en local |
| API10 Consommation non sûre d'API tierces | A08 | Les réponses de Mistral, Ollama et Open Food Facts sont contrôlées. Une erreur ou une réponse inattendue donne un 503 avec un message clair, jamais une trace technique. | `app/services/llm_mistral.py`, `app/routers/ai.py` | Lecture du code |

Correspondances supplémentaires du Top 10 web 2021 :

- A03 Injection : les requêtes SQL passent par l'ORM SQLAlchemy (requêtes
  paramétrées). Côté prompt, la question est nettoyée et le prompt système
  impose de répondre uniquement à partir des extraits fournis.
- A09 Journalisation : une ligne de log par routage d'intention, sans le texte
  de la question (donnée de santé potentielle).

## Limites connues

- Pas de limitation du nombre de requêtes par utilisatrice (API4). Risque
  accepté : le site n'est pas ouvert au public et les routes IA exigent un
  compte. À ajouter avant toute ouverture publique, pour protéger le quota
  Mistral.
- Le nettoyage de la question ne bloque pas toutes les injections de prompt.
  Le garde-fou principal reste le prompt système et le classifieur
  d'intention, qui écarte les questions hors sujet avant l'appel à Mistral.