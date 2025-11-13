from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os
import datetime

# --- Configuração de Dados Globais e Persistência ---

DATA_FILE = 'hashem_data.json'
USUARIOS_FILE = 'hashem_usuarios.json'
NOME_SISTEMA = "Hashem Personal Trainer"

clientes = {}
proximo_cliente_id = 1
usuarios = {}

exercicios_cadastrados = [
    "Supino Reto", "Agachamento Livre", "Remada Cavalinho",
    "Desenvolvimento Halteres", "Cadeira Extensora", "Rosca Direta"
]

# Mapeamento de exercício para o nome do arquivo de imagem (deve existir em static/images/)
IMAGENS_EXERCICIOS = {
    "Supino Reto": "supino_reto.jpg",
    "Agachamento Livre": "agachamento_livre.jpg",
    "Remada Cavalinho": "remada_cavalinho.jpg",
    "Desenvolvimento Halteres": "desenvolvimento_halteres.jpg",
    "Cadeira Extensora": "cadeira_extensora.jpg",
    "Rosca Direta": "rosca_direta.jpg",
}


def _carregar_dados():
    """Carrega dados de clientes do arquivo JSON."""
    global clientes, proximo_cliente_id
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                data = json.load(f)
                clientes_str_keys = data.get('clientes', {})
                clientes = {int(k): v for k, v in clientes_str_keys.items()}
                proximo_cliente_id = data.get('proximo_cliente_id', 1)
            except json.JSONDecodeError:
                pass


def _salvar_dados():
    """Salva dados de clientes no arquivo JSON."""
    with open(DATA_FILE, 'w') as f:
        data = {
            'clientes': clientes,
            'proximo_cliente_id': proximo_cliente_id
        }
        json.dump(data, f, indent=4)


def _carregar_usuarios():
    """Carrega dados de usuários do arquivo JSON."""
    global usuarios
    if os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, 'r') as f:
            try:
                usuarios = json.load(f)
            except json.JSONDecodeError:
                pass


def _salvar_usuarios():
    """Salva dados de usuários no arquivo JSON."""
    with open(USUARIOS_FILE, 'w') as f:
        json.dump(usuarios, f, indent=4)


# Função utilitária para hash de senha (simples para protótipo)
def hash_senha_simples(senha):
    """Inverte a string para simular um hash simples."""
    return senha[::-1]


# --- Funções de Lógica de Negócios (CRUD) ---

def cadastrar_usuario(email, senha, perfil):
    global usuarios
    email = email.strip().lower()
    if email in usuarios:
        return False, "E-mail já cadastrado."

    senha_hashed = hash_senha_simples(senha)

    usuarios[email] = {
        'email': email,
        'senha_hash': senha_hashed,
        'perfil': perfil,  # 'aluno' ou 'professor'
        'data_cadastro': datetime.date.today().strftime('%Y-%m-%d'),
        'status_pagamento': 'Pendente' if perfil == 'aluno' else 'N/A'
    }
    _salvar_usuarios()
    return True, "Usuário cadastrado com sucesso."


def cadastrar_cliente(nome, objetivo):
    global proximo_cliente_id
    novo_cliente = {
        "id": proximo_cliente_id,
        "nome": nome.strip().title(),
        "objetivo": objetivo,
        "treinos": {},
        "progresso": []
    }
    clientes[proximo_cliente_id] = novo_cliente
    proximo_cliente_id += 1
    _salvar_dados()
    return novo_cliente


def remover_cliente(cliente_id):
    if cliente_id in clientes:
        nome = clientes[cliente_id]['nome']
        del clientes[cliente_id]
        _salvar_dados()
        return nome, True
    return "Cliente não encontrado.", False


def registrar_progresso_data(cliente_id, peso, cintura, braco):
    cliente = clientes.get(cliente_id)
    if not cliente: return "Cliente não encontrado.", False

    novo_registro = {
        "data": datetime.date.today().strftime('%Y-%m-%d'),
        "peso": peso,
        "cintura": cintura if cintura else "-",
        "braco": braco if braco else "-",
    }
    if 'progresso' not in cliente: cliente['progresso'] = []
    cliente['progresso'].append(novo_registro)
    _salvar_dados()
    return f"Progresso registrado para {cliente['nome']}.", True


def remover_registro_progresso(cliente_id, data_registro):
    cliente = clientes.get(cliente_id)
    if cliente:
        registros = cliente.get('progresso', [])
        cliente['progresso'] = [r for r in registros if r['data'] != data_registro]
        _salvar_dados()
        return True
    return False


def remover_exercicio(cliente_id, nome_treino, index_exercicio):
    cliente = clientes.get(cliente_id)
    if cliente and nome_treino in cliente['treinos']:
        treino = cliente['treinos'][nome_treino]
        if 0 <= index_exercicio < len(treino):
            exercicio_removido = treino.pop(index_exercicio)
            if not treino:
                del cliente['treinos'][nome_treino]

            _salvar_dados()
            return exercicio_removido['nome'], True
    return "Falha ao remover exercício.", False


# --- Configuração e Context Processor do Flask ---
app = Flask(__name__)
app.secret_key = 'uma_chave_secreta_muito_segura_para_hashem'
_carregar_dados()
_carregar_usuarios()


@app.context_processor
def inject_global_data():
    """Injeta dados globais em todos os templates."""
    return dict(
        nome_sistema=NOME_SISTEMA,
        perfil=session.get('perfil'),
        imagens_exercicios=IMAGENS_EXERCICIOS
    )


# --- Controle de Acesso ---

def login_required():
    """Verifica se o usuário está logado antes de acessar qualquer página."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return None


# --- ROTAS DE AUTENTICAÇÃO E CADASTRO PESSOAL ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        senha = request.form.get('senha')

        usuario = usuarios.get(email)
        senha_hashed = hash_senha_simples(senha)

        if usuario and usuario['senha_hash'] == senha_hashed:
            # Autenticação bem-sucedida
            session['logged_in'] = True
            session['perfil'] = usuario['perfil']
            session['user_email'] = email  # Salva o e-mail do usuário logado
            flash(f"Bem-vindo(a), Perfil de {usuario['perfil'].title()}!", 'success')

            if usuario['perfil'] == 'professor':
                return redirect(url_for('index'))
            else:
                return redirect(url_for('area_aluno'))
        else:
            flash('E-mail ou senha incorretos.', 'error')

    # Redirecionamento se já logado
    if session.get('logged_in'):
        if session.get('perfil') == 'professor':
            return redirect(url_for('index'))
        else:
            return redirect(url_for('area_aluno'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        senha = request.form.get('senha')
        perfil = request.form.get('perfil')

        if not email or not senha or not perfil:
            flash('Preencha todos os campos.', 'error')
            return redirect(url_for('register'))

        sucesso, mensagem = cadastrar_usuario(email, senha, perfil)

        if sucesso:
            flash(f'✅ {mensagem}. Faça login para acessar.', 'success')
            return redirect(url_for('login'))
        else:
            flash(f'⚠️ {mensagem}', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('perfil', None)
    session.pop('user_email', None)
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('login'))


# --- ROTAS DA ÁREA DO PROFESSOR (Gerenciamento de Clientes e Pagamentos) ---

@app.route('/')
def index():
    if login_required(): return login_required()
    if session.get('perfil') != 'professor':
        return redirect(url_for('area_aluno'))

    return render_template('index.html', clientes=clientes.values())


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if login_required(): return login_required()
    if session.get('perfil') != 'professor':
        flash('Acesso negado. Apenas o Professor pode cadastrar clientes.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        objetivo = request.form.get('objetivo')

        if not nome or not objetivo:
            flash('Preencha todos os campos!', 'error')
            return redirect(url_for('cadastro'))

        cliente = cadastrar_cliente(nome, objetivo)
        flash(f"✅ Cliente {cliente['nome']} cadastrado com ID {cliente['id']}!", 'success')
        return redirect(url_for('index'))

    return render_template('cadastro.html')


@app.route('/remover_cliente/<int:cliente_id>', methods=['POST'])
def remover_cliente_route(cliente_id):
    if login_required(): return login_required()
    if session.get('perfil') != 'professor':
        flash('Acesso negado. Apenas o Professor pode remover clientes.', 'error')
        return redirect(url_for('index'))

    nome, sucesso = remover_cliente(cliente_id)
    if sucesso:
        flash(f"❌ Cliente {nome} removido permanentemente.", 'success')
    else:
        flash(f"⚠️ {nome}", 'error')
    return redirect(url_for('index'))


@app.route('/pagamentos', methods=['GET', 'POST'])
def pagamentos():
    if login_required(): return login_required()
    if session.get('perfil') != 'professor':
        flash('Acesso negado. Apenas o Professor gerencia Pagamentos.', 'error')
        return redirect(url_for('area_aluno' if session.get('perfil') == 'aluno' else 'index'))

    # Lógica de processamento de formulário de pagamento (POST)
    if request.method == 'POST':
        user_email = request.form.get('user_email')
        novo_status = request.form.get('status')

        if user_email in usuarios and usuarios[user_email]['perfil'] == 'aluno':
            usuarios[user_email]['status_pagamento'] = novo_status
            _salvar_usuarios()
            flash(f"Status de pagamento de {user_email} atualizado para '{novo_status}'.", 'success')
        else:
            flash("Usuário aluno não encontrado.", 'error')

        return redirect(url_for('pagamentos'))

    alunos_para_pagamento = [u for u in usuarios.values() if u['perfil'] == 'aluno']
    return render_template('pagamentos.html', alunos=alunos_para_pagamento)


# --- ROTAS COMPARTILHADAS (Treinos e Progresso) ---

@app.route('/progresso/<int:cliente_id>', methods=['GET', 'POST'])
def progresso(cliente_id):
    if login_required(): return login_required()
    cliente = clientes.get(cliente_id)
    if not cliente:
        flash('Cliente não encontrado.', 'error')
        return redirect(url_for('index'))  # Professor é redirecionado para index

    if request.method == 'POST':
        # Permite remoção APENAS para o professor
        if 'remover_data' in request.form:
            if session.get('perfil') != 'professor':
                flash('Acesso negado. Apenas o Professor pode remover registros.', 'error')
                return redirect(url_for('progresso', cliente_id=cliente_id))

            data_registro = request.form.get('remover_data')
            if remover_registro_progresso(cliente_id, data_registro):
                flash(f"Registro de progresso da data {data_registro} removido.", 'success')
            else:
                flash("Falha ao remover registro.", 'error')
            return redirect(url_for('progresso', cliente_id=cliente_id))

        # Lógica de Registro
        peso = request.form.get('peso')
        cintura = request.form.get('cintura')
        braco = request.form.get('braco')

        if not peso:
            flash('O campo Peso é obrigatório.', 'error')
            return redirect(url_for('progresso', cliente_id=cliente_id))

        try:
            float(peso)
        except ValueError:
            flash('Peso deve ser um valor numérico válido.', 'error')
            return redirect(url_for('progresso', cliente_id=cliente_id))

        mensagem, sucesso = registrar_progresso_data(cliente_id, peso, cintura, braco)
        if sucesso:
            flash(f'✅ {mensagem}', 'success')
        else:
            flash(f'⚠️ {mensagem}', 'error')
        return redirect(url_for('progresso', cliente_id=cliente_id))

    return render_template('progresso.html', cliente=cliente)


@app.route('/treinos/<int:cliente_id>', methods=['GET', 'POST'])
@app.route('/treinos/<int:cliente_id>/<string:nome_treino_selecionado>', methods=['GET', 'POST'])
def treinos(cliente_id, nome_treino_selecionado=None):
    if login_required(): return login_required()

    cliente = clientes.get(cliente_id)
    if not cliente:
        flash('Cliente não encontrado.', 'error')
        return redirect(url_for('index'))

    treinos_cliente = cliente.get('treinos', {})
    treino_atual = None

    if treinos_cliente:
        if nome_treino_selecionado and nome_treino_selecionado in treinos_cliente:
            treino_atual = nome_treino_selecionado
        elif treinos_cliente:
            treino_atual = list(treinos_cliente.keys())[0]

    if request.method == 'POST':
        # Permite manipulação (adição/remoção) APENAS para o professor
        if session.get('perfil') != 'professor':
            flash('Acesso negado. Apenas o Professor pode editar treinos.', 'error')
            return redirect(url_for('treinos', cliente_id=cliente_id))

        # Lógica de Remoção de Exercício
        if 'remover_exercicio_index' in request.form:
            index = int(request.form.get('remover_exercicio_index'))
            treino_alvo = request.form.get('treino_alvo')

            nome_ex, sucesso = remover_exercicio(cliente_id, treino_alvo, index)

            if sucesso:
                flash(f"❌ Exercício '{nome_ex}' removido do Treino '{treino_alvo}'.", 'success')
                if treino_alvo not in cliente['treinos']:
                    return redirect(url_for('treinos', cliente_id=cliente_id))
            else:
                flash(f"⚠️ {nome_ex}", 'error')
            return redirect(url_for('treinos', cliente_id=cliente_id, nome_treino_selecionado=treino_alvo))

        # Lógica de Adição de Exercício
        nome_treino = request.form.get('nome_treino').strip().upper()
        nome_exercicio = request.form.get('nome_exercicio')
        series = request.form.get('series').strip()
        reps = request.form.get('reps').strip()
        carga = request.form.get('carga').strip()

        if not nome_treino or not nome_exercicio:
            flash('Preencha o Nome do Treino e selecione um Exercício.', 'error')
            return redirect(url_for('treinos', cliente_id=cliente_id))

        if nome_treino not in cliente['treinos']:
            cliente['treinos'][nome_treino] = []

        exercicio_data = {
            "nome": nome_exercicio, "series": series, "reps": reps, "carga": carga
        }
        cliente['treinos'][nome_treino].append(exercicio_data)
        _salvar_dados()

        flash(f"✅ Exercício '{nome_exercicio}' adicionado ao Treino '{nome_treino}'!", 'success')
        return redirect(url_for('treinos', cliente_id=cliente_id, nome_treino_selecionado=nome_treino))

    return render_template('treinos.html',
                           cliente=cliente,
                           exercicios_cadastrados=exercicios_cadastrados,
                           treino_atual=treino_atual,
                           treinos_cliente=treinos_cliente)


# --- ROTA DA ÁREA DO ALUNO ---

@app.route('/area_aluno')
def area_aluno():
    if login_required(): return login_required()
    if session.get('perfil') != 'aluno':
        flash('Acesso negado. Esta é a área exclusiva do Aluno.', 'error')
        return redirect(url_for('index'))

    user_email = session.get('user_email')
    user_data = usuarios.get(user_email)

    # Simulação: tenta associar o primeiro cliente cadastrado ao aluno.
    # Em um sistema real, essa associação seria feita no banco de dados.
    cliente_associado = None
    if clientes:
        # Pega o primeiro cliente (apenas para ter dados de treino/progresso para mostrar)
        cliente_associado = list(clientes.values())[0]

    return render_template('area_aluno.html', user_data=user_data, cliente=cliente_associado)


if __name__ == '__main__':
    app.run(debug=True)