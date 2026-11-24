# Sécurité / Security

[Français](#français) · [English](#english)

## Français

### Signaler une faille

Ne signalez **pas** une faille dans une issue publique. Utilisez le bouton **« Report a vulnerability »** de l'onglet [Security](../../security/advisories/new) du dépôt : le signalement reste privé entre vous et les mainteneurs.

Si vous ne pouvez pas utiliser GitHub, écrivez à [dora-qa@proton.me](mailto:dora-qa@proton.me) avec « SÉCURITÉ » dans l'objet.

Merci d'indiquer la version de DORA QA, l'édition (hors ligne ou en ligne), le système (Windows, macOS, Docker), les étapes pour reproduire et, si possible, un fichier d'exemple **fictif**. N'envoyez jamais de registre réel.

Nous accusons réception sous 7 jours et publions un correctif ainsi qu'un avis de sécurité dès que possible.

### Principes de sécurité du produit

- Le moteur et l'interface n'écoutent que sur `127.0.0.1` ; ils ne sont pas joignables depuis le réseau.
- Aucune donnée de registre n'est envoyée à l'extérieur ni conservée après l'analyse.
- La version hors ligne ne contient aucun code réseau.
- La version en ligne ne se connecte qu'au démarrage, pour télécharger la copie publique du GLEIF, et refuse tout registre pendant ce téléchargement.
- L'import est durci : taille, nombre de lignes, colonnes et cellules plafonnés ; noms de fichiers piégés et archives malformées rejetés.

## English

### Reporting a vulnerability

Do **not** report a vulnerability in a public issue. Use the **"Report a vulnerability"** button of the repository's [Security](../../security/advisories/new) tab: the report stays private between you and the maintainers.

If you cannot use GitHub, e-mail [dora-qa@proton.me](mailto:dora-qa@proton.me) with "SECURITY" in the subject.

Please state the version of DORA QA, the edition (offline or online), the system (Windows, macOS, Docker), the steps to reproduce and, if possible, a **fictitious** sample file. Never send a real register.

We acknowledge receipt within 7 days and publish a fix and a security advisory as soon as possible.

### Security principles of the product

- The engine and the interface only listen on `127.0.0.1`; they cannot be reached from the network.
- No register data is sent outside or kept after the analysis.
- The offline version contains no network code.
- The online version only connects at start-up, to download the public copy of the GLEIF data, and refuses any register during this download.
- The import is hardened: size, number of rows, columns and cells capped; malicious file names and malformed archives rejected.
