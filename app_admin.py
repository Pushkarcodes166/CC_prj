from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import mysql.connector
import os
import boto3

# ================= CONFIG =================
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Config (RDS via env vars, fallback to LOCAL)
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "admin"),
    "password": os.environ.get("DB_PASS", "root"),
    "database": "workforce_db" 
}

# File Upload Config
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# AWS S3 Config (for later use)
S3_BUCKET = "your-bucket-name"

# =========================================

# ================= DB CONNECTION =================
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# ================= AUTH DECORATOR =================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ================= DASHBOARD STATS =================
def get_statistics():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM employees")
    employees = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks")
    tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shifts")
    shifts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE status='Present'")
    present = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE status='Absent'")
    absent = cursor.fetchone()[0]

    conn.close()
    return employees, tasks, shifts, present, absent

# ================= ROUTES =================

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            flash('Login successful', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')

    return render_template('login.html')

# ---------- SIGNUP ----------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s,%s,%s)",
                (name, email, password)
            )
            conn.commit()
            flash('Account created', 'success')
            return redirect(url_for('login'))
        except:
            flash('Email already exists', 'error')

    return render_template('signup.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect(url_for('login'))

# ---------- EMPLOYEES ----------
@app.route('/employees', methods=['GET', 'POST'])
@login_required
def employees():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        position = request.form['position']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        try:
            cursor.execute(
                "INSERT INTO employees (name, position, email, password) VALUES (%s,%s,%s,%s)",
                (name, position, email, password)
            )
            conn.commit()
            flash('Employee added successfully', 'success')
        except Exception as e:
            flash(f'Error adding employee: possibly duplicate email.', 'error')

    cursor.execute("SELECT * FROM employees")
    data = cursor.fetchall()
    return render_template('employees.html', employees=data)

@app.route('/delete_employee/<int:id>')
@login_required
def delete_employee(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM employees WHERE id=%s", (id,))
    conn.commit()
    return redirect(url_for('employees'))

# ---------- TASKS ----------
@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        employee_id = request.form['employee_id']
        task = request.form['task']
        status = request.form['status']

        cursor.execute(
            "INSERT INTO tasks (employee_id, task, status) VALUES (%s,%s,%s)",
            (employee_id, task, status)
        )
        conn.commit()

    cursor.execute("""
        SELECT tasks.id, employees.name AS name, tasks.task, tasks.status 
        FROM tasks 
        JOIN employees ON tasks.employee_id = employees.id
    """)
    data = cursor.fetchall()

    cursor.execute("SELECT * FROM employees")
    employees_data = cursor.fetchall()

    return render_template('tasks.html', tasks=data, employees=employees_data)

@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task_route(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id=%s", (task_id,))
    conn.commit()
    return redirect(url_for('tasks'))

# ---------- ATTENDANCE ----------
@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        employee_id = request.form['employee_id']
        date = request.form['date']
        status = request.form['status']

        cursor.execute(
            "INSERT INTO attendance (employee_id, date, status) VALUES (%s,%s,%s)",
            (employee_id, date, status)
        )
        conn.commit()

    # ✅ JOIN to get employee name
    cursor.execute("""
        SELECT attendance.id, employees.name AS name, attendance.date, attendance.status
        FROM attendance
        JOIN employees ON attendance.employee_id = employees.id
    """)
    attendance_records = cursor.fetchall()

    # ✅ employees for dropdown
    cursor.execute("SELECT * FROM employees")
    employees = cursor.fetchall()

    return render_template(
        'attendance.html',
        attendance_records=attendance_records,
        employees=employees
    )

@app.route('/delete_attendance/<int:id>')
@login_required
def delete_attendance(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM attendance WHERE id=%s", (id,))
    conn.commit()
    return redirect(url_for('attendance'))

def test_db():
    try:
        conn = get_db_connection()
        return "Database connected successfully!"
    except Exception as e:
        return str(e)

# ---------- SHIFTS ----------
@app.route('/shifts', methods=['GET', 'POST'])
@login_required
def shifts():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        employee_id = request.form['employee_id']
        shift_time = request.form['shift_time']

        cursor.execute(
            "INSERT INTO shifts (employee_id, shift_time) VALUES (%s,%s)",
            (employee_id, shift_time)
        )
        conn.commit()

    cursor.execute("""
        SELECT shifts.id, employees.name AS name, shifts.shift_time 
        FROM shifts 
        JOIN employees ON shifts.employee_id = employees.id
    """)
    data = cursor.fetchall()

    cursor.execute("SELECT * FROM employees")
    employees_data = cursor.fetchall()

    return render_template('shifts.html', shifts=data, employees=employees_data)

@app.route('/delete_shift/<int:shift_id>')
@login_required
def delete_shift_route(shift_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shifts WHERE id=%s", (shift_id,))
    conn.commit()
    return redirect(url_for('shifts'))

# ---------- LEAVE MODULE (NEW) ----------
@app.route('/leave', methods=['GET', 'POST'])
@login_required
def leave():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        employee_id = request.form['employee_id']
        reason = request.form['reason']

        cursor.execute(
            "INSERT INTO leaves (employee_id, reason, status) VALUES (%s,%s,%s)",
            (employee_id, reason, "Pending")
        )
        conn.commit()

    cursor.execute("""
        SELECT leaves.id, employees.name AS name, leaves.reason, leaves.status 
        FROM leaves 
        JOIN employees ON leaves.employee_id = employees.id
    """)
    data = cursor.fetchall()

    cursor.execute("SELECT * FROM employees")
    employees_data = cursor.fetchall()

    return render_template('leave.html', leaves=data, employees=employees_data)

@app.route('/delete_leave/<int:leave_id>')
@login_required
def delete_leave_route(leave_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leaves WHERE id=%s", (leave_id,))
    conn.commit()
    return redirect(url_for('leave'))

# ---------- FILE UPLOAD ----------
@app.route('/upload', methods=['POST'])
@login_required
def upload():
    file = request.files['file']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    return "File uploaded successfully"

# ---------- PERFORMANCE ----------
@app.route('/performance')
@login_required
def performance():
    e, t, s, p, a = get_statistics()
    return render_template(
        'performance.html',
        no_of_employees=e,
        no_of_tasks=t,
        no_of_shifts=s,
        no_of_present=p,
        no_of_absent=a
    )

# =========================================

@app.route("/test-db")
def test_db_route():
    return test_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)