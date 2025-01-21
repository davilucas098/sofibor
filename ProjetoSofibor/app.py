from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required

# Configuração inicial do Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1818@127.0.0.1:5432/sistema'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'sua_chave_secreta'

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Modelos do Banco de Dados
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # administrador, cabral, mauricio

class Pedido(db.Model):
    __tablename__ = 'pedidos'
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='pendente')
    responsavel = db.Column(db.String(100), nullable=True)  # Cabral ou Maurício
    origem = db.Column(db.String(50), nullable=False)  # estamparia ou compra
    tratamento = db.Column(db.String(50), nullable=True)  # zinco, fosfato, solda, etc.
    galpao_destino = db.Column(db.String(50), nullable=True)  # Samy, Cachoeira

# Rotas de Autenticação
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('senha'):
        return jsonify({'error': 'Email e senha são obrigatórios'}), 400

    email = data['email']
    senha = data['senha']

    usuario = Usuario.query.filter_by(email=email, senha=senha).first()
    if not usuario:
        return jsonify({'error': 'Credenciais inválidas'}), 401

    token = create_access_token(identity={'id': usuario.id, 'nome': usuario.nome, 'tipo': usuario.tipo})
    return jsonify({'token': token})

# Rotas para Administradores
@app.route('/usuarios', methods=['GET'])
@jwt_required()
def listar_usuarios():
    usuarios = Usuario.query.all()
    return jsonify([{'id': u.id, 'nome': u.nome, 'email': u.email, 'tipo': u.tipo} for u in usuarios])

@app.route('/usuarios', methods=['POST'])
@jwt_required()
def criar_usuario():
    data = request.get_json()
    if not data or not all(key in data for key in ('nome', 'email', 'senha', 'tipo')):
        return jsonify({'error': 'Dados incompletos para criar usuário'}), 400

    novo_usuario = Usuario(
        nome=data['nome'],
        email=data['email'],
        senha=data['senha'],
        tipo=data['tipo']
    )
    db.session.add(novo_usuario)
    db.session.commit()
    return jsonify({'message': 'Usuário criado com sucesso'}), 201

# Rotas para Cabral (Fábrica)
@app.route('/pedidos', methods=['POST'])
@jwt_required()
def criar_pedido():
    data = request.get_json()
    if not data or not all(key in data for key in ('item', 'quantidade')):
        return jsonify({'error': 'Dados incompletos para criar pedido'}), 400

    novo_pedido = Pedido(
        item=data['item'],
        quantidade=data['quantidade'],
        origem='compra',
        responsavel='Cabral'
    )
    db.session.add(novo_pedido)
    db.session.commit()
    return jsonify({'message': 'Pedido criado com sucesso'}), 201

@app.route('/pedidos', methods=['GET'])
@jwt_required()
def listar_pedidos():
    pedidos = Pedido.query.all()
    return jsonify([{
        'id': p.id,
        'item': p.item,
        'quantidade': p.quantidade,
        'status': p.status,
        'responsavel': p.responsavel,
        'origem': p.origem,
        'tratamento': p.tratamento,
        'galpao_destino': p.galpao_destino
    } for p in pedidos])

# Rotas para Maurício (Recebimento, Separação e Distribuição)
@app.route('/recebimentos', methods=['POST'])
@jwt_required()
def registrar_recebimento():
    data = request.get_json()
    if not data or not all(key in data for key in ('item', 'quantidade', 'origem')):
        return jsonify({'error': 'Dados incompletos para registrar recebimento'}), 400

    novo_pedido = Pedido(
        item=data['item'],
        quantidade=data['quantidade'],
        origem=data['origem'],
        responsavel='Maurício',
        status='recebido'
    )
    db.session.add(novo_pedido)
    db.session.commit()
    return jsonify({'message': 'Recebimento registrado com sucesso'}), 201

@app.route('/tratamentos/<int:pedido_id>', methods=['PUT'])
@jwt_required()
def enviar_para_tratamento(pedido_id):
    data = request.get_json()
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return jsonify({'error': 'Pedido não encontrado'}), 404

    pedido.tratamento = data.get('tratamento')
    if not pedido.tratamento:
        return jsonify({'error': 'Tratamento não especificado'}), 400

    pedido.status = 'em tratamento'
    db.session.commit()
    return jsonify({'message': f'Pedido enviado para {pedido.tratamento}'}), 200

@app.route('/tratamentos/<int:pedido_id>/verificar', methods=['PUT'])
@jwt_required()
def verificar_retorno_tratamento(pedido_id):
    data = request.get_json()
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return jsonify({'error': 'Pedido não encontrado'}), 404

    if not data or 'quantidade' not in data or data['quantidade'] != pedido.quantidade:
        return jsonify({'error': 'Quantidade recebida está incorreta ou não foi informada'}), 400

    pedido.status = 'tratamento concluído'
    db.session.commit()
    return jsonify({'message': 'Retorno do tratamento verificado com sucesso'}), 200

@app.route('/envio/<int:pedido_id>', methods=['PUT'])
@jwt_required()
def enviar_para_galpao(pedido_id):
    data = request.get_json()
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return jsonify({'error': 'Pedido não encontrado'}), 404

    pedido.galpao_destino = data.get('galpao_destino')
    if not pedido.galpao_destino:
        return jsonify({'error': 'Galpão de destino não especificado'}), 400

    pedido.status = 'enviado ao galpão'
    db.session.commit()
    return jsonify({'message': f'Pedido enviado para o galpão {pedido.galpao_destino}'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)