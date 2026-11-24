# DORA QA — copie GLEIF (dépôt de données)

Ce dossier contient de quoi créer le **dépôt public de données** lu par la version **en ligne** de DORA QA : `DORA-QA/dora-qa-gleif-data`.

- `gleif-copy.yml` : workflow quotidien, à placer dans `.github/workflows/` du dépôt de données. Il lit la dernière Golden Copy du GLEIF, la convertit en Parquet avec `backend/tools/build_gleif.py` (lu dans ce dépôt de code, public) et la publie en release `gleif-AAAAMMJJ-HHMM` du dépôt de données. Seules les 2 dernières releases (2 jours) sont gardées.
- Le README du dépôt de données doit rappeler la source et la licence : *Source : GLEIF, Golden Copy, données publiées sous licence CC0 1.0 — https://www.gleif.org*.

Mise en place :

1. Créer le dépôt **public** `dora-qa-gleif-data` (vide, branche `main`).
2. Y copier `gleif-copy.yml` dans `.github/workflows/` et un README.
3. *Actions > GLEIF copy > Run workflow* pour publier la première copie.

Pourquoi un dépôt séparé : une release par jour encombrerait la page des releases du logiciel, et la version en ligne n'a besoin d'aucun jeton pour lire un dépôt public.
