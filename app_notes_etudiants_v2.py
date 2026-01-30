import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os

import gspread
import pandas as pd
import numpy as np
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Consultation des Notes", layout="wide", page_icon="📚")


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID")


# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 30px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 40px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-size: 18px;
        font-weight: bold;
        padding: 15px;
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"><h1>📚 Consultation de Notes Étudiants</h1><p style="font-size: 18px; margin-top: 10px;">Entrez votre identifiant et sélectionnez votre matière</p></div>', unsafe_allow_html=True)

def fmt2(x):
    return "-" if pd.isna(x) else f"{float(x):.2f}"

def fmt_pct(x):
    return "-" if pd.isna(x) else f"{float(x):.1f}%"


# Configuration du chemin du fichier Excel
# MODIFIEZ CE CHEMIN selon l'emplacement de votre fichier
EXCEL_FILE_PATH = "baseNote.xlsx"  # Fichier dans le même dossier que le script

def extract_matiere_name(sheet_name):
    """Extraire le nom de la matière depuis le nom de la feuille"""
    return sheet_name.replace(' - Repa', '').replace(' - Note', '').strip()

def get_bareme_data(repa_df):
    """Extraire les données de barème depuis la feuille de répartition"""
    bareme = []
    if 'titre' in repa_df.columns and 'point' in repa_df.columns:
        for _, row in repa_df.iterrows():
            if pd.notna(row['titre']) and pd.notna(row['point']):
                titre = str(row['titre']).strip()
                if titre:  # éviter titre vide
                    bareme.append({'question': titre, 'bareme': float(row['point'])})
    return bareme


def calculate_student_notes(student_row, note_df, bareme_data):
    details = []
    total_points_obtenus = 0.0
    total_bareme = 0.0
    bonus_total = 0.0

    bareme_dict = {item['question']: float(item['bareme']) for item in bareme_data}

    for col in note_df.columns:
        # ignorer colonnes id/parasites
        if col in ['Unnamed: 0', 'id']:
            continue

        # ne garder que les colonnes qui existent dans le barème
        bareme_val = bareme_dict.get(col)
        if bareme_val is None:
            continue

        # lire la valeur "pourcentage" (0..1..>1)
        raw_val = student_row.get(col, np.nan)

        # valeur par défaut si vide
        pourcentage_obtenu = np.nan
        points_reels = np.nan
        bonus_question = 0.0  # bonus = 0 par défaut (plus simple)

        if pd.notna(raw_val):
            try:
                pourcentage_obtenu = float(raw_val)
            except Exception:
                pourcentage_obtenu = np.nan

        if pd.notna(pourcentage_obtenu):
            points_reels = bareme_val * pourcentage_obtenu

            if pourcentage_obtenu > 1.0:
                points_base = bareme_val
                bonus_question = points_reels - bareme_val
                bonus_total += bonus_question
            else:
                points_base = points_reels
                bonus_question = 0.0

            total_points_obtenus += points_base

        total_bareme += bareme_val

        details.append({
            'question': col,
            'bareme': bareme_val,
            'pourcentage_obtenu': (pourcentage_obtenu * 100) if pd.notna(pourcentage_obtenu) else np.nan,
            'points_obtenu': points_reels,
            'bonus': bonus_question if pd.notna(pourcentage_obtenu) else np.nan
        })

    return details, total_points_obtenus, total_bareme, bonus_total



def open_gsheet(spreadsheet_id: str):
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )

    client = gspread.authorize(creds)
    return client.open_by_key(spreadsheet_id)



def sheet_to_df(ws):
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame()

    headers = [h.strip() if h else "" for h in values[0]]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=headers)

    # 1) supprimer les colonnes dont l'en-tête est vide
    df = df.loc[:, df.columns.astype(str).str.strip() != ""]

    # 2) convertir "point" en numérique (Repa)
    if "point" in df.columns:
        df["point"] = pd.to_numeric(df["point"], errors="coerce")

    return df


# @st.cache_data(show_spinner=False)
# def load_data():
#     """Charger les données depuis le fichier Excel local"""
#     if not os.path.exists(EXCEL_FILE_PATH):
#         return None, f"Fichier non trouvé: {EXCEL_FILE_PATH}"
    
#     try:
#         excel_file = pd.ExcelFile(EXCEL_FILE_PATH)
#         sheet_names = excel_file.sheet_names
        
#         # Séparer les feuilles de répartition et de notes
#         repa_sheets = [s for s in sheet_names if 'Repa' in s]
#         note_sheets = [s for s in sheet_names if 'Note' in s]
        
#         # Créer un dictionnaire pour associer les matières
#         matieres_data = {}
        
#         for repa_sheet in repa_sheets:
#             matiere = extract_matiere_name(repa_sheet)
#             note_sheet = repa_sheet.replace('Repa', 'Note')
            
#             if note_sheet in note_sheets:
#                 repa_df = pd.read_excel(EXCEL_FILE_PATH, sheet_name=repa_sheet)
#                 note_df = pd.read_excel(EXCEL_FILE_PATH, sheet_name=note_sheet)
                
#                 bareme_data = get_bareme_data(repa_df)
                
#                 bonus_global = next(
#                     (item['bareme'] for item in bareme_data
#                     if str(item['question']).strip().lower() == 'bonus'),
#                     0.0
#                 )

#                 total_points = sum([item['bareme'] for item in bareme_data 
#                                     #if item['question'] != 'bonus'
#                                     ])
                

#                 # print("bareme_data", bareme_data)
#                 # print("total_points", total_points)

#                 matieres_data[matiere] = {
#                     'repa_df': repa_df,
#                     'note_df': note_df,
#                     'bareme': bareme_data,
#                     'total_points': total_points,
#                     'bonus_global': bonus_global 
#                 }
        
#         return matieres_data, None
#     except Exception as e:
#         return None, str(e)

@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    """Charger les données depuis le fichier google sheet server"""
    try:
        
        gs = open_gsheet(SPREADSHEET_ID)

        worksheet_names = [ws.title for ws in gs.worksheets()]
        
        repa_sheets = [s for s in worksheet_names if 'Repa' in s]
        note_sheets = [s for s in worksheet_names if 'Note' in s]

        matieres_data = {}

        for repa_sheet in repa_sheets:
            matiere = extract_matiere_name(repa_sheet)
            note_sheet = repa_sheet.replace('Repa', 'Note')

            if note_sheet in note_sheets:
                repa_df = sheet_to_df(gs.worksheet(repa_sheet))
                note_df = sheet_to_df(gs.worksheet(note_sheet))

                bareme_data = get_bareme_data(repa_df)

                # Bonus global dans Repa (ex: "bonus" 0.5)
                bonus_global = next(
                    (item['bareme'] for item in bareme_data
                     if str(item['question']).strip().lower() == 'bonus'),
                    0.0
                )

                # total_bareme sans le bonus
                total_points = sum(
                    item['bareme'] for item in bareme_data
                    if str(item['question']).strip().lower() != 'bonus'
                )

                matieres_data[matiere] = {
                    'repa_df': repa_df,
                    'note_df': note_df,
                    'bareme': bareme_data,
                    'total_points': total_points,
                    'bonus_global': bonus_global
                }

        return matieres_data, None

    except Exception as e:
        return None, str(e)



# Charger les données au démarrage
matieres_data, error = load_data()

if error:
    st.error(f"❌ Erreur lors du chargement des données: {error}")
    # st.info(f"💡 Assurez-vous que le fichier **{EXCEL_FILE_PATH}** existe dans le même dossier que cette application.") # en local
    st.info(f"💡 Assurez-vous d'etre connecté, connexion impossible au serveur.")
    st.stop()

if matieres_data:
    st.success(f"✅ Base de données chargée! {len(matieres_data)} matière(s) disponible(s).")
    
    # Formulaire de saisie
    st.markdown("---")
    st.header("🔐 Identification")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        student_id = st.text_input(
            "🆔 Votre identifiant étudiant",
            placeholder="Ex: AKCHDJO",
            help="Entrez votre identifiant tel qu'il apparaît dans le système (4 premières lettres de votre nom de famille et 3 premières lettres de votre prénom, sans accent ni caractère spécial)"
        ).strip().upper()
    
    with col2:
        matieres_list = list(matieres_data.keys())
        selected_matiere = st.selectbox(
            "📖 Sélectionnez la matière",
            ["Choisir une matière..."] + matieres_list,
            help="Choisissez la matière dont vous voulez consulter les notes"
        )
        
        # Vérifier si une vraie matière est sélectionnée
        if selected_matiere == "Choisir une matière...":
            selected_matiere = ""
    
    with col3:
        st.write("")
        st.write("")
        valider_button = st.button("✅ VALIDER", width='stretch')
    
    # Afficher les résultats après validation
    if valider_button:
        if not student_id:
            st.error("⚠️ Veuillez entrer votre identifiant étudiant.")
        elif not selected_matiere:
            st.error("⚠️ Veuillez sélectionner une matière.")
        else:
            st.markdown("---")
            
            # Récupérer les données de la matière sélectionnée depuis la base de données
            matiere_info = matieres_data[selected_matiere]
            note_df = matiere_info['note_df']
            bareme_data = matiere_info['bareme']
            total_points = matiere_info['total_points']
            
            # Chercher l'étudiant dans la feuille de notes
            student_found = False
            student_row = None
            
            # Vérifier dans la colonne 'id' si elle existe
            if 'id' in note_df.columns:
                student_row = note_df[note_df['id'].astype(str).str.upper() == student_id]
                if not student_row.empty:
                    student_found = True
                    student_row = student_row.iloc[0]
            
            # Sinon chercher dans les autres colonnes
            if not student_found:
                for col in note_df.columns[:3]:
                    if note_df[col].dtype == 'object':
                        student_row = note_df[note_df[col].astype(str).str.upper() == student_id]
                        if not student_row.empty:
                            student_found = True
                            student_row = student_row.iloc[0]
                            break
            
            if student_found:
                # Calculer les notes détaillées
                details, total_points_obtenus, total_bareme, bonus_total = calculate_student_notes(
                    student_row, note_df, bareme_data
                )

                
                
                # Calculer la note sur 20 (basée sur le pourcentage de réussite)
                # Note = (points_obtenus / total_bareme) × 20
                note_sur_20_base = (total_points_obtenus / total_bareme * 20) if total_bareme > 0 else 0
                
                # Ajouter le bonus à la note finale
                note_sur_20_finale = note_sur_20_base + bonus_total
                
                # Ajouter le bonus globale à tous les étudiants à la note finale
                # bonus_global = matiere_info['bonus_global']
                bonus_global = matiere_info.get("bonus_global", 0.0)
                note_sur_20_finale = note_sur_20_base + bonus_global

                # La note finale ne peut pas dépasser 20
                note_sur_20_finale = min(note_sur_20_finale, 20)
                
                # Calculer le pourcentage de réussite
                pourcentage_reussite = (total_points_obtenus / total_bareme * 100) if total_bareme > 0 else 0
                
                # Afficher l'en-tête avec les informations de l'étudiant
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #667eea22 0%, #764ba244 100%);
                    border-left: 5px solid #667eea;
                    border-radius: 10px;
                    padding: 25px;
                    margin-bottom: 30px;
                ">
                    <h2 style="color: #667eea; margin-top: 0;">👤 {student_id}</h2>
                    <h3 style="color: #555; margin: 10px 0;">📖 Matière: {selected_matiere}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Afficher la note générale
                st.header("🎯 Note Générale")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col2:
                    if note_sur_20_finale >= 16:
                        couleur = "#28a745"
                        mention = "Excellent 🌟"
                    elif note_sur_20_finale >= 14:
                        couleur = "#20c997"
                        mention = "Très bien ⭐⭐"
                    elif note_sur_20_finale >= 12:
                        couleur = "#17a2b8"
                        mention = "Bien ⭐"
                    elif note_sur_20_finale >= 10:
                        couleur = "#ffc107"
                        mention = "Assez bien ✓"
                    else:
                        couleur = "#dc3545"
                        mention = "Insuffisant ✗"
                    
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, {couleur}22 0%, {couleur}44 100%);
                        border: 4px solid {couleur};
                        border-radius: 15px;
                        padding: 40px;
                        text-align: center;
                        box-shadow: 0 8px 20px rgba(0,0,0,0.2);
                    ">
                        <h1 style="color: {couleur}; font-size: 5em; margin: 0;">
                            {note_sur_20_finale:.2f}/20
                        </h1>
                        <p style="font-size: 1.8em; margin-top: 20px; color: {couleur}; font-weight: bold;">
                            {mention}
                        </p>
                        <hr style="border: 1px solid {couleur}; margin: 20px 0;">
                        <p style="font-size: 1.3em; color: #555;">
                            Note de base: {note_sur_20_base:.2f}/20
                        </p> {f'<p style="font-size: 1.3em; color: #28a745; font-weight: bold;">🎁 Bonus: +{bonus_total+bonus_global:.2f} points</p>' if bonus_total+bonus_global > 0 else ''}
                        <hr style="border: 1px solid {couleur}; margin: 20px 0;">
                        <p style="font-size: 1.2em; color: #777;">
                            Points obtenus: {total_points_obtenus:.2f}/{total_bareme:.2f}
                        </p>
                        <p style="font-size: 1.2em; color: #777;">
                            Taux de réussite: {pourcentage_reussite:.1f}%
                        </p>
                    </div>
                    """, unsafe_allow_html=True)


                   

                
                st.markdown("---")
                
                # Afficher le détail des questions
                st.header("📝 Détail par Question")
                
                if details:
                    # Créer un DataFrame pour l'affichage
                    details_df = pd.DataFrame(details)
                    
                    # Ajouter une colonne de statut basée sur le pourcentage
                    details_df['statut'] = details_df.apply(
                        lambda row: '✅ Réussie' if row['pourcentage_obtenu'] >= 100 else 
                                    ('🟡 Partielle' if row['pourcentage_obtenu'] >= 50 else '❌ Ratée'),
                        axis=1
                    )


                    display_df = pd.DataFrame({
                        'Question / Exercice': details_df['question'],
                        'Barème': details_df['bareme'].apply(fmt2),
                        'Points Obtenus': details_df['points_obtenu'].apply(fmt2),
                        'Bonus': details_df['bonus'].apply(lambda x: "-" if pd.isna(x) else (f"+{x:.2f}" if x > 0 else "-")),
                        'Pourcentage': details_df['pourcentage_obtenu'].apply(fmt_pct),
                        'Statut': details_df['statut']
                    })

                    
                    # Afficher le tableau avec styling
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        height=min(600, len(display_df) * 35 + 38)  # Hauteur dynamique
                    )
                    
                    # Statistiques supplémentaires
                    st.markdown("---")
                    st.header("📊 Statistiques")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    nb_questions_reussies = len([d for d in details if d['pourcentage_obtenu'] >= 100])
                    nb_questions_partielles = len([d for d in details if 0 < d['pourcentage_obtenu'] < 100])
                    nb_questions_ratees = len([d for d in details if d['pourcentage_obtenu'] == 0])
                    moyenne_pourcentage = details_df['pourcentage_obtenu'].mean()
                    
                    with col1:
                        st.metric("Questions réussies", f"{nb_questions_reussies}/{len(details)}", 
                                 delta="✅" if nb_questions_reussies > 0 else None)
                    
                    with col2:
                        st.metric("Réponses partielles", nb_questions_partielles,
                                 delta="🟡" if nb_questions_partielles > 0 else None)
                    
                    with col3:
                        st.metric("Questions ratées", nb_questions_ratees,
                                 delta="❌" if nb_questions_ratees > 0 else None)
                    
                    with col4:
                        st.metric("Taux moyen", f"{moyenne_pourcentage:.1f}%")
                    
                    # Graphique de répartition
                    st.markdown("---")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Graphique en barres
                        fig_bar = go.Figure()
                        
                        couleurs_bar = []
                        for _, row in details_df.iterrows():
                            if row['pourcentage_obtenu'] >= 75:
                                couleurs_bar.append('#28a745')
                            elif row['pourcentage_obtenu'] >= 50:
                                couleurs_bar.append('#ffc107')
                            else:
                                couleurs_bar.append('#dc3545')
                        
                        fig_bar.add_trace(go.Bar(
                            x=details_df['question'],
                            y=details_df['points_obtenu'],
                            name='Points obtenus',
                            marker_color=couleurs_bar,
                            text=details_df['points_obtenu'].round(2),
                            textposition='auto',
                        ))
                        
                        fig_bar.add_trace(go.Scatter(
                            x=details_df['question'],
                            y=details_df['bareme'],
                            name='Barème',
                            mode='markers+lines',
                            marker=dict(size=10, color='#667eea'),
                            line=dict(dash='dash', color='#667eea')
                        ))
                        
                        fig_bar.update_layout(
                            title="Points obtenus vs Barème",
                            xaxis_title="Questions",
                            yaxis_title="Points",
                            height=400,
                            showlegend=True,
                            hovermode='x unified'
                        )
                        
                        st.plotly_chart(fig_bar, use_container_width=True)
                    
                    with col2:
                        # Graphique en camembert
                        fig_pie = go.Figure(data=[go.Pie(
                            labels=['Réussies (100%)', 'Partielles (>0%)', 'Ratées (0%)'],
                            values=[nb_questions_reussies, nb_questions_partielles, nb_questions_ratees],
                            marker=dict(colors=['#28a745', '#ffc107', '#dc3545']),
                            hole=0.4,
                            textinfo='label+percent',
                            textposition='outside'
                        )])
                        
                        fig_pie.update_layout(
                            title="Répartition des résultats",
                            height=400,
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig_pie, use_container_width=True)
                    
                    # Bouton de téléchargement
                    st.markdown("---")
                    
                    # Générer un rapport détaillé
                    rapport = f"""
╔═══════════════════════════════════════════════════════════════════╗
║                    RELEVÉ DE NOTES DÉTAILLÉ                       ║
╚═══════════════════════════════════════════════════════════════════╝

ÉTUDIANT: {student_id}
MATIÈRE: {selected_matiere}
DATE: {pd.Timestamp.now().strftime('%d/%m/%Y à %H:%M')}

{'='*70}
NOTE GÉNÉRALE
{'='*70}

Note de base: {note_sur_20_base:.2f}/20
Bonus: +{bonus_total:.2f} points
Bonus global: +{bonus_global:.2f} points
NOTE FINALE: {note_sur_20_finale:.2f}/20

Points obtenus: {total_points_obtenus:.2f}/{total_bareme:.2f}
Taux de réussite: {pourcentage_reussite:.1f}%
Mention: {mention}

{'='*70}
DÉTAIL PAR QUESTION
{'='*70}

"""

                    for _, row in details_df.iterrows():
                        bonus_val = row['bonus']
                        bonus_txt = "-" if pd.isna(bonus_val) else (f"+{bonus_val:.2f}" if bonus_val > 0 else "-")

                        points_txt = "-" if pd.isna(row['points_obtenu']) else f"{row['points_obtenu']:.2f}"
                        pourc_txt = "-" if pd.isna(row['pourcentage_obtenu']) else f"{row['pourcentage_obtenu']:.1f}%"

                        statut_text = (
                            "Réussie" if row['statut'] == '✅ Réussie'
                            else "Partielle" if row['statut'] == '🟡 Partielle'
                            else "Ratée"
                        )

                        rapport += f"""
{row['question']}
  ├─ Barème: {row['bareme']:.2f} points
  ├─ Points obtenus: {points_txt} points
  ├─ Bonus: {bonus_txt} points
  ├─ Pourcentage: {pourc_txt}
  └─ Statut: {statut_text}
"""



                    
                    rapport += f"""
{'='*70}
STATISTIQUES
{'='*70}

Questions réussies (100%): {nb_questions_reussies}/{len(details)}
Réponses partielles (>0%): {nb_questions_partielles}/{len(details)}
Questions ratées (0%): {nb_questions_ratees}/{len(details)}
Taux moyen de réussite: {moyenne_pourcentage:.1f}%

{'='*70}
Fin du relevé de notes
{'='*70}
"""
                    
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        st.download_button(
                            label="📥 Télécharger le relevé détaillé",
                            data=rapport,
                            file_name=f"releve_{student_id}_{selected_matiere.replace(' ', '_')}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                else:
                    st.warning("⚠️ Aucun détail de note disponible pour cette matière.")
            
            else:
                st.error(f"❌ Aucun étudiant trouvé avec l'identifiant: **{student_id}**")
                st.info("💡 Vérifiez que votre identifiant est correct et réessayez.")

else:
    st.error("❌ Impossible de charger les données.")

# Instructions dans le footer
st.markdown("---")
with st.expander("📖 Guide d'utilisation"):
    st.markdown("""
    ### Comment consulter vos notes:
    
    1. **🆔 Entrez** votre identifiant étudiant
    2. **📖 Sélectionnez** la matière 
    3. **✅ Cliquez** sur VALIDER
    4. **📊 Consultez** vos résultats détaillés
    
    ### Informations affichées:
    
    - **Question**: Nom de la question ou exercice
    - **Barème**: Points maximum pour la question
    - **Points obtenus**: Vos points
    - **Bonus**: Points bonus si applicable
    - **Pourcentage**: Votre taux de réussite
    - **Note générale**: Note finale sur 20
    """)