# Signer DORA QA avec votre propre certificat

Les exécutables publiés dans les Releases ne sont **pas signés** (ni Authenticode sous Windows, ni notarisation Apple). Beaucoup de DSI préfèrent de toute façon un binaire qu'elles ont **reconstruit et signé elles-mêmes**, à partir d'un code source qu'elles ont pu auditer. Cette page décrit la marche à suivre.

## 1. Reconstruire depuis les sources

Sur un poste de build Windows ou macOS (Python 3.13, uv, Node.js 22) :

```bash
git clone https://github.com/stephanealpha/dora-register-quality-analyst
cd dora-register-quality-analyst
git checkout vX.Y.Z            # la version auditée
uv sync --frozen --no-dev --project backend
uv run --project backend --with pyinstaller python portable/build.py              # version hors ligne
uv run --project backend --with pyinstaller python portable/build.py --online     # version en ligne
```

Les ZIP sont produits dans `dist-portable/`, le dossier de l'application dans `dist-portable/app/DORA-QA/`. Comparez si besoin leur contenu à celui de la Release.

## 2. Signer sous Windows (Authenticode)

Avec le certificat de signature de code de votre entreprise (magasin de certificats, HSM ou service de signature) :

```powershell
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a `
  dist-portable\app\DORA-QA\DORA-QA.exe
signtool verify /pa dist-portable\app\DORA-QA\DORA-QA.exe
```

Rezippez ensuite le dossier, ou emballez-le dans un MSI (WiX, Inno Setup) pour un déploiement par Intune ou SCCM.

## 3. Signer et notariser sous macOS

Avec un certificat « Developer ID Application » de votre entreprise :

```bash
codesign --deep --force --options runtime --timestamp \
  --sign "Developer ID Application: Votre Entreprise (TEAMID)" dist-portable/app/DORA-QA/DORA-QA
ditto -c -k --keepParent dist-portable/app/DORA-QA DORA-QA.zip
xcrun notarytool submit DORA-QA.zip --keychain-profile "notary" --wait
```

## Besoin d'aide ?

Ouvrez une issue avec le modèle **« Demande de signature entreprise »**. N'y indiquez aucune information confidentielle.
