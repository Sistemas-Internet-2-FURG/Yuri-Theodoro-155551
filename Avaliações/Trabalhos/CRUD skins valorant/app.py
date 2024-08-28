import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Função para obter conexão com o banco de dados
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para criar a tabela users
def create_users_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()

# Função para criar outras tabelas, se necessário
def create_other_tables():
    conn = get_db_connection()
    # Adicione a criação de outras tabelas aqui, se necessário
    conn.close()

# Função de carregamento do usuário para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user is None:
        return None
    return User(user['id'], user['username'], user['password'])

# Classe User para gerenciar autenticação
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Rotas para a aplicação
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/colecoes')
@login_required
def list_colecoes():
    conn = get_db_connection()
    colecoes = conn.execute('SELECT * FROM colecoes').fetchall()
    conn.close()
    return render_template('colecoes.html', colecoes=colecoes)

@app.route('/colecoes/novo', methods=['GET', 'POST'])
@login_required
def add_colecao():
    if request.method == 'POST':
        nome = request.form['nome']
        if nome:
            conn = get_db_connection()
            conn.execute('INSERT INTO colecoes (nome) VALUES (?)', (nome,))
            conn.commit()
            conn.close()
            return redirect(url_for('list_colecoes'))
        else:
            return "Nome da coleção não pode estar vazio.", 400
    return render_template('add_colecao.html')

@app.route('/colecoes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def edit_colecao(id):
    conn = get_db_connection()
    if request.method == 'POST':
        nome = request.form['nome']
        if nome:
            conn.execute('UPDATE colecoes SET nome = ? WHERE id = ?', (nome, id))
            conn.commit()
            conn.close()
            return redirect(url_for('list_colecoes'))
        else:
            return "Nome da coleção não pode estar vazio.", 400
    colecao = conn.execute('SELECT * FROM colecoes WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('edit_colecao.html', colecao=colecao)

@app.route('/colecoes/<int:id>/deletar', methods=['POST'])
@login_required
def delete_colecao(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM colecoes WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('list_colecoes'))

@app.route('/skins')
@login_required
def list_skins():
    conn = get_db_connection()
    
    colecao_id = request.args.get('colecao_id')
    nome_arma = request.args.get('nome_arma', '')

    query = '''
        SELECT skins.id, skins.nome, colecoes.nome AS colecao_nome
        FROM skins
        JOIN colecoes ON skins.colecao_id = colecoes.id
        WHERE 1=1
    '''

    params = []

    if colecao_id:
        query += ' AND colecoes.id = ?'
        params.append(colecao_id)
    
    if nome_arma:
        query += ' AND skins.nome LIKE ?'
        params.append(f'%{nome_arma}%')
    
    skins = conn.execute(query, params).fetchall()
    colecoes = conn.execute('SELECT * FROM colecoes').fetchall()
    conn.close()
    return render_template('skins.html', skins=skins, colecoes=colecoes, colecao_id=colecao_id, nome_arma=nome_arma)

@app.route('/skins/novo', methods=['GET', 'POST'])
@login_required
def add_skin():
    conn = get_db_connection()
    if request.method == 'POST':
        nome = request.form['nome']
        colecao_id = request.form['colecao_id']
        if nome and colecao_id:
            conn.execute('INSERT INTO skins (nome, colecao_id) VALUES (?, ?)', (nome, colecao_id))
            conn.commit()
            conn.close()
            return redirect(url_for('list_skins'))
        else:
            return "Nome da skin e ID da coleção não podem estar vazios.", 400
    colecoes = conn.execute('SELECT * FROM colecoes').fetchall()
    conn.close()
    return render_template('add_skin.html', colecoes=colecoes)

@app.route('/skins/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def edit_skin(id):
    conn = get_db_connection()
    if request.method == 'POST':
        nome = request.form['nome']
        colecao_id = request.form['colecao_id']
        if nome and colecao_id:
            conn.execute('UPDATE skins SET nome = ?, colecao_id = ? WHERE id = ?', (nome, colecao_id, id))
            conn.commit()
            conn.close()
            return redirect(url_for('list_skins'))
        else:
            return "Nome da skin e ID da coleção não podem estar vazios.", 400
    skin = conn.execute('SELECT * FROM skins WHERE id = ?', (id,)).fetchone()
    colecoes = conn.execute('SELECT * FROM colecoes').fetchall()
    conn.close()
    return render_template('edit_skin.html', skin=skin, colecoes=colecoes)

@app.route('/skins/<int:id>/deletar', methods=['POST'])
@login_required
def delete_skin(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM skins WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('list_skins'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username'], user['password']))
            return redirect(url_for('index'))
        else:
            flash('Login inválido.')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Nome de usuário já existe.')
            return redirect(url_for('register'))
    return render_template('register.html')

# Criação das tabelas na inicialização da aplicação
if __name__ == '__main__':
    create_users_table()
    create_other_tables()
    app.run(debug=True)
