#!/bin/bash
sudo apt update -y
sudo apt install python3-pip python3-venv git mysql-client -y

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASS" -e "CREATE DATABASE IF NOT EXISTS workforce_db; USE workforce_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    position VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    password TEXT
);

CREATE TABLE IF NOT EXISTS shifts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT,
    shift_time TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT,
    date VARCHAR(255) NOT NULL,
    status VARCHAR(255) NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT,
    task TEXT NOT NULL,
    status VARCHAR(255) NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS leaves (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT,
    reason TEXT NOT NULL,
    status VARCHAR(255) DEFAULT 'Pending',
    FOREIGN KEY (employee_id) REFERENCES employees (id) ON DELETE CASCADE
);

-- Safely attempt to add the document_url column if reusing an old database
ALTER TABLE leaves ADD COLUMN document_url VARCHAR(500);"

echo "Database schemas updated."

# Start Admin App in background on port 5000
nohup python3 app_admin.py > admin.log 2>&1 &
echo "Admin App started on Port 5000."

# Start Employee App in background on port 8000
nohup python3 app_employee.py > employee.log 2>&1 &
echo "Employee App started on Port 8000."

echo "Deployment complete! Make sure Port 5000 and 8000 are open in your AWS Security Group."
