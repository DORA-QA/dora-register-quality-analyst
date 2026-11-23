# Sécurité / Security

## Signaler une faille

Ne signalez **pas** une faille dans une issue publique. Utilisez le bouton **« Report a vulnerability »** de l'onglet [Security](../../security/advisories/new) du dépôt : le signalement reste privé entre vous et les mainteneurs.

Merci d'indiquer la version de DORA QA, le système (Windows, macOS, Docker), les étapes pour reproduire et, si possible, un fichier d'exemple **fictif**. N'envoyez jamais de registre réel.

Nous accusons réception sous 7 jours et publions un correctif ainsi qu'un avis de sécurité dès que possible.

## Principes de sécurité du produit

- Le moteur et l'interface n'écoutent que sur `127.0.0.1` ; ils ne sont pas joignables depuis le réseau.
- Aucune donnée de registre n'est envoyée à l'extérieur ni conservée après l'analyse.
- La version en ligne ne se connecte qu'au démarrage, pour télécharger la copie publique du GLEIF, et refuse tout registre pendant ce téléchargement.
- L'import est durci : taille, nombre de lignes, colonnes et cellules plafonnés ; noms de fichiers piégés et archives malformées rejetés.

---

**Reporting a vulnerability**: please use the private *Report a vulnerability* button of the [Security](../../security/advisories/new) tab, never a public issue, and never attach a real register.
