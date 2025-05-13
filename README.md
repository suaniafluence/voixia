# 📘 Documentation UML – MVP Agent Vocal IA

Ce dossier contient les principaux diagrammes UML pour modéliser le fonctionnement du MVP de l'agent vocal IA.

## 📂 Contenu

### 1. `use_case.puml`
Diagramme de **cas d’usage** :
- Acteur : Interlocuteur
- Cas d’usage : passer un appel, parler à l’IA, recevoir une réponse, terminer l’appel.

### 2. `activity.puml`
Diagramme **d’activités** montrant le workflow logique d’un appel :
1. Appel reçu
2. Connexion SIP
3. Streaming audio
4. Réception de réponse OpenAI
5. Lecture de la réponse

### 3. `sequence.mmd`
Diagramme **de séquence** en Mermaid :
- Interactions entre l’utilisateur, le système SIP, l’application Python et l’API OpenAI.

### 4. `class.puml`
Diagramme de **classes** montrant l’architecture logicielle du code Python (CallHandler, AudioStream, GPTClient…).

### 5. `deployment.puml`
Diagramme de **déploiement** montrant l’infrastructure :
- Téléphone → OVH SIP → Serveur SIP → App Python → OpenAI API.

## 🛠️ Visualisation

- `.puml` → à ouvrir avec [PlantUML](https://plantuml.com/)
- `.mmd` → à ouvrir avec [Mermaid Live](https://mermaid.live)

## ✍️ Auteur

Diagrammes générés avec ❤️ par Suan Tay et ChatGPT.