# Services d'IA paramétrés

Ce dossier documente les services d'intelligence artificielle préexistants
installés et paramétrés pour Alimendo (compétence C8, épreuve E2).

| Service | Rôle dans Alimendo | Documentation | État |
|---|---|---|---|
| Mistral Small (API Mistral) | Génère la réponse du chatbot à partir des extraits du corpus | [Documentation du service Mistral](mistral.md) | En service |
| Qwen3-VL 4B (Ollama, local) | Reconnaît un aliment brut sur une photo | Documentation du VLM, à rédiger avec le lot VLM | Non branché (la route `/ai/vision` renvoie 501) |

Le classifieur d'intention n'apparaît pas ici : c'est un modèle entraîné dans
le projet, pas un service préexistant. Il est documenté dans le README racine.