from flask import Flask, render_template, request, redirect
from sentence_transformers import SentenceTransformer, util
import mysql.connector

app = Flask(__name__)

model = SentenceTransformer('all-MiniLM-L6-v2')

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="KRISH2005",
    database="vivasense",
    port=3307
)
cursor = db.cursor()

# ---------------- AI ----------------
def evaluate_answer(ideal, student, max_marks):

    ideal_lower = ideal.lower()
    student_lower = student.lower()

    words = ideal_lower.split()
    match = sum(1 for w in words if w in student_lower)

    keyword_score = match / len(words) if len(words) > 0 else 0

    if keyword_score < 0.3:
        return 0, 0

    ideal_emb = model.encode(ideal, convert_to_tensor=True)
    student_emb = model.encode(student, convert_to_tensor=True)

    similarity = float(util.cos_sim(ideal_emb, student_emb)[0][0])

    if similarity < 0.4:
        return 0, 0

    final_score = (0.6 * similarity) + (0.4 * keyword_score)
    marks = round(final_score * max_marks)

    return marks, round(final_score, 2)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("home.html")

# ---------------- EXAMINER ----------------
@app.route("/examiner", methods=["GET", "POST"])
def examiner():

    if request.method == "POST":
        test_id = request.form.get("test_id")
        question = request.form.get("question")
        ideal = request.form.get("ideal")
        max_marks = int(request.form.get("max_marks"))

        cursor.execute(
            "INSERT INTO tests (test_id, question, ideal, max_marks) VALUES (%s,%s,%s,%s)",
            (test_id, question, ideal, max_marks)
        )
        db.commit()

    cursor.execute("SELECT DISTINCT test_id FROM tests")
    tests = cursor.fetchall()

    return render_template("examiner.html", tests=tests)

# ---------------- STUDENT ----------------
@app.route("/student", methods=["GET", "POST"])
def student():

    results = []
    total_marks = 0
    total_max = 0
    selected_test = []
    grade = ""

    name = ""
    roll = ""
    test_id = ""

    cursor.execute("SELECT DISTINCT test_id FROM tests")
    tests = cursor.fetchall()

    if request.method == "POST":

        action = request.form.get("action")
        name = request.form.get("name")
        roll = request.form.get("roll")
        test_id = request.form.get("test_id")

        if action == "load":
            cursor.execute("SELECT * FROM tests WHERE test_id = %s", (test_id,))
            rows = cursor.fetchall()

            for r in rows:
                selected_test.append({
                    "question": r[2],
                    "ideal": r[3],
                    "max_marks": r[4]
                })

        elif action == "submit":

            cursor.execute("SELECT * FROM tests WHERE test_id = %s", (test_id,))
            rows = cursor.fetchall()

            for i, r in enumerate(rows):
                answer = request.form.get(f"answer_{i}")

                if answer:
                    marks, score = evaluate_answer(r[3], answer, r[4])

                    results.append({
                        "question": r[2],
                        "marks": marks,
                        "max_marks": r[4]
                    })

                    total_marks += marks
                    total_max += r[4]

            if total_max > 0:
                percentage = (total_marks / total_max) * 100

                if percentage >= 90:
                    grade = "A+"
                elif percentage >= 80:
                    grade = "A"
                elif percentage >= 70:
                    grade = "B+"
                elif percentage >= 60:
                    grade = "B"
                elif percentage >= 50:
                    grade = "C"
                else:
                    grade = "F"

            cursor.execute(
                "INSERT INTO students (name, roll_no, total_marks, total_max) VALUES (%s,%s,%s,%s)",
                (name, roll, total_marks, total_max)
            )
            db.commit()

    return render_template(
        "student.html",
        tests=tests,
        questions=selected_test,
        results=results,
        total_marks=total_marks,
        total_max=total_max,
        grade=grade,
        name=name,
        roll=roll,
        test_id=test_id
    )

# ---------------- RECORDS ----------------
@app.route("/records")
def records():
    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()

    students = []

    for r in rows:
        percentage = (r[3] / r[4] * 100) if r[4] != 0 else 0

        students.append({
            "id": r[0],
            "name": r[1],
            "roll": r[2],
            "marks": r[3],
            "max": r[4],
            "percentage": round(percentage, 2)
        })

    return render_template("records.html", students=students)

# ---------------- DELETE STUDENT ----------------
@app.route("/delete_record/<int:id>")
def delete_record(id):

    cursor.execute("DELETE FROM evaluations WHERE student_id = %s", (id,))
    cursor.execute("DELETE FROM students WHERE id = %s", (id,))
    db.commit()

    return redirect("/records")

# ---------------- DELETE TEST ----------------
@app.route("/delete_test/<test_id>")
def delete_test(test_id):

    cursor.execute("DELETE FROM tests WHERE test_id = %s", (test_id,))
    db.commit()

    return redirect("/examiner")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
