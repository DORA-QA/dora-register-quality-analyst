# EUID : ce que dit le règlement d'exécution (UE) 2021/1042

26 octobre 2026 · Claude · documents fournis par le PO · complète `docs/references-dora-europe.md` (S21) et `docs/sources-acpr-eba-2025.md` §4

## 1. Le texte

| Élément | Détail |
| --- | --- |
| Acte | Règlement d'exécution (UE) 2021/1042 de la Commission du 18 juin 2021, spécifications techniques et procédures du système d'interconnexion des registres (BRIS) |
| Base | Directive (UE) 2017/1132, art. 13 decies §5 et art. 24 ; c'est l'article 16 de cette directive que vise l'ITS DORA 2024/2956, art. 3 §5 |
| Publication | JO L 225 du 25/06/2021, p. 7 à 51 (versions française et anglaise fournies) |
| Entrée en vigueur | 20e jour après publication (art. 3), soit le 15/07/2021 ; abroge le règlement 2020/2244 (art. 2) |
| Portée | Texte présentant de l'intérêt pour l'EEE |
| Niveau (méthode §3) | **Référence absolue** (Commission, JO de l'UE) |

## 2. La structure de l'EUID (annexe, point 9, p. L 225/42)

L'EUID est l'identifiant unique des sociétés (art. 16 §1 de la directive) et des **succursales** (art. 29 §4) pour les échanges entre registres. Sa structure suit la norme **ISO 6523** et comprend quatre éléments :

| Élément | Rôle | Statut |
| --- | --- | --- |
| Code pays | Identifier l'État membre du registre | Obligatoire |
| Identifiant du registre | Identifier le registre national d'origine | Obligatoire |
| Numéro d'immatriculation | Numéro de la société ou de la succursale dans ce registre | Obligatoire |
| Chiffre de contrôle | Éviter les erreurs d'identification | Facultatif |

Ce que le texte **ne dit pas** :
- **aucun séparateur** : ni point, ni autre caractère ;
- aucun jeu de caractères, aucune longueur ;
- aucune norme pour le code pays (ISO 3166 n'est pas citée ; la Grèce, GR ou EL, n'est pas tranchée) ;
- aucune liste des identifiants de registre : elle relève des listes de codes de la plateforme BRIS (point 8, d), qui ne sont pas publiées dans le règlement.

Les messages de l'annexe distinguent l'EUID des « autres identifiants de la société (par exemple le LEI) » : ce sont deux identifiants différents.

## 3. Confrontation avec les autres sources

| Source | Ce qu'elle dit | Rapport au règlement |
| --- | --- | --- |
| ITS DORA 2024/2956, art. 3 §5 | LEI valide et actif, ou EUID au sens de l'art. 16 de la directive 2017/1132 | Renvoie au règlement 2021/1042 pour la structure |
| EBA, observations 2025 (S12 p. 20) | Contrôles simples recommandés : un point, et un préfixe de pays de l'EEE | Le point est une **pratique de BRIS**, pas une exigence du texte. Le pays de l'EEE découle du texte (État du registre, intérêt EEE) |
| ACPR, Forum Fintech 2025 (S16 p. 13) | La vérification de l'EUID est la seule exception à l'alignement d'OneGate sur les AES | Contenu de la vérification inconnu |
| Fichier réel accepté par l'ACPR (0.6.2) | EUID sans point accepté | Cohérent avec le texte |

## 4. Conséquences pour nos contrôles

| Contrôle | Situation actuelle | Ce que le règlement change | Proposition |
| --- | --- | --- | --- |
| DAT-011, syntaxe | Pays (2 lettres) + code alphanumérique, un point facultatif | Le point facultatif est **conforme au texte**. Mais l'identifiant du registre est obligatoire, et **sans séparateur on ne peut pas vérifier qu'il est présent** : c'est la vraie raison du point recommandé par l'EBA | Garder la syntaxe actuelle. Sans point : information ou MINOR, « présence de l'identifiant du registre non vérifiable ; l'EBA recommande le point ». Source : règlement 2021/1042 (CONFIRMED pour la structure) |
| DAT-011, caractères | Lettres et chiffres seulement, un seul point | Le texte ne fixe aucun jeu de caractères | Inchangé (aucun EUID réel connu avec d'autres caractères), à surveiller |
| DAT-011, exemple affiché | « FR1234567 » | Cet exemple n'a ni identifiant de registre ni numéro de 9 chiffres visibles | Remplacer par un exemple à trois éléments (forme française déjà décrite par PO-5 : FR + code du registre + SIREN) |
| DAT-012, pays de l'EEE | Liste UE + Islande, Liechtenstein, Norvège, PROVISIONAL | Le code pays désigne l'État membre du registre ; texte d'intérêt EEE ; EBA concordante | Source vérifiée (règlement + S12) ; la liste des pays reste à confirmer pour l'EEE (participation de l'Islande, du Liechtenstein et de la Norvège à BRIS) |
| DAT-013, pays de l'EUID = pays du siège | MINOR, hypothèse H24 | Le code pays est celui du **registre**, pas du siège. Ils coïncident pour une société, mais **pas pour une succursale** immatriculée dans un autre État | H24 reste une hypothèse ; ajouter l'exception des succursales dans l'explication |
| DAT-014, LEI déclaré comme EUID | MAJOR | Le texte distingue l'EUID du LEI ; l'EBA cite cette confusion comme erreur fréquente | Appui supplémentaire, sans changement |
| Chiffre de contrôle | Non contrôlé | Facultatif, algorithme non défini | Rien à faire |
| Identifiant du registre | Non contrôlé (sauf forme française de DAT-017/DAT-018) | Liste détenue par BRIS, non publiée dans le règlement | Contrôle impossible sans la liste de codes BRIS ; candidat pour l'édition experte |

## 5. Effet sur l'arbitrage PO-24 (#94)

Le règlement ne rend pas le point obligatoire. Rendre DAT-011 bloquant ou majeur faute de point irait au-delà du texte, et contre un fichier réel accepté par l'ACPR. La proposition est donc :
- **point facultatif maintenu** (décision 0.6.2 confirmée par le texte) ;
- **constat d'information** en l'absence de point, qui explique pourquoi l'EBA le recommande ;
- structure de l'EUID passée en **CONFIRMED** sur la base du règlement 2021/1042.

## 6. Questions ouvertes

1. Quelle vérification de l'EUID l'ACPR applique-t-elle sur OneGate (S16) ? Question ajoutée à #16.
2. Liste des identifiants de registre BRIS, par pays : où est-elle publiée (portail e-Justice) ?
3. Code pays de la Grèce dans l'EUID : EL ou GR ? Aujourd'hui, nous acceptons les deux.
