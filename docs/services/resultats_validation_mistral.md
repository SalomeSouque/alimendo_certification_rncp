# Résultats des tests de validation du service Mistral

Date d'exécution : 2026-10-23. Modèle : `mistral-small-2603`.
Généré par `scripts/validate_mistral.py`. Procédure : `docs/services/mistral.md`.

| Cas | Attendu | Obtenu | Conforme | Latence (ms) |
|---|---|---|---|---|
| question_connue | Réponse tirée de l'extrait (cite la sardine) | D'après l'extrait documentaire **"Fiche de test Alimendo"**, les oméga-3 sont des acides gras polyinsaturés que l'on trouve notamment dans les poissons gras comme la sardine et le maquereau. *Source : Fiche de test Alimendo* | Oui | 1110 |
| hors_extraits | Refus de répondre, pas de « Canberra » (connaissance générale) | Je ne peux répondre qu'à des questions liées à l'endométriose et à l'alimentation dans ce contexte. Pour votre question sur la capitale de l'Australie, je ne dispose pas d'informations pertinentes dans les extraits fournis. Je vous invite à consulter une source fiable pour cette information. | Oui | 674 |
| cle_invalide | Accès refusé par Mistral (401), erreur propre côté application | LLMIndisponibleError : Le service de génération est momentanément indisponible. | Oui | 83 |
| service_injoignable | Aucune réponse du service, erreur propre côté application | LLMIndisponibleError : Le service de génération est momentanément indisponible. | Oui | 13 |
