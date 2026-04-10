from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import mysql.connector
import os

# ================= CONFIG =================
app = Flask(__name__, template_folder='templates_employee')
app.secret_key = 'your_secret_key'

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "admin"),
    "password": os.environ.get("DB_PASS", "root"),
    "database": "workforce_db" 
}

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
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM employees WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash('Login successful', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')

    return render_template('login.html')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect(url_for('login'))

# ---------- TASKS ----------
@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        task_id = request.form['task_id']
        status = request.form['status']
        cursor.execute(
            "UPDATE tasks SET status=%s WHERE id=%s AND employee_id=%s",
            (status, task_id, session['user_id'])
        )
        conn.commit()

    cursor.execute("""
        SELECT tasks.id, employees.name AS name, tasks.task, tasks.status 
        FROM tasks 
        JOIN employees ON tasks.employee_id = employees.id
        WHERE tasks.employee_id = %s
    """, (session['user_id'],))
    data = cursor.fetchall()
    
    return render_template('tasks.html', tasks=data, employees=[])

# ---------- ATTENDANCE ----------
@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        date = request.form['date']
        status = request.form['status']

        cursor.execute(
            "INSERT INTO attendance (employee_id, date, status) VALUES (%s,%s,%s)",
            (session['user_id'], date, status)
        )
        conn.commit()

    cursor.execute("""
        SELECT attendance.id, employees.name AS name, attendance.date, attendance.status
        FROM attendance
        JOIN employees ON attendance.employee_id = employees.id
        WHERE attendance.employee_id = %s
    """, (session['user_id'],))
    attendance_records = cursor.fetchall()

    return render_template(
        'attendance.html',
        attendance_records=attendance_records,
        employees=[{'id': session['user_id'], 'name': session.get('user_name', 'You')}]
    )

# ---------- SHIFTS ----------
@app.route('/shifts', methods=['GET'])
@login_required
def shifts():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT shifts.id, employees.name AS name, shifts.shift_time 
        FROM shifts 
        JOIN employees ON shifts.employee_id = employees.id
        WHERE shifts.employee_id = %s
    """, (session['user_id'],))
    data = cursor.fetchall()

    return render_template('shifts.html', shifts=data, employees=[])

# ---------- LEAVE MODULE ----------
@app.route('/leave', methods=['GET', 'POST'])
@login_required
def leave():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        reason = request.form['reason']

        cursor.execute(
            "INSERT INTO leaves (employee_id, reason, status) VALUES (%s,%s,%s)",
            (session['user_id'], reason, "Pending")
        )
        conn.commit()

    cursor.execute("""
        SELECT leaves.id, employees.name AS name, leaves.reason, leaves.status 
        FROM leaves 
        JOIN employees ON leaves.employee_id = employees.id
        WHERE leaves.employee_id = %s
    """, (session['user_id'],))
    data = cursor.fetchall()

    return render_template('leave.html', leaves=data, employees=[{'id': session['user_id'], 'name': session.get('user_name', 'You')}])

# ---------- PERFORMANCE ----------
@app.route('/performance')
@login_required
def performance():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE employee_id=%s AND status='Completed'", (session['user_id'],))
    t = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM shifts WHERE employee_id=%s", (session['user_id'],))
    s = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE employee_id=%s AND status='Present'", (session['user_id'],))
    p = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leaves WHERE employee_id=%s AND status='Approved'", (session['user_id'],))
    a = cursor.fetchone()[0]

    conn.close()
    return render_template(
        'performance.html',
        no_of_tasks=t,
        no_of_shifts=s,
        no_of_present=p,
        no_of_absent=a,
        no_of_employees=1
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)