# Déploiement d'Alimendo

> Squelette à compléter au fil du lot 18 (C15, C19). Chaque section se remplit avec les
> commandes réellement lancées et leur résultat. Les `À COMPLÉTER` disparaissent à la fin.

## 1. Vue d'ensemble

Alimendo tourne sur un serveur fourni par un hébergeur bénévole, derrière son reverse proxy
Traefik, qui gère le HTTPS (certificats Let's Encrypt). Cet environnement sert de
**pré-production** pour la certification (C15-CR4).

| Élément | Valeur |
|---|---|
| URL publique | À COMPLÉTER |
| Route de l'API | `https://DOMAINE/api/...` (préfixe retiré par Traefik) |
| Fichier compose | `docker-compose.prod.yml` |
| Configuration | `.env` sur le serveur, modèle versionné : `.env.prod.example` |
| Images | `ghcr.io/salomesouque/alimendo-api` et `alimendo-frontend`, tag `sha-<commit>` |

Schéma des flux : À COMPLÉTER (internet → Traefik → frontend / api → db, chromadb ; api → Mistral, Open Food Facts).

## 2. Rôles

| Qui | Responsabilité |
|---|---|
| Hébergeur | Serveur, OS, Docker, Traefik, DNS, pare-feu |
| Moi | Fichiers de déploiement, conteneurs Alimendo, données, sauvegardes |

## 3. Prérequis du serveur

Relevés du À COMPLÉTER (date) :

| Ressource | Valeur |
|---|---|
| OS / noyau | |
| CPU | |
| RAM | |
| Disque libre | |
| GPU | |
| Docker / Compose | |
| Traefik : réseau, entrypoint, certresolver | |

## 4. Premier déploiement

À COMPLÉTER : clone, `.env`, page de maintenance, `deploy.sh`, import CIQUAL, ingestion RAG, vérifications.

## 5. Mise à jour

```bash
./deploy/deploy.sh sha-<commit>
```

À COMPLÉTER : ce que fait le script, durée observée, comportement de la page de maintenance.

## 6. Retour arrière

```bash
./deploy/deploy.sh "$(cat ~/.alimendo-deploy/previous)"
```

Limite : les migrations ne sont pas annulées par le retour d'images (voir l'en-tête de `deploy/deploy.sh`).
À COMPLÉTER : test réalisé le …, résultat.

## 7. Sauvegarde et restauration

À COMPLÉTER : cron, rétention, emplacement, test de restauration (date, comptages avant / après).

## 8. Secrets

Liste des secrets, où ils vivent, comment les régénérer : À COMPLÉTER (sans jamais les valeurs).

## 9. Dépannage

À COMPLÉTER au fil des incidents rencontrés.
