**Français** · [English](Analyse-a-register)

# Analyser un registre

## Quel fichier déposer ?

Le fichier que vous remettez (ou allez remettre) à l'autorité :

- le **package ZIP** xBRL-CSV produit par votre outil de reporting (format EBA) ;
- ou l'**enveloppe XML** OneGate qui le contient (remise ACPR).

Un seul registre à la fois, 100 Mo au plus.

> Le registre réel ne doit être analysé que sur un poste où l'outil est **autorisé par votre DSI** (voir [Autonomie et DSI](Autonomie-et-DSI)).

## Étapes

1. Lancez DORA QA et acceptez l'avertissement.
2. Cliquez sur **Choisir un fichier** (ou glissez le fichier dans la zone « Déposer un registre d'information »).
3. Patientez quelques secondes : l'analyse se fait sur votre poste.
4. Le rapport s'affiche : voir [Lire le rapport](Lire-le-rapport).

## Corriger et recommencer

1. Notez les constats à corriger (ou exportez-les).
2. Corrigez le registre **dans votre outil de reporting habituel**, puis régénérez le ZIP ou le XML. DORA QA ne modifie jamais votre fichier.
3. Déposez le nouveau fichier : une nouvelle analyse démarre.

## Changer de langue

Sélecteur **EN | FR** en haut à droite. Les constats sont alors affichés dans la langue choisie.

## Découvrir l'outil sans registre réel

Le dossier `exemples` du ZIP contient des registres **entièrement fictifs**, dont un registre volontairement plein d'erreurs : idéal pour une démonstration ou une formation.
