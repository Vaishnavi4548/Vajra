from flask import Flask, render_template, request, redirect, url_for, session
from flask_session import Session
from pymongo import MongoClient
from bson import Binary
from werkzeug.security import generate_password_hash
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ashwin'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["vajra_audit"]
users_collection = db["users"]
user_audits_collection = db["useraudits"]

# Create upload folder if not exists
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ---------------- Routes ---------------- #

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup', methods=['POST'])
def signup():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')

    if not username or not email or not password:
        return "Missing required fields!", 400

    if users_collection.find_one({"email": email}):
        return "User already exists!", 400

    users_collection.insert_one({
        "username": username,
        "email": email,
        "password": generate_password_hash(password)
    })

    session['username'] = username
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    user_audits = user_audits_collection.find_one({"username": username})
    audits = user_audits.get("audits", []) if user_audits else []

    return render_template('dashboard.html', username=username, audits=audits)


@app.route('/submit_audit', methods=['POST'])
def submit_audit():
    if 'username' not in session:
        return redirect(url_for('index'))

    username = session['username']

    audit_type = request.form.get('audit_type')
    audit_date = request.form.get('audit_date')
    audit_time = request.form.get('audit_time')
    auditor_name = request.form.get('auditor_name')
    org_name = request.form.get('org_name')
    department = request.form.get('department')

    belarc_file = request.files.get('belarcReport')
    history_file = request.files.get('browserHistory')
    downloads_file = request.files.get('browserDownloads')

    if not belarc_file or not history_file or not downloads_file:
        return "All three files must be uploaded!", 400

    # Read file data
    belarc_data = belarc_file.read()
    history_data = history_file.read()
    downloads_data = downloads_file.read()

    # Create audit entry
    audit_entry = {
        "audit_type": audit_type,
        "audit_date": audit_date,
        "audit_time": audit_time,
        "auditor_name": auditor_name,
        "organization": org_name,
        "department": department,
        "belarc_report": {
            "filename": belarc_file.filename,
            "data": Binary(belarc_data)
        },
        "browser_history": {
            "filename": history_file.filename,
            "data": Binary(history_data)
        },
        "browser_downloads": {
            "filename": downloads_file.filename,
            "data": Binary(downloads_data)
        }
    }

    # Insert audit into user audit list
    user_audits_collection.update_one(
        {"username": username},
        {"$push": {"audits": audit_entry}},
        upsert=True
    )

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/google-login', methods=['POST'])
def google_login():
    return "Google login not implemented yet", 501


if __name__ == '__main__':
    app.run(debug=True)
