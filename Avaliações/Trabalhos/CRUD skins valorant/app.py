import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

#Criação da instância do Flask
app = Flask(__name__)
app.secret_key = 'your_secret_key' 

# Configuração do Flask-Login para gerenciar autenticação
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Página de login quando usuário não autenticado tenta acessar uma rota protegida

#função para obter conexão com o banco de dados
def get_db_connection():
    conn = sqlite3.connect('database.db')  #Conecta ao banco de dados
    conn.row_factory = sqlite3.Row  # ermite acessar as colunas pelo nome
    return conn

#Função para criar a tabela de usuários
def create_users_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
    ''')  #Cria a tabela se não existir
    conn.commit()
    conn.close()

#Função para criar a tabela de coleções
def create_colecoes_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS colecoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL
        );
    ''')  #Cria a tabela se não existir
    conn.commit()
    conn.close()

#Função para criar a tabela de skins
def create_skins_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS skins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            colecao_id INTEGER,
            FOREIGN KEY (colecao_id) REFERENCES colecoes (id)
        );
    ''')  #Cria a tabela se não existir, com relação estrangeira para coleções
    conn.commit()
    conn.close()

#Função para criar outras tabelas necessárias
def create_other_tables():
    create_colecoes_table()
    create_skins_table()

#Classe User para gerenciar a autenticação do usuário
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def get_id(self):
        return str(self.id)

#Função para carregar um usuário pelo ID, necessário para o Flask-Login
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    finally:
        conn.close()
    
    if user is None:
        return None
    return User(user['id'], user['username'], user['password'])

#Rota para a página inicial
@app.route('/')
def index():
    return render_template('index.html')

#Rota para listar coleções
@app.route('/colecoes')
@login_required
def list_colecoes():
    conn = get_db_connection()
    try:
        colecoes = conn.execute('SELECT * FROM colecoes').fetchall()
    finally:
        conn.close()
    return render_template('colecoes.html', colecoes=colecoes)

#Rota para adicionar uma nova coleção
@app.route('/colecoes/novo', methods=['GET', 'POST'])
@login_required
def add_colecao():
    if request.method == 'POST':
        nome = request.form['nome']
        if nome:
            conn = get_db_connection()
            try:
                conn.execute('INSERT INTO colecoes (nome) VALUES (?)', (nome,))
                conn.commit()
            finally:
                conn.close()
            return redirect(url_for('list_colecoes'))
        else:
            return "Nome da coleção não pode estar vazio.", 400
    return render_template('add_colecao.html')

#Rota para editar uma coleção existente
@app.route('/colecoes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def edit_colecao(id):
    conn = get_db_connection()
    if request.method == 'POST':
        nome = request.form['nome']
        if nome:
            try:
                conn.execute('UPDATE colecoes SET nome = ? WHERE id = ?', (nome, id))
                conn.commit()
            finally:
                conn.close()
            return redirect(url_for('list_colecoes'))
        else:
            return "Nome da coleção não pode estar vazio.", 400
    colecao = conn.execute('SELECT * FROM colecoes WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('edit_colecao.html', colecao=colecao)

#Rota para deletar uma coleção
@app.route('/colecoes/<int:id>/deletar', methods=['POST'])
@login_required
def delete_colecao(id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM colecoes WHERE id = ?', (id,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('list_colecoes'))

#Rota para listar skins, com filtros opcionais
@app.route('/skins')
@login_required
def list_skins():
    conn = get_db_connection()
    
    colecao_id = request.args.get('colecao_id')  #Obtém parâmetros da query string
    nome_arma = request.args.get('nome_arma', '')

    #Monta a consulta SQL dinamicamente com base nos filtros
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
    
    try:
        skins = conn.execute(query, params).fetchall()
        colecoes = conn.execute('SELECT * FROM colecoes').fetchall()
    finally:
        conn.close()

    return render_template('skins.html', skins=skins, colecoes=colecoes, colecao_id=colecao_id, nome_arma=nome_arma)

#Rota para adicionar uma nova skin, protegida por autenticação
@app.route('/skins/novo', methods=['GET', 'POST'])
@login_required
def add_skin():
    conn = get_db_connection()
    if request.method == 'POST':
        nome = request.form['nome']
        colecao_id = request.form['colecao_id']
        if nome and colecao_id:
            try:
                conn.execute('INSERT INTO skins (nome, colecao_id) VALUES (?, ?)', (nome, colecao_id))
                conn.commit()
            finally:
                conn.close()
            return redirect(url_for('list_skins'))
        else:
            return "Nome da skin e ID da coleção não podem estar vazios.", 400
    try:
        colecoes = conn.execute('SELECT * FROM colecoes').fetchall()
    finally:
        conn.close()
    return render_template('add_skin.html', colecoes=colecoes)

#Rota para editar uma skin existente, protegida por autenticação
@app.route('/skins/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def edit_skin(id):
    conn = get_db_connection()
    if request.method == 'POST':
        nome = request.form['nome']
        colecao_id = request.form['colecao_id']
        if nome and colecao_id:
            try:
                conn.execute('UPDATE skins SET nome = ?, colecao_id = ? WHERE id = ?', (nome, colecao_id, id))
                conn.commit()
            finally:
                conn.close()
            return redirect(url_for('list_skins'))
        else:
            return "Nome da skin e ID da coleção não podem estar vazios.", 400
    try:
        skin = conn.execute('SELECT * FROM skins WHERE id = ?', (id,)).fetchone()
        colecoes = conn.execute('SELECT * FROM colecoes').fetchall()
    finally:
        conn.close()
    return render_template('edit_skin.html', skin=skin, colecoes=colecoes)

#Rota para deletar uma skin, protegida por autenticação
@app.route('/skins/<int:id>/deletar', methods=['POST'])
@login_required
def delete_skin(id):
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM skins WHERE id = ?', (id,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('list_skins'))

#Rota para login de usuários
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        try:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        finally:
            conn.close()

        if user and check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username'], user['password']))
            return redirect(url_for('index'))
        else:
            flash('Login inválido.')  # Mensagem de erro se login falhar
            return redirect(url_for('login'))
    return render_template('login.html')

#Rota para logout de usuários
@app.route('/logout')
@login_required
def logout():
    logout_user()  # Desloga o usuário
    return redirect(url_for('login'))

#Rota para registro de novos usuários
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        try:
            hashed_password = generate_password_hash(password)  # Hash da senha para segurança
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
        finally:
            conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

#Criação das tabelas ao iniciar a aplicação
create_users_table()
create_other_tables()


if __name__ == '__main__':
    app.run(debug=True)  
