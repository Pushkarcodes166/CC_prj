========================================================================
AWS CLOUD DEPLOYMENT GUIDE: WORKFORCE MANAGEMENT SYSTEM
========================================================================
This guide provides baby step-by-step instructions to deploy your Python
Flask dashboard to the AWS Cloud utilizing the 5 Core Fundamentals 
of AWS (EC2, S3, IAM, VPC, RDS/Database). 

STEP 1: PREP YOUR CODE (GITHUB)
==============================
Before AWS can run your code, it needs a place to download it from.
1. Go to github.com and sign in.
2. Create a new repository titled "Workforce-Management-System".
3. Upload all your project folders/files (app.py, database.py, /templates, etc.) to this repo.

STEP 2: IAM (IDENTITY & ACCESS) - SECURITY PERMISSIONS
======================================================
1. Log into the AWS Management Console and search for "IAM".
2. Click "Roles" on the left menu -> "Create role".
3. Trusted Entity Type: Select "AWS Service".
4. Use Case: Select "EC2", click Next.
5. In Permissions, search for and check "AmazonS3FullAccess".
6. Click Next. Name the role "Workforce-EC2-Role", then create it.

STEP 3: S3 - CLOUD STORAGE FOR DOCUMENTS
=======================================
1. Search for "S3" in the top AWS search bar.
2. Click "Create bucket".
3. Enter a globally unique name (e.g., workforce-docs-eep).
4. Leave "Block all public access" turned ON (it's safer).
5. Click "Create bucket".
6. Click into the bucket, click "Upload", and upload any required HR documents or initial assets.

STEP 4: VPC (SECURITY GROUPS) - FIREWALL SETTINGS
=================================================
1. Search for "EC2" in the top search bar.
2. On the left menu, scroll down to Network & Security -> "Security Groups".
3. Click "Create security group".
4. Name it "Workforce-Web-SG" and add these Inbound Rules:
   - Type: HTTP  | Source: Anywhere-IPv4 (0.0.0.0/0)
   - Type: SSH   | Source: Anywhere-IPv4 (0.0.0.0/0) -> So the browser client works!
   - Type: Custom TCP | Port Range: 5000 | Source: Anywhere-IPv4 (0.0.0.0/0)
5. Click "Create security group".

STEP 5: RDS - RELATIONAL DATABASE SETUP
=======================================
1. Search for "RDS" in the top AWS search bar.
2. Click "Create database".
3. Select "MySQL" and choose the "Free tier" template.
4. Name the DB instance "workforce-db", set master username to "admin", and create a secure password.
5. Under Connectivity, for Virtual Private Cloud (VPC) security group, select "Choose existing" and select "Workforce-Web-SG".
6. Click "Create database" and wait for the "Endpoint" address to appear.

STEP 6: EC2 - VIRTUAL CLOUD SERVER
==================================
1. In the EC2 Dashboard, go to "Instances" -> "Launch instances".
2. Name the server "Workforce-Server".
3. OS Images: Select "Ubuntu" (Ubuntu Server 24.04 LTS).
4. Instance Type: Select "t2.micro" (for free tier).
5. Key Pair: Click "Create new key pair", name it "workforce-key", and download the .pem file.
6. Network Settings: 
   - Click "Edit".
   - Select "Select existing security group".
   - Choose the "Workforce-Web-SG" you just made.
7. Advanced Details: 
   - Find "IAM instance profile".
   - Choose "Workforce-EC2-Role".
8. Click "Launch instance".

STEP 7: CONNECTING TO THE SERVER
================================
1. Go back to your EC2 "Instances" list. Click on "Workforce-Server".
2. Click the orange "Connect" button at the top.
3. Choose the "EC2 Instance Connect" tab and hit "Connect".
4. A black terminal will open inside your browser. Type the following commands one by one, hitting Enter after each:

   sudo apt update -y
   sudo apt install python3-pip python3-venv git mysql-client -y
   git clone <YOUR-GITHUB-REPO-LINK-HERE>
   cd Workforce-Management-System
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   export DB_HOST="<YOUR_RDS_ENDPOINT>"
   export DB_USER="admin"
   export DB_PASS="<YOUR_SECURE_PASSWORD>"

STEP 8: RUNNING THE APPLICATION
===============================
1. In that same black terminal, start your Python application:
   
   python app.py

   (Keep this terminal tab open so the Python server stays running).

STEP 9: VIEWING YOUR LIVE WEBSITE
=================================
1. Look at your AWS Instance Summary page again.
2. Find the "Public IPv4 address" (e.g., 44.210.77.243).
3. Open a brand new browser tab, go to the top URL bar, and type:

   http://YOUR-PUBLIC-IP:5000

   (Example: http://44.210.77.243:5000)
4. Hit Enter! Your Workforce Management System is now live on the internet!
