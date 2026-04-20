from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, datetime
import mysql.connector
import os
import boto3

# ================= CONFIG =================
app = Flask(__name__, template_folder='templates_employee')
app.secret_key = 'your_secret_key'

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "wfms-database-v2.cs1ui6eo0uvn.us-east-1.rds.amazonaws.com"),
    "user": os.environ.get("DB_USER", "admin"),
    "password": os.environ.get("DB_PASS", "shravani1508"), # Use the new password you set in AWS Console
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

        pass_matched = False
        if user and user.get('password'):
            try:
                pass_matched = check_password_hash(user['password'], password)
            except ValueError:
                # Support old plaintext passwords natively
                pass_matched = (user['password'] == password)

        if pass_matched:
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
        # Requirement 3: Captures the exact time the status changed
        cursor.execute(
            "UPDATE tasks SET status=%s, updated_at=NOW() WHERE id=%s", 
            (status, task_id)
        )
        conn.commit()

    # --- CHANGES MADE HERE ---
    # Added: AND tasks.due_date >= CURDATE()
    # This filters out any tasks from yesterday or earlier
    cursor.execute("""
        SELECT tasks.id, employees.name AS name, tasks.task, tasks.status, tasks.due_date 
        FROM tasks 
        JOIN employees ON tasks.employee_id = employees.id
        WHERE tasks.employee_id = %s AND tasks.due_date >= CURDATE()
        ORDER BY tasks.due_date ASC
    """, (session['user_id'],))
    data = cursor.fetchall()
    
    conn.close()
    return render_template('tasks.html', tasks=data, employees=[])

# ---------- ATTENDANCE ----------
# ---------- ATTENDANCE (UPDATED) ----------
@app.route('/attendance', methods=['GET', 'POST'])
@login_required
def attendance():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # 1. FORCE TODAY'S DATE (Requirement #2)
        # We ignore 'request.form' for the date and use the server's clock
        today_date = date.today()
        status = request.form.get('status', 'Present')

        # 2. DUPLICATE CHECK (Requirement #1)
        # Check if this employee already has a record for today
        cursor.execute(
            "SELECT id FROM attendance WHERE employee_id = %s AND date = %s", 
            (session['user_id'], today_date)
        )
        already_marked = cursor.fetchone()

        if already_marked:
            flash('Error: You have already marked attendance for today!', 'error')
        else:
            # 3. INSERT RECORD
            # The 'submitted_at' timestamp column in RDS will fill itself automatically
            try:
                cursor.execute(
                    "INSERT INTO attendance (employee_id, date, status) VALUES (%s, %s, %s)",
                    (session['user_id'], today_date, status)
                )
                conn.commit()
                flash('Attendance marked successfully!', 'success')
            except Exception as e:
                flash(f'Database Error: {str(e)}', 'error')

    # This part shows the history table to the employee
    cursor.execute("""
        SELECT attendance.id, employees.name AS name, attendance.date, attendance.status
        FROM attendance
        JOIN employees ON attendance.employee_id = employees.id
        WHERE attendance.employee_id = %s
        ORDER BY attendance.date DESC
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

    # --- CHANGES MADE HERE ---
    # 1. Added 'shifts.shift_date' to the SELECT so it can be displayed
    # 2. Added 'AND shifts.shift_date >= CURDATE()' to filter out the past
    # 3. Added 'ORDER BY' to show the most recent shift first
    cursor.execute("""
        SELECT shifts.id, employees.name AS name, shifts.shift_time, shifts.shift_date 
        FROM shifts 
        JOIN employees ON shifts.employee_id = employees.id
        WHERE shifts.employee_id = %s AND shifts.shift_date >= CURDATE()
        ORDER BY shifts.shift_date ASC
    """, (session['user_id'],))
    
    data = cursor.fetchall()
    conn.close()

    return render_template('shifts.html', shifts=data, employees=[])

# ---------- LEAVE MODULE ----------
@app.route('/leave', methods=['GET', 'POST'])
@login_required
def leave():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        reason = request.form['reason']
        file_url = None
        
        file = request.files.get('file')
        if file and file.filename != '':
            try:
                s3 = boto3.client('s3', region_name='us-east-1')
                bucket_name = "wfms-assets-12345"
                file_key = f"leaves/{session['user_id']}_{file.filename.replace(' ', '_')}"
                # Removed ACL='public-read' to prevent Block Public Access crash. Instead presigned URL or direct link relying on bucket policy.
                s3.upload_fileobj(file, bucket_name, file_key)
                file_url = f"https://{bucket_name}.s3.amazonaws.com/{file_key}"
            except Exception as e:
                print("S3 Upload Failed:", str(e))
                pass

        cursor.execute(
            "INSERT INTO leaves (employee_id, reason, status, document_url) VALUES (%s,%s,%s,%s)",
            (session['user_id'], reason, "Pending", file_url)
        )
        conn.commit()

    cursor.execute("""
        SELECT leaves.id, employees.name AS name, leaves.reason, leaves.status, leaves.document_url 
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