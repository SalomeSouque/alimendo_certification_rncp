# Sécurité de l'API Alimendo : OWASP

Ce document relie chaque risque OWASP aux mesures appliquées dans le code.
Il sert de preuve pour les critères C9-CR3 (API qui expose les modèles IA) et
C17-CR8 (application).

Référentiels utilisés :

- OWASP API Security Top 10, édition 2023 (risques propres aux API)
- OWASP Top 10, édition 2021 (risques web généraux), en correspondance

Périmètre : l'API FastAPI du dossier `backend/` et son déploiement en production
(`docker-compose.prod.yml`, derrière le reverse proxy Traefik de l'hébergeur). Les routes IA (`/ai/chat`,
`/ai/vision`) sont derrière un mur de connexion et ne s'ouvrent qu'après
validation du compte par une admin. Les routes `/admin` exigent le rôle admin. La recherche
d'aliments et le score sont publics par choix : ils ne touchent à aucune
donnée personnelle.

## Tableau risque -> mesure

| Risque OWASP API 2023 | Web 2021 | Mesure appliquée | Où dans le code | Preuve |
|---|---|---|---|---|
| API1 Contrôle d'accès au niveau objet | A01 | Aucune route IA ne prend d'identifiant d'objet dans l'URL. L'identité de l'utilisatrice vient uniquement du jeton signé. | `app/routers/ai.py`, `get_current_user` | Lecture du code |
| API2 Authentification défaillante | A07 | Jeton JWT signé (HS256) avec expiration (60 min par défaut). Mots de passe hachés avec bcrypt. Même message d'erreur pour email inconnu et mot de passe faux. Mot de passe de 8 caractères minimum. | `app/core/security.py`, `app/services/auth_service.py`, `app/schemas/auth.py` | `tests/test_api_access.py`, `tests/test_security.py` |
| API3 Exposition de propriétés | A01 | Les routes IA et d'authentification déclarent un `response_model` Pydantic : seuls les champs prévus sortent de l'API. Le hash du mot de passe n'est jamais renvoyé. | `app/schemas/` | Lecture du code |
| API4 Consommation de ressources | A04 | Question limitée à 1000 caractères, image à 5 Mo et à trois formats. Réponse Mistral bornée (800 tokens, délai de 30 s). En production, Traefik coupe toute requête de plus de 6 Mo avant qu'elle n'atteigne l'API (le backend ne lit donc jamais un fichier énorme en mémoire). Clé Mistral de production dédiée, avec un plafond de dépense. | `app/schemas/chat.py`, `app/routers/ai.py`, `app/core/config.py`, `docker-compose.prod.yml` (middleware `buffering`) | `tests/test_chat_schema.py`, test de déploiement : fichier de 7 Mo refusé en 413 |
| API5 Contrôle d'accès au niveau fonction | A01 | Le routeur IA impose à toutes ses routes d'un coup (dépendance au niveau du routeur) un jeton valide et un accès IA validé par une admin (`acces_ia`, relu en base à chaque appel, 403 sinon). Le routeur admin impose le rôle admin à toutes ses routes de la même façon. | `app/routers/ai.py`, `app/routers/admin.py`, `require_acces_ia`, `require_role` | `tests/test_api_access.py`, `tests/test_acces_ia.py` (403 sans accès, révocation immédiate, routes admin refusées à un compte non admin) |
| API6 Accès sans limite à un flux métier sensible | A04 | Inscription publique, encadrée : consentement explicite obligatoire (422 sinon), mot de passe de 8 caractères minimum. Le flux coûteux (appels Mistral payants, VLM du serveur) n'est ouvert qu'aux comptes validés à la main : créer des comptes en masse ne donne pas accès à l'IA. | `app/schemas/auth.py`, `app/core/security.py` | `tests/test_endpoints.py`, `tests/test_acces_ia.py` |
| API7 Falsification de requête côté serveur (SSRF) | A10 | L'API n'appelle que des adresses fixées dans la configuration (Mistral, Ollama, Open Food Facts). Aucune URL ne vient de la requête de l'utilisatrice. | `app/core/config.py` | Lecture du code |
| API8 Mauvaise configuration de sécurité | A05 | CORS limité aux origines déclarées et aux méthodes utilisées. Documentation `/docs` désactivée hors environnement local. Secrets lus dans `.env`, jamais dans le code. Secrets masqués dans les logs. Caractères de contrôle retirés de la question avant le classifieur et le prompt. En production : HTTPS obligatoire ; PostgreSQL, ChromaDB et Ollama sur un réseau Docker privé, invisibles de Traefik, ports publiés seulement sur la boucle locale du serveur ; `/health/detail` non routé publiquement ; secrets propres à la production ; rotation des logs Docker. | `app/main.py`, `app/core/config.py`, `app/core/logging_config.py`, `app/schemas/chat.py`, `docker-compose.prod.yml` | `tests/test_chat_schema.py`, tests de déploiement ([`deploiement.md`](deploiement.md)) : `/docs` en 404, `/health/detail` en 503 depuis Internet |
| API9 Inventaire mal géré | A05 | Une seule API, une seule version en service. Les routes sont listées par l'OpenAPI générée en local. | `app/main.py` | `/docs` en local |
| API10 Consommation non sûre d'API tierces | A08 | Les réponses de Mistral, Ollama et Open Food Facts sont contrôlées. Une erreur ou une réponse inattendue donne un 503 avec un message clair, jamais une trace technique. | `app/services/llm_mistral.py`, `app/routers/ai.py` | Lecture du code |

Correspondances supplémentaires du Top 10 web 2021 :

- A02 Défaillances cryptographiques : en production, tout le trafic passe en
  HTTPS. Le certificat Let's Encrypt est obtenu et renouvelé par Traefik, et la
  redirection HTTP → HTTPS est assurée par la configuration de l'hébergeur.
  Mots de passe hachés avec bcrypt, jetons signés avec une clé propre à la
  production.
- A03 Injection : les requêtes SQL passent par l'ORM SQLAlchemy (requêtes
  paramétrées). Côté prompt, la question est nettoyée et le prompt système
  impose de répondre uniquement à partir des extraits fournis.
- A09 Journalisation : une ligne de log par routage d'intention, sans le texte
  de la question (donnée de santé potentielle). L'échec de connexion est
  journalisé sans l'email saisi.
- Ancien garde-fou `X-API-Key` retiré : une clé livrée dans le frontend n'est
  pas un secret. La protection repose sur le JWT, la validation de l'accès IA
  et le CORS restreint.

## Limites connues

- Pas de limitation du nombre de requêtes par utilisatrice (API4, API6), ni sur
  l'inscription, ni sur les routes IA. Risque réduit : seuls les comptes validés
  à la main consomment le quota Mistral, et un compte abusif se révoque en une
  commande, avec effet immédiat. Évolution V2 : limitation de débit et quota de
  tokens par compte.
- Le rôle admin est lu dans le jeton : un compte retiré du rôle admin garde ses
  droits sur `/admin` jusqu'à l'expiration du jeton (60 min).
- Le script d'administration (`python -m app.cli`) sait promouvoir un compte et
  ouvrir ou fermer son accès IA, mais pas retirer le rôle admin ni supprimer un
  compte : ces deux opérations se font aujourd'hui en SQL sur le serveur
  ([`deploiement.md`](deploiement.md)).
- Pas de double authentification, y compris pour le compte admin : sa
  protection repose sur un mot de passe long et unique. Évolution V2.
- Les sauvegardes de la base sont stockées sur le même serveur que la base.
- Le nettoyage de la question ne bloque pas toutes les injections de prompt.
  Le garde-fou principal reste le prompt système et le classifieur
  d'intention, qui écarte les questions hors sujet avant l'appel à Mistral.