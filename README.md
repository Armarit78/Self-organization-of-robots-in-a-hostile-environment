# Self-organization of robots in a hostile environment

## Présentation

Ce projet implémente un système multi-agents dans lequel des robots évoluent dans un environnement hostile afin de collecter, transformer et transporter des déchets radioactifs.

Le système repose sur :
- des agents autonomes distribués
- une spécialisation des rôles (robots verts, jaunes, rouges)
- une transformation progressive des déchets
- des stratégies de coordination avec ou sans communication

Deux versions du système sont proposées afin de comparer différentes approches.

---

## Structure du projet

Le dépôt est organisé en deux versions principales :

### Version 1

Implémentation de base du système avec :

- des agents orientés tâche
- un système de communication optionnel
- une coordination via une carte partagée et un mécanisme de buffer
- un benchmark et une évaluation des performances

→ Détails complets disponibles ici :  
[README Version 1](./Version%201/README_V1.md)

---

### Version 2 — Contamination

Version étendue introduisant de nouvelles contraintes :

- résistance des robots à la radioactivité
- mécanismes de dégâts et de récupération (état KO)
- nouveaux défis de coordination
- comportements et gestion des tâches améliorés

→ Détails complets disponibles ici :  
[README Version 2](./Version%202%20-%20Contamination/README_V2.md)

## Auteurs
- Guillaume PORET  
- Christophe BOSHRA  
- Groupe 30
