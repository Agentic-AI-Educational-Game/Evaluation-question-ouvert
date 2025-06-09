# app.py
import streamlit as st
import json
import os
import pandas as pd # Pour st.dataframe

# Importer la fonction de workflow modifiée
try:
    from workflow import run_evaluation_workflow
except ImportError:
    st.error("Échec de l'importation de workflow.py. Assurez-vous qu'il se trouve dans le même répertoire ou accessible dans PYTHONPATH.")
    st.stop()


# --- Configuration de la Page ---
st.set_page_config(page_title="Workflow de Notation Automatisée", layout="wide")

st.title("📝 Workflow de Notation Automatisée")
st.markdown("""
Cette application démontre un workflow assisté par IA pour noter automatiquement les réponses des élèves.
Entrez le texte de contexte, la question et la réponse de l'élève ci-dessous, puis cliquez sur "Évaluer la Réponse".
Vous pouvez superviser chaque étape du processus d'évaluation dans les sections déroulantes qui apparaissent.
""")

# --- Vérification de la Clé API ---
if not os.environ.get("GROQ_API_KEY"):
    st.error("🚨 Variable d'environnement GROQ_API_KEY non définie ! Veuillez la définir avant de lancer l'application.")
    st.info("Vous pouvez la définir dans votre terminal, par ex., `export GROQ_API_KEY='votre_clé_api'` ou dans un fichier `.env` si vous utilisez un outil comme python-dotenv (non implémenté ici).")
    st.stop()
else:
    st.sidebar.success("GROQ_API_KEY trouvée !")

# --- Textes par Défaut (déjà en français) ---
DEFAULT_TEXT = """
Dans la cour de l'école, les élèves sont joyeux. Ils jouent en groupes. Certains font de la
corde à sauter. D'autres jouent à cache-cache. On entend des rires partout.
En classe, la maîtresse explique la leçon de mathématiques avec un grand sourire. Elle
écrit des chiffres au tableau. Les enfants l'écoutent avec attention.
Nous prenons nos livres et nos cahiers. Il est temps d'apprendre à faire des additions
et à résoudre des problèmes. La maîtresse nous montre comment faire. Chacun essaie
sur son cahier. Si on a du mal, on peut demander de l'aide. Petit à petit, on devient plus
fort en maths.
"""
DEFAULT_QUESTION = "Que fait la maîtresse ?"
DEFAULT_STUDENT_ANSWER = "La maitresse explique la lecon de mathematiques et elle ecrit au tableau"

# --- Champs de Saisie ---
st.header("📋 Entrées")
col1, col2 = st.columns(2)
with col1:
    text_input = st.text_area("📚 Texte de Contexte", value=DEFAULT_TEXT, height=250)
with col2:
    question_input = st.text_area("❓ Question", value=DEFAULT_QUESTION, height=100)
student_answer_input = st.text_area("✍️ Réponse de l'Élève", value=DEFAULT_STUDENT_ANSWER, height=100)

# --- État de Session ---
if 'workflow_steps' not in st.session_state:
    st.session_state.workflow_steps = None
if 'final_evaluation_result' not in st.session_state:
    st.session_state.final_evaluation_result = None
if 'evaluation_triggered' not in st.session_state:
    st.session_state.evaluation_triggered = False

# --- Fonction d'aide pour afficher joliment le JSON analysé ---
def display_parsed_output(data, step_name):
    """Affiche les données JSON analysées en utilisant les composants Streamlit appropriés."""
    if not isinstance(data, dict):
        st.json(data) # Solution de repli pour les données non-dict
        return

    # --- Logique d'affichage spécifique par agent/étape ---
    if "Question Understanding" in step_name or "Compréhension des Questions" in step_name:
        st.write(f"**Type de Question :** {data.get('question_type', 'N/A')}")
        st.write("**Concepts Clés Attendus :**")
        if data.get('key_concepts_expected'):
            for concept in data['key_concepts_expected']:
                st.markdown(f"- {concept}")
        else:
            st.write("N/A")
        st.write("**Attentes de l'Enseignant :**")
        if data.get('teacher_expectations'):
            for expectation in data['teacher_expectations']:
                st.markdown(f"- {expectation}")
        else:
            st.write("N/A")

    elif "Rubric Extraction" in step_name or "Extraction de Rubriques" in step_name:
        if data.get('rubric') and isinstance(data['rubric'], list):
            st.write("**Grille d'Évaluation (Rubrique) :**")
            if data['rubric']:
                df = pd.DataFrame(data['rubric'])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("La liste de la rubrique est vide.")
        else:
            st.write("Données de la rubrique non trouvées ou format de liste inattendu.")
            st.json(data)


    elif "Answer Understanding" in step_name or "Compréhension des Réponses" in step_name:
        st.write("**Concepts Trouvés :**")
        if data.get('concepts_found'):
            for concept in data['concepts_found']:
                st.markdown(f"- {concept}")
        else:
            st.write("N/A")
        
        st.write("**Entités Nommées :**")
        if data.get('named_entities'):
            for entity in data['named_entities']:
                st.markdown(f"- {entity}")
        else:
            st.write("N/A")

        st.write("**Dates Mentionnées :**")
        if data.get('dates'):
            for date_ref in data['dates']:
                st.markdown(f"- {date_ref}")
        else:
            st.write("N/A")

        if 'structure' in data and isinstance(data['structure'], dict):
            st.write("**Structure de la Réponse :**")
            structure = data['structure']
            st.write(f"- Cohérente : {structure.get('coherent', 'N/A')}")
            st.write(f"- A une Introduction : {structure.get('has_intro', 'N/A')}")
            st.write(f"- A un Corps : {structure.get('has_body', 'N/A')}")
            st.write(f"- A une Conclusion : {structure.get('has_conclusion', 'N/A')}")
        else:
            st.write("Données de structure non trouvées ou format de dictionnaire inattendu.")


    elif "Grammar and Language" in step_name or "Grammaire et Langue" in step_name:
        score_col, penalty_col = st.columns(2)
        with score_col:
            st.metric("Score de Grammaire (0-100)", value=data.get('grammar_score', 'N/A'))
        with penalty_col:
            st.metric("Pénalité Linguistique (%)", value=data.get('penalty', 'N/A'))
        
        if data.get('errors') and isinstance(data['errors'], list):
            st.write("**Erreurs Identifiées :**")
            if data['errors']:
                errors_df = pd.DataFrame(data['errors'])
                st.dataframe(errors_df, use_container_width=True)
            else:
                st.info("Aucune erreur grammaticale identifiée.")
        else:
            st.write("Données d'erreurs non trouvées ou format de liste inattendu.")
            st.json(data)


    elif "Evaluation Agent" in step_name or "Évaluation" == step_name:
        if 'total_score' in data:
            st.metric("Score Basé sur la Rubrique", value=data.get('total_score', 'N/A'))
        
        if data.get('scores') and isinstance(data['scores'], list):
            st.write("**Scores Détaillés :**")
            if data['scores']:
                scores_df = pd.DataFrame(data['scores'])
                st.dataframe(scores_df, use_container_width=True)
            else:
                st.info("La liste des scores détaillés est vide.")
        else:
            st.write("Données des scores détaillés non trouvées ou format de liste inattendu.")
            st.json(data)


    elif "Final Scoring" in step_name or "Notation Finale" in step_name:
        if 'final_score' in data:
            st.metric("Score Final (sur 100)", value=data.get('final_score', 'N/A'))
        if 'feedback' in data:
            st.write("**Feedback pour l'Élève :**")
            st.info(data['feedback'])
        else:
            st.json(data)


    else: # Solution de repli pour toute autre étape ou donnée inattendue
        st.json(data)

# --- Bouton d'Évaluation ---
if st.button("🚀 Évaluer la Réponse", type="primary"):
    if not text_input or not question_input or not student_answer_input:
        st.warning("Veuillez remplir tous les champs de saisie.")
    else:
        st.session_state.evaluation_triggered = True
        st.session_state.workflow_steps = None 
        st.session_state.final_evaluation_result = None

        with st.spinner("🧠 Évaluation en cours... Cela peut prendre un moment car les LLMs sont appelés..."):
            final_result, steps_data = run_evaluation_workflow(
                text_input, question_input, student_answer_input
            )
            st.session_state.workflow_steps = steps_data
            st.session_state.final_evaluation_result = final_result

# --- Affichage des Résultats ---
if st.session_state.evaluation_triggered:
    st.header("🔍 Supervision du Workflow & Résultats")

    if st.session_state.workflow_steps:
        for i, step in enumerate(st.session_state.workflow_steps):
            # Traduire les noms d'étapes s'ils viennent de workflow.py en anglais
            step_name_display = step['name']
            if "Question Understanding" in step_name_display: step_name_display = step_name_display.replace("Question Understanding", "Compréhension des Questions")
            if "Rubric Extraction" in step_name_display: step_name_display = step_name_display.replace("Rubric Extraction", "Extraction de Rubriques")
            if "Answer Understanding" in step_name_display: step_name_display = step_name_display.replace("Answer Understanding", "Compréhension des Réponses")
            if "Grammar and Language" in step_name_display: step_name_display = step_name_display.replace("Grammar and Language", "Grammaire et Langue")
            if "Evaluation Agent" in step_name_display: step_name_display = step_name_display.replace("Evaluation Agent", "Agent d'Évaluation")
            if "Final Scoring" in step_name_display: step_name_display = step_name_display.replace("Final Scoring", "Notation Finale")
            if "Logic Check" in step_name_display: step_name_display = step_name_display.replace("Logic Check", "Vérification Logique")

            status_display = "Succès" if step['status'] == "Success" else "Échec"
            expander_title = f"Étape {i+1}: {step_name_display} - Statut: {status_display}"
            
            is_last_successful_step = (i == len(st.session_state.workflow_steps) - 1) and step['status'] == "Success"
            expanded_default = (step['status'] == "Failure") or is_last_successful_step

            with st.expander(expander_title, expanded=expanded_default):
                st.subheader("Logs des Tentatives :")
                if step.get('attempts_logs'):
                    for log_entry in step['attempts_logs']:
                        st.text(log_entry)
                else:
                    st.write("Aucun log de tentative.")
                
                if step.get('parsed_output'):
                    st.subheader("Sortie Analysée :")
                    display_parsed_output(step['parsed_output'], step['name']) # step['name'] original pour la logique interne
                
                if step['status'] == "Failure" and step.get('error_message_detail'):
                    st.error(f"Détail de l'Erreur : {step['error_message_detail']}")
        
        st.divider()

    if st.session_state.final_evaluation_result:
        st.subheader("🏆 Résultat Final de l'Évaluation")
        # Utiliser display_parsed_output pour le résultat final également
        if st.session_state.workflow_steps and ("Final Scoring" in st.session_state.workflow_steps[-1]['name'] or "Notation Finale" in st.session_state.workflow_steps[-1]['name']):
             display_parsed_output(st.session_state.final_evaluation_result, "Notation Finale") # Utiliser un nom cohérent
        else:
            st.json(st.session_state.final_evaluation_result) 

        st.success("🎉 Workflow terminé avec succès !")
        # st.balloons() # Effet de succès supprimé

    elif st.session_state.workflow_steps: 
        st.error("❌ L'exécution du workflow a échoué. Veuillez examiner les étapes ci-dessus pour plus de détails.")