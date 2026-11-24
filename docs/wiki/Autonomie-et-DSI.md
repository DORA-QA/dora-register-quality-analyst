**Français** · [English](Self-service-and-IT)

# Ce que vous pouvez faire seul, ce que vous devez voir avec votre DSI

DORA QA est conçu pour être utilisé par les équipes métier, sans installation ni droits d'administrateur. Mais il manipule votre **registre d'information**, une donnée sensible, et il s'exécute sur un **poste de l'entreprise** : certaines étapes relèvent de votre DSI (direction des systèmes d'information) et de votre RSSI (sécurité).

> **Règle simple** : tout ce qui touche au **poste de travail**, au **réseau** ou au **traitement de données réelles** se décide avec la DSI **avant** de commencer. Une fois l'outil autorisé, l'analyse et la lecture des résultats sont entièrement entre vos mains.

## ✅ Ce que vous pouvez faire en autonomie

| Action | Pourquoi c'est sans risque |
|---|---|
| Lire la documentation et ce wiki | Aucune action sur le poste |
| Découvrir l'outil **sur un ordinateur personnel**, avec les **exemples fictifs** fournis (dossier `exemples`) | Aucune donnée de l'entreprise, aucun poste professionnel |
| Une fois DORA QA **autorisé par la DSI** sur votre poste : lancer l'outil, analyser vos registres, changer de langue | Tout reste sur votre poste ; rien n'est envoyé ni conservé |
| Lire le rapport, filtrer les constats, passer de la vue réglementaire à la vue experte | Simple consultation |
| Corriger votre registre dans votre outil habituel, puis le réanalyser | Vous travaillez sur vos propres fichiers |
| Exporter les constats **sans les valeurs du registre** (case « Exclure les valeurs du registre ») | L'export ne contient que des codes, des explications et des emplacements |
| Répondre « Annuler » si le pare-feu demande une autorisation réseau (version hors ligne) | L'analyse n'a pas besoin du réseau |
| Signaler un constat qui vous semble faux, **sans joindre de registre réel** | Voir [Questions fréquentes](Questions-frequentes) |

## ⚠️ Ce que vous devez impérativement voir avec votre DSI

| Sujet | Pourquoi | Ce qu'il faut demander |
|---|---|---|
| **Exécuter DORA QA sur un poste professionnel** | Le programme n'est pas signé : Windows (SmartScreen) et macOS l'empêchent de démarrer. **Ne contournez pas ces alertes vous-même** sur un poste de l'entreprise. | L'autorisation d'utiliser l'outil, ou une version signée par l'entreprise (voir la [fiche DSI](Fiche-pour-la-DSI)) |
| **Analyser un registre réel** | Le registre contient des données confidentielles (contrats, prestataires, montants) | La confirmation que l'outil est validé pour traiter des données de ce niveau de confidentialité |
| **Choisir la version en ligne** | Elle se connecte à Internet au démarrage (GitHub) pour télécharger la copie publique du GLEIF | L'ouverture du flux sortant, ou l'usage de la version **hors ligne** |
| **Où ranger les exports** | Un export **avec valeurs** contient des données du registre | L'emplacement autorisé (dossier partagé, outil de GED) et la durée de conservation |
| **Alerte de l'antivirus, programme bloqué ou supprimé** | Le poste est protégé par des règles que vous ne devez pas modifier | Le traitement de l'alerte par la DSI : ne désactivez jamais l'antivirus |
| **Installer les nouvelles versions** | Une nouvelle version est un nouveau programme | Le circuit de mise à jour (qui télécharge, qui vérifie, qui déploie) |
| **Déploiement à plusieurs personnes** | Plusieurs postes, éventuellement un paquet d'installation | Un déploiement centralisé (Intune, SCCM…) avec une version signée |

## Le circuit recommandé

1. **Vous** : découvrez l'outil sur un ordinateur personnel avec les exemples fictifs.
2. **Vous → DSI** : transmettez la [fiche DSI](Fiche-pour-la-DSI) avec votre besoin (version hors ligne ou en ligne, nombre d'utilisateurs).
3. **DSI** : vérifie, autorise, éventuellement signe et déploie l'outil.
4. **Vous** : analysez vos registres en autonomie avant chaque remise.

> **Jamais, par aucun canal** : n'envoyez de registre réel aux auteurs du projet, ni dans une issue GitHub, ni par e-mail.
