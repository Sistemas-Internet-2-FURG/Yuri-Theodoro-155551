import os
import sqlite3
from flask import Flask, jsonify, request, abort, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

#Criação do Flask
app = Flask(__name__)
import secrets

app.secret_key = secrets.token_hex(16)

#Configuração do JWT
jwt = JWTManager(app)

app.config['DATABASE'] = os.path.join(app.instance_path, 'database.db')
os.makedirs(app.instance_path, exist_ok=True)

#Conexão com o banco de dados
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

#Criação das tabelas
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

#Rota index
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    print("Credenciais recebidas - Username:", username, "Password:", password)
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password'], password):
        #Gerando token 
        token = create_access_token(identity=username)
        return jsonify(token=token), 200
    else:
        
        print("Falha na autenticação: Credenciais inválidas")
        return jsonify(error="Usuário ou senha incorretos"), 401

#Rota registro
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Nome de usuário e senha são obrigatórios."}), 400

    conn = get_db_connection()
    
    #Verifica se o usuário já existe
    existing_user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if existing_user:
        conn.close()
        return jsonify({"error": "Nome de usuário já está em uso."}), 409

    hashed_password = generate_password_hash(password)
    conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Usuário registrado com sucesso!"}), 201

#Rota coleções
@app.route('/colecoes', methods=['GET'])
@jwt_required()
def list_colecoes():
    conn = get_db_connection()
    colecoes = conn.execute('SELECT * FROM colecoes').fetchall()
    conn.close()
    return jsonify([dict(colecao) for colecao in colecoes]), 200

@app.route('/colecoes', methods=['POST'])
@jwt_required()
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

@app.route('/colecoes/<int:id>', methods=['PUT'])
@jwt_required()
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

@app.route('/colecoes/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_colecao(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM colecoes WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Coleção deletada com sucesso!"}), 200

#Rota skins
@app.route('/skins', methods=['GET'])
@jwt_required()
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

@app.route('/skins', methods=['POST'])
@jwt_required()
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

@app.route('/skins/<int:id>', methods=['PUT'])
@jwt_required()
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

@app.route('/skins/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_skin(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM skins WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Skin deletada com sucesso!"}), 200

#Cria tabelas 
create_tables()

#Inicia servidor
if __name__ == '__main__':
    app.run(debug=True) 