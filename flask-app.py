from flask import Flask, request, render_template, redirect, url_for
import json
import os
import traceback
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

# Load environment variables from .env file
load_dotenv()

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("MONGO_DB_NAME", "evaluation_results_db")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "evaluations")

client = None
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    evaluations_collection = db[COLLECTION_NAME]
    # The ismaster command is cheap and does not require auth.
    client.admin.command('ismaster')
    print("Connecté à MongoDB avec succès !")
except ConnectionFailure as e:
    print(f"Impossible de se connecter à MongoDB : {e}")
    client = None # S'assurer que le client est None si la connexion échoue
except Exception as e:
    print(f"Une erreur inattendue est survenue lors de la connexion à MongoDB : {e}")
    client = None

# Importer votre fonction de flux de travail
# Assurez-vous que workflow.py et le dossier Agents/ sont dans le même répertoire que app.py ou dans le chemin Python
try:
    from workflow import run_evaluation_workflow
except ImportError as e:
    print(f"Erreur lors de l'importation du flux de travail : {e}")
    print("Assurez-vous que workflow.py et le dossier Agents sont correctement placés et que __init__.py existe dans Agents.")
    run_evaluation_workflow = None # Pour que l'application puisse toujours démarrer et afficher une erreur

app = Flask(__name__)
app.secret_key = os.urandom(24) # For session management, flash messages etc.

# Example default texts
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
DEFAULT_ANSWER = "La maîtresse explique la leçon de mathématiques, écrit des chiffres au tableau, montre comment faire des additions et résoudre des problèmes, et aide les élèves quand ils ont du mal."


@app.route('/', methods=['GET', 'POST'])
def index():
    final_result = None
    steps_data = []
    error_message = None # For errors happening in app.py itself

    if not os.getenv("GROQ_API_KEY"):
        error_message = "CRITIQUE : La variable d'environnement GROQ_API_KEY n'est pas définie. Le flux de travail pourrait échouer si les agents en ont besoin."
        # Vous pourriez vouloir empêcher la soumission du formulaire ou afficher un avertissement plus visible
        # Pour les tests de stub, cela pourrait être acceptable, mais il est bon de le signaler.

    if run_evaluation_workflow is None:
        error_message = "Le module de flux de travail n'a pas pu être chargé. Veuillez vérifier les journaux du serveur."
        return render_template('index.html', error_message=error_message)

    if request.method == 'POST':
        text_input = request.form.get('text_input')
        question_input = request.form.get('question_input')
        student_answer_input = request.form.get('student_answer_input')

        if not all([text_input, question_input, student_answer_input]):
            error_message = "Tous les champs de saisie sont obligatoires."
            # Re-render form with an error, preserving existing inputs
            return render_template('index.html',
                                   error_message=error_message,
                                   text_input=text_input,
                                   question_input=question_input,
                                   student_answer_input=student_answer_input)
        try:
            print("Démarrage du flux de travail d'évaluation...")
            final_result, steps_data = run_evaluation_workflow(
                text_input, question_input, student_answer_input
            )
            print("Flux de travail terminé.")
            if final_result:
                print("Résultat final :", json.dumps(final_result, indent=2, ensure_ascii=False))
                
                # Extraire le score final et le feedback
                final_score = final_result.get('final_score')
                feedback = final_result.get('feedback')

                # Préparer les données pour MongoDB
                data_to_save = {
                    "text": text_input,
                    "question": question_input,
                    "student_answer": student_answer_input,
                    "final_score": final_score,
                    "feedback": feedback,
                    "timestamp": datetime.utcnow() # Ajouter un horodatage
                }

                # Sauvegarder dans MongoDB
                if client:
                    try:
                        evaluations_collection.insert_one(data_to_save)
                        print("Données sauvegardées avec succès dans MongoDB.")
                    except PyMongoError as mongo_e:
                        print(f"Erreur lors de la sauvegarde des données dans MongoDB : {mongo_e}")
                        error_message = f"Erreur lors de la sauvegarde des résultats : {str(mongo_e)}"
                else:
                    print("Client MongoDB non initialisé. Données non sauvegardées.")
                    error_message = "Base de données non connectée. Résultats non sauvegardés."
            else:
                print("Le flux de travail n'a pas produit de résultat final. Vérifiez les données des étapes pour les erreurs.")
            # print("Steps Data:", json.dumps(steps_data, indent=2, ensure_ascii=False))


        except Exception as e:
            print(f"Une erreur est survenue dans l'application Flask lors de l'exécution du flux de travail : {e}")
            traceback.print_exc()
            error_message = f"Une erreur inattendue est survenue : {str(e)}"
            # Optionally, you can pass steps_data if it was partially populated
            # steps_data.append({"name": "Flask App Error", "status": "Failure", "error_message_detail": str(e)})

        return render_template('index.html',
                               final_result=final_result,
                               steps_data=steps_data,
                               error_message=error_message,
                               # Pass back the inputs to repopulate the form
                               text_input=text_input,
                               question_input=question_input,
                               student_answer_input=student_answer_input)
    else: # GET request
        # Populate form with default values for GET request
        return render_template('index.html',
                               text_input=DEFAULT_TEXT.strip(),
                               question_input=DEFAULT_QUESTION.strip(),
                               student_answer_input=DEFAULT_ANSWER.strip(),
                               error_message=error_message # Show GROQ key warning if applicable
                               )

if __name__ == '__main__':
    if not os.getenv("GROQ_API_KEY"):
        print("AVERTISSEMENT : La variable d'environnement GROQ_API_KEY n'est pas définie. Les stubs pourraient fonctionner, mais les agents réels pourraient échouer.")
    app.run(debug=True)
