**Français** · [English](Offline-or-online)

# Choisir sa version : hors ligne ou en ligne

| | **Hors ligne** | **En ligne** |
|---|---|---|
| Fichier à télécharger | `DORA-QA-hors-ligne-…zip` | `DORA-QA-en-ligne-…zip` |
| Connexion Internet | **Jamais** | **Au démarrage seulement**, quelques secondes à quelques minutes |
| Contrôles des LEI auprès du GLEIF (existence, statut, pays, mère ultime) | Non disponibles (l'écran l'indique) | Oui, sur une copie publique du GLEIF mise à jour chaque nuit |
| Tous les autres contrôles | Oui | Oui |
| Accord de la DSI | Pour utiliser l'outil | Pour utiliser l'outil **et** pour le flux Internet sortant |

## Comment choisir

- **Par défaut, prenez la version hors ligne.** C'est la plus simple à faire accepter : aucun flux réseau.
- **Prenez la version en ligne** si vous voulez aussi vérifier vos LEI auprès du GLEIF et que votre DSI autorise la connexion à GitHub.

## Ce qui se passe au démarrage de la version en ligne

1. L'outil affiche un écran d'attente : **aucun registre n'est accepté** pendant ce temps.
2. Il télécharge la dernière copie publique du GLEIF (environ 90 Mo), seulement si elle a changé.
3. Il se déconnecte, puis l'écran d'import s'ouvre. **Votre registre n'est jamais envoyé sur Internet.**

Si le téléchargement échoue (pas de réseau, pare-feu), l'outil démarre quand même : il utilise la copie précédente, ou indique que les contrôles GLEIF ne sont pas évalués.
