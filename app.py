from flask import Flask, render_template, request
from sentence_transformers import SentenceTransformer, util
import mysql.connector
import re

app = Flask(__name__)

# Load BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')

# MySQL connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="KRISH2005",
    database="vivasense",
    port=3307
)
cursor = db.cursor()

questions_data = []


# ---------------- EVALUATION FUNCTION ----------------

def evaluate_answer(ideal, student, max_marks):

    ideal_emb = model.encode(ideal, convert_to_tensor=True)
    student_emb = model.encode(student, convert_to_tensor=True)

    similarity = util.cos_sim(ideal_emb, student_emb)
    meaning_score = float(similarity[0][0])

    if meaning_score < 0.35:
        return 0, 0

    marks = round(meaning_score * max_marks)
    return marks, round(meaning_score, 2)



@app.route("/")
def home():
    return render_template("home.html")




@app.route("/examiner", methods=["GET", "POST"])
def examiner():

    if request.method == "POST":
        question = request.form.get("question")
        ideal = request.form.get("ideal")
        max_marks = request.form.get("max_marks")

        if question and ideal and max_marks:
            if len(questions_data) < 10:
                questions_data.append({
                    "question": question,
                    "ideal": ideal,
                    "max_marks": int(max_marks)
                })

    return render_template("examiner.html", questions=questions_data)


# ---------------- STUDENT ----------------

@app.route("/student", methods=["GET", "POST"])
def student():

    results = []
    total_marks = 0
    total_max = 0

    if request.method == "POST":

        name = request.form.get("name")
        roll = request.form.get("roll")

        for i, q in enumerate(questions_data):

            answer = request.form.get(f"answer_{i}")

            if answer:

                marks, score = evaluate_answer(
                    q["ideal"],
                    answer,
                    q["max_marks"]
                )

                results.append({
                    "question": q["question"],
                    "marks": marks,
                    "max_marks": q["max_marks"],
                    "score": score
                })

                total_marks += marks
                total_max += q["max_marks"]

        # Save student record
        cursor.execute(
            "INSERT INTO students (name, roll_no, total_marks, total_max) VALUES (%s,%s,%s,%s)",
            (name, roll, total_marks, total_max)
        )
        db.commit()

        student_id = cursor.lastrowid

        # Save individual answers
        for i, r in enumerate(results):
            cursor.execute(
                "INSERT INTO evaluations (student_id, question, student_answer, marks, max_marks) VALUES (%s,%s,%s,%s,%s)",
                (
                    student_id,
                    questions_data[i]["question"],
                    request.form.get(f"answer_{i}"),
                    r["marks"],
                    r["max_marks"]
                )
            )
        db.commit()

    return render_template(
        "student.html",
        questions=questions_data,
        results=results,
        total_marks=total_marks,
        total_max=total_max
    )


# ---------------- RECORDS ----------------

@app.route("/records")
def records():

    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()

    return render_template("records.html", students=students)


if __name__ == "__main__":
    app.run(debug=True)