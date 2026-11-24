# Journal des versions · Changelog

Ce fichier suit le principe de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et la numérotation [SemVer](https://semver.org/lang/fr/).
La section de la version taguée sert de texte à la release GitHub.

<!-- release:1.0.0 -->
## [1.0.0] — première version publique · first public release

### Français

Première version publique de **DORA Register Quality Analyst (DORA QA)**, gratuite et open source sous licence **EUPL 1.2**.

**Ce que fait DORA QA**
- Analyse, **sur votre poste**, un registre d'information DORA (règlement d'exécution (UE) 2024/2956, taxonomie EBA 4.0), au format ZIP xBRL-CSV ou dans son enveloppe XML OneGate (ACPR).
- Classe les constats par gravité, avec pour chacun une explication en clair, sa référence (règle EBA, article de l'ITS, note de l'ACPR) et un conseil pour le corriger.
- Calcule les scores de conformité réglementaire, de qualité et de confiance ; exporte les constats en CSV et JSON Lines.
- Interface en français et en anglais.

**Deux versions, Windows et macOS (Apple Silicon)**
- **Hors ligne** : aucune connexion, jamais. Les contrôles qui interrogent le GLEIF sont absents, et l'écran comme les exports l'indiquent.
- **En ligne** : au démarrage seulement, téléchargement de la copie publique du GLEIF pour vérifier les LEI et les mères ultimes ; aucun registre n'est accepté pendant ce téléchargement.

**Confidentialité**
- Le registre n'est jamais envoyé sur Internet ; l'application ne répond que sur `127.0.0.1`.
- Rien n'est conservé : le fichier est purgé à la fin de l'analyse et à l'arrêt.

**Avertissement**
- Une fenêtre de non-responsabilité s'affiche à chaque lancement : les résultats sont indicatifs et ne constituent pas une attestation de conformité.

**À savoir**
- Les exécutables ne sont pas signés : voir le README pour passer SmartScreen (Windows) et Gatekeeper (macOS). Une entreprise peut demander une version signée à son nom (modèle d'issue « Demande de signature entreprise » ou dora-qa@proton.me).
- Vérifiez l'empreinte de votre ZIP avec `SHA256SUMS.txt`. La nomenclature logicielle (SBOM, SPDX) est jointe.

### English

First public release of **DORA Register Quality Analyst (DORA QA)**, free and open source under the **EUPL 1.2**.

**What DORA QA does**
- Analyses a DORA register of information (Implementing Regulation (EU) 2024/2956, EBA taxonomy 4.0) **on your own computer**, as an xBRL-CSV ZIP or inside its OneGate XML envelope (ACPR).
- Ranks findings by severity, each with a plain-language explanation, its reference (EBA rule, ITS article, ACPR note) and advice on how to fix it.
- Computes regulatory, quality and confidence scores; exports findings as CSV and JSON Lines.
- User interface in French and English.

**Two editions, Windows and macOS (Apple Silicon)**
- **Offline**: no connection, ever. Checks that query the GLEIF are left out, as the screen and exports state.
- **Online**: at start-up only, downloads the public GLEIF copy to check LEIs and ultimate parents; no register is accepted during the download.

**Privacy**
- The register is never sent over the Internet; the application only listens on `127.0.0.1`.
- Nothing is kept: the file is purged at the end of the analysis and on shutdown.

**Disclaimer**
- A disclaimer is shown at every launch: results are indicative and are not a certificate of compliance.

**Good to know**
- The executables are not signed: see the README to get past SmartScreen (Windows) and Gatekeeper (macOS). A company can request a build signed in its own name (issue template "Enterprise signing request" or dora-qa@proton.me).
- Check your ZIP against `SHA256SUMS.txt`. A software bill of materials (SBOM, SPDX) is attached.
<!-- /release:1.0.0 -->
