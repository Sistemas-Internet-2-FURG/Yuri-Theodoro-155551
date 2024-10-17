import sqlite3
from flask import Flask, jsonify, request, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

#Criação do Flask
app = Flask(__name__)
app.secret_key = 'your_secret_key'
#Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  #Página de login quando não autenticado

#Conexão com o banco de dados
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

#Criar tabelas
def create_tables():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password TEXT NOT NULL
                    );''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS colecoes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL
                    );''')
    
    conn.execute('''CREATE TABLE IF NOT EXISTS skins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL,
                        colecao_id INTEGER,
                        FOREIGN KEY (colecao_id) REFERENCES colecoes (id)
                    );''')
    
    conn.commit()
    conn.close()

#Classe User para gerenciar autenticação
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    def get_id(self):
        return str(self.id)
    
#Carregar usuário pelo ID
@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user is None:
        return None
    return User(user['id'], user['username'], user['password'])

#Rotas para usuários
#Rota para login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        login_user(User(user['id'], user['username'], user['password']))
        return jsonify({"message": "Login bem-sucedido!"}), 200
    else:
        return jsonify({"error": "Login inválido."}), 401
#Rota para logout
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout realizado com sucesso!"}), 200
#Rota para registro de usuários
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Nome de usuário e senha são obrigatórios."}), 400

    conn = get_db_connection()
    hashed_password = generate_password_hash(password)
    conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()
    return jsonify({"message": "Usuário registrado com sucesso!"}), 201

#Rotas para coleções
#Rota para listar coleções
@app.route('/colecoes', methods=['GET'])
@login_required
def list_colecoes():
    conn = get_db_connection()
    colecoes = conn.execute('SELECT * FROM colecoes').fetchall()
    conn.close()
    return jsonify([dict(colecao) for colecao in colecoes]), 200
#Rota para adicionar nova coleção
@app.route('/colecoes', methods=['POST'])
@login_required
def add_colecao():
    data = request.get_json()
    nome = data.get('nome')

    if not nome:
        return jsonify({"error": "Nome da coleção não pode estar vazio."}), 400
    
    conn = get_db_connection()
    conn.execute('INSERT INTO colecoes (nome) VALUES (?)', (nome,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Coleção adicionada com sucesso!"}), 201
#Rota para editar coleção
@app.route('/colecoes/<int:id>', methods=['PUT'])
@login_required
def edit_colecao(id):
    data = request.get_json()
    nome = data.get('nome')

    if not nome:
        return jsonify({"error": "Nome da coleção não pode estar vazio."}), 400

    conn = get_db_connection()
    conn.execute('UPDATE colecoes SET nome = ? WHERE id = ?', (nome, id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Coleção atualizada com sucesso!"}), 200
#Rota para deletar coleção
@app.route('/colecoes/<int:id>', methods=['DELETE'])
@login_required
def delete_colecao(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM colecoes WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Coleção deletada com sucesso!"}), 200

#Rotas para skins
#Rota para listar skins
@app.route('/skins', methods=['GET'])
@login_required
def list_skins():
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

    conn = get_db_connection()
    skins = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(skin) for skin in skins]), 200

#Rota para adicionar nova skin
@app.route('/skins', methods=['POST'])
@login_required
def add_skin():
    data = request.get_json()
    nome = data.get('nome')
    colecao_id = data.get('colecao_id')

    if not nome or not colecao_id:
        return jsonify({"error": "Nome da skin e ID da coleção não podem estar vazios."}), 400

    conn = get_db_connection()
    conn.execute('INSERT INTO skins (nome, colecao_id) VALUES (?, ?)', (nome, colecao_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Skin adicionada com sucesso!"}), 201

#Rota para editar skin
@app.route('/skins/<int:id>', methods=['PUT'])
@login_required
def edit_skin(id):
    data = request.get_json()
    nome = data.get('nome')
    colecao_id = data.get('colecao_id')

    if not nome or not colecao_id:
        return jsonify({"error": "Nome da skin e ID da coleção não podem estar vazios."}), 400

    conn = get_db_connection()
    conn.execute('UPDATE skins SET nome = ?, colecao_id = ? WHERE id = ?', (nome, colecao_id, id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Skin atualizada com sucesso!"}), 200
#Rota para deletar skin
@app.route('/skins/<int:id>', methods=['DELETE'])
@login_required
def delete_skin(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM skins WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Skin deletada com sucesso!"}), 200
#Cria tabelas ao iniciar a aplicação
create_tables()

#Inicia servidor 
if __name__ == '__main__':
    app.run(debug=True)
