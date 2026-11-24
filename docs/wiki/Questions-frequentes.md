**Français** · [English](FAQ)

# Questions fréquentes

**Mon registre part-il sur Internet ?**
Non. L'analyse se fait entièrement sur votre poste. Seule la version en ligne se connecte, au démarrage, pour télécharger des données publiques du GLEIF, et jamais pendant une analyse.

**Un registre sans constat sera-t-il forcément accepté par l'autorité ?**
Non. DORA QA donne des indications ; l'autorité reste seule juge. L'entité déclarante reste responsable de son registre.

**Le navigateur ne s'ouvre pas.**
Regardez la fenêtre du terminal : elle affiche l'adresse à ouvrir (par exemple `http://127.0.0.1:8765`). Copiez-la dans votre navigateur.

**Windows ou macOS refuse de lancer le programme.**
C'est normal pour un programme non signé. Sur un poste professionnel, **voyez avec votre DSI** ; ne contournez pas l'alerte vous-même. Voir [Installer et lancer](Installer-et-lancer).

**Mon antivirus bloque ou supprime DORA QA.**
Contactez votre DSI. Ne désactivez jamais l'antivirus.

**Le pare-feu demande une autorisation réseau.**
Version hors ligne : cliquez sur « Annuler », l'outil n'en a pas besoin. Version en ligne : voyez avec votre DSI.

**L'écran indique « contrôles GLEIF non disponibles ».**
Vous utilisez la version hors ligne : c'est normal. Pour ces contrôles, il faut la [version en ligne](Hors-ligne-ou-en-ligne), avec l'accord de votre DSI.

**L'écran « Mise à jour en ligne en cours » reste affiché (version en ligne).**
L'outil télécharge la copie du GLEIF ; patientez. Au-delà de 15 minutes, il abandonne et démarre sans nouvelle copie. Si cela se répète, le flux réseau est sans doute bloqué : voyez avec votre DSI.

**Le numéro de ligne d'un constat ne correspond pas à mon fichier.**
La ligne 1 est la première ligne **de données** : l'en-tête n'est pas comptée.

**Je pense qu'un constat est faux.**
Ouvrez une [issue « Constat erroné »](https://github.com/DORA-QA/dora-register-quality-analyst/issues/new/choose) avec le code du constat et la source réglementaire, **sans joindre de registre réel**. Pour une demande confidentielle : [dora-qa@proton.me](mailto:dora-qa@proton.me).

**Comment obtenir une nouvelle version ?**
Les nouvelles versions sont publiées dans les [Releases](https://github.com/DORA-QA/dora-register-quality-analyst/releases). Sur un poste professionnel, la mise à jour passe par votre DSI.
