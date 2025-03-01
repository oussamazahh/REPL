from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import sys
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///REPL.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    scripts = db.relationship('Script', backref='author', lazy=True)

class Script(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        password = generate_password_hash(request.form['password'])
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/save', methods=['POST'])
@login_required
def save_script():
    data = request.get_json()
    title = data.get('title')
    code = data.get('code')
    language = data.get('language')
    script = Script(title=title, code=code, language=language, user_id=current_user.id)
    db.session.add(script)
    db.session.commit()
    return jsonify({'message': 'Script saved successfully'})

@app.route('/scripts')
@login_required
def get_scripts():
    scripts = Script.query.filter_by(user_id=current_user.id).all()
    scripts_data = [{'id': s.id, 'title': s.title, 'code': s.code, 'language': s.language} for s in scripts]
    return jsonify(scripts_data)

@app.route('/execute', methods=['POST'])
def execute_code():
    data = request.get_json()
    code = data.get('code')
    language = data.get('language')
    try:
        if language == 'javascript':
            result = subprocess.run(['node', '-e', code], capture_output=True, text=True, timeout=5)
            output = result.stdout + result.stderr
        elif language == 'python':
            return jsonify({'output': 'Use Pyodide for Python execution'})  
        elif language == 'java':
            file_name = 'Main.java'
            with open(file_name, 'w') as f:
                f.write(code)
            result = subprocess.run(['javac', file_name], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                output = result.stderr
            else:
                result = subprocess.run(['java', 'Main'], capture_output=True, text=True, timeout=5)
                output = result.stdout + result.stderr
            os.remove(file_name)
        elif language == 'c':
            file_name = 'main.c'
            with open(file_name, 'w') as f:
                f.write(code)
            result = subprocess.run(['gcc', file_name], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                output = result.stderr
            else:
                result = subprocess.run(['./a.out'], capture_output=True, text=True, timeout=5)
                output = result.stdout + result.stderr
            os.remove('a.out')
        else:
            output = 'Unsupported language'
        return jsonify({'output': output})
    except subprocess.TimeoutExpired:
        return jsonify({'output': 'Execution timed out'})

@app.route('/delete/<int:script_id>', methods=['DELETE'])
@login_required
def delete_script(script_id):
    script = Script.query.get_or_404(script_id)
    if script.author != current_user:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(script)
    db.session.commit()
    return jsonify({'message': 'Script deleted successfully'})
    
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)