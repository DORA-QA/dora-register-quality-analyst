# Package golden

Un seul package conforme, dont chaque cas de test est dérivé par mutation (`tests/cases/mutations.py`).

- `golden.zip` : fichier local du Product Owner, **jamais versionné** (ignoré par Git).
- `golden.sample.zip` : package **fictif** fourni par les experts du projet (version du 28/10/2026, qui remplace celle du 20/10 : en-têtes neutres, RT.05.01.0040 = « Not applicable »), versionné, utilisé par la CI. Validé sans constat (hors LEI fictifs, inconnus du GLEIF). Caractère fictif : `sample-data/README.md`. Il couvre une succursale en Belgique (RT.04.01.0040) et une sous-traitance de rang 2 déclarée en RT.05.02 sans signature en RT.03.02.
- Sans aucun des deux, les tests utilisent le package fictif de `tests/factories.py`.

Le golden doit passer sans aucun constat dans l'outil.
