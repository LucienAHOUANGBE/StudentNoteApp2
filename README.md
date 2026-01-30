# Application de consultation des notes – Streamlit

Cette application permet aux étudiants de consulter leurs notes de manière sécurisée et interactive à partir d’une base de données centralisée dans **Google Sheets**.

Elle est développée avec **Streamlit** et propose un affichage clair des résultats, du détail par question, des statistiques et des graphiques interactifs.

---

## Fonctionnalités

- 🔐 Identification par identifiant étudiant  
- 📖 Sélection de la matière  
- 🧮 Calcul automatique de la note sur 20  
- 🎁 Prise en compte d’un bonus global défini dans la feuille *Repa*  
- 📝 Détail des points par question  
- 📊 Statistiques et graphiques interactifs  
- 📥 Téléchargement d’un relevé de notes détaillé  

---

## Structure des données (Google Sheets)

Le fichier Google Sheets doit contenir, pour chaque matière :

- **Une feuille `NomMatière - Repa`**  
  - `titre` : nom de la question  
  - `point` : barème associé  
  - une ligne `bonus` (optionnelle) pour un bonus global  

- **Une feuille `NomMatière - Note`**  
  - une ligne par étudiant  
  - une colonne par question  
  - les valeurs correspondent aux points obtenus ou aux pourcentages selon la configuration  

Les noms des questions doivent correspondre exactement entre les feuilles *Repa* et *Note*.

---

## Technologies utilisées

- Python 3  
- Streamlit  
- Pandas / NumPy  
- Plotly  
- Google Sheets API  
- gspread  

---

## Sécurité des données

Les accès à Google Sheets sont gérés via un **service account** Google.

Les informations sensibles (clé du service account, identifiant du tableur) sont stockées dans :

- `.streamlit/secrets.toml` (local)
- ou dans les **Secrets** de Streamlit Community Cloud

⚠️ **Aucun secret n’est versionné sur GitHub.**

---

## ▶️ Lancer l’application en local

1. Cloner le dépôt :
```bash
  git clone https://github.com/<votre-compte>/<nom-du-repo>.git
  cd <nom-du-repo>
```
2. Créer un environnement virtuel :
```bash
  python -m venv venv
  source venv/bin/activate  # Windows : venv\Scripts\activate
```

3. Installer les dépendances :
```bash
  pip install -r requirements.txt
```


4. Ajouter le fichier ```.streamlit/secrets.toml```

5. Lancer l’application :
```bash
  streamlit run app.py
```

---

## Déploiement sur Streamlit Community Cloud

Pousser le projet sur GitHub

Créer une application sur Streamlit Community Cloud

Ajouter les secrets dans l’interface web

Partager le Google Sheet avec l’email du service account


---

## Remarques pédagogiques

Le bonus global est ajouté après le calcul de la note de base.

La note finale est plafonnée à 20.

Les colonnes vides ou non renseignées sont ignorées automatiquement.


---
## Licence

Projet développé à des fins pédagogiques et académiques.
Toute réutilisation doit mentionner l’auteur.