from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import os
import datetime
from apscheduler.schedulers.background import BackgroundScheduler  # NOVO
import atexit  # NOVO

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
    """Salva dados de usuários no arquivo JSON e garante a existência do Admin padrão."""
    global usuarios

    # Garante que o usuário Admin padrão existe na primeira execução
    if '99999999999' not in usuarios:
        usuarios['99999999999'] = {
            'nome_completo': 'Administrador Geral',
            'celular': '99999999999',
            'senha_hash': hash_senha_simples('admin'),
            'perfil': 'admin',
            'data_cadastro': datetime.date.today().strftime('%Y-%m-%d'),
            'status_pagamento': 'N/A'
        }

    with open(USUARIOS_FILE, 'w') as f:
        json.dump(usuarios, f, indent=4)


def hash_senha_simples(senha):
    """Inverte a string para simular um hash simples."""
    return senha[::-1]


# --- Funções de Lógica de Negócios (CRUD) ---

def cadastrar_usuario(nome_completo, celular, senha, perfil):
    global usuarios
    celular = celular.strip()
    if celular in usuarios:
        return False, "Número de celular já cadastrado."

    senha_hashed = hash_senha_simples(senha)

    usuarios[celular] = {
        'nome_completo': nome_completo.strip().title(),
        'celular': celular,
        'senha_hash': senha_hashed,
        'perfil': perfil,
        'data_cadastro': datetime.date.today().strftime('%Y-%m-%d'),
        'status_pagamento': 'Pendente' if perfil == 'aluno' else 'N/A'
    }
    _salvar_usuarios()
    return True, "Usuário cadastrado com sucesso."


def remover_usuario(celular):
    global usuarios
    if celular in usuarios:
        if usuarios[celular]['perfil'] == 'admin':
            return False, "Não é permitido remover o administrador principal."
        del usuarios[celular]
        _salvar_usuarios()
        return True, "Usuário removido com sucesso."
    return False, "Usuário não encontrado."


def cadastrar_cliente(nome, objetivo, professor_celular=None, aluno_celular=None):
    global proximo_cliente_id
    novo_cliente = {
        "id": proximo_cliente_id,
        "nome": nome.strip().title(),
        "objetivo": objetivo,
        "treinos": {},
        "progresso": [],
        "professor_celular": professor_celular,  # Vinculação ao Professor
        "aluno_celular": aluno_celular  # Vinculação ao Aluno (para acesso)
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


# --- Configuração e Filtros do Flask ---
app = Flask(__name__)
app.secret_key = 'uma_chave_secreta_muito_segura_para_hashem'
_carregar_dados()
_carregar_usuarios()
_salvar_usuarios()

# Adiciona um cliente de teste para o Admin/Professor padrão se não houver clientes
if not clientes:
    cadastrar_cliente(
        nome="Cliente Padrão Teste",
        objetivo="Hipertrofia",
        professor_celular='99999999999',
        aluno_celular=None
    )


# Função para formatar o celular (usada no jinja2)
def formatar_celular(celular):
    """Formata o número de celular (11 dígitos, sem DDI) para o padrão (00) 90000-0000."""
    celular = str(celular).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if len(celular) == 11:
        return f'({celular[0:2]}) {celular[2:7]}-{celular[7:]}'
    elif len(celular) == 10:
        return f'({celular[0:2]}) {celular[2:6]}-{celular[6:]}'
    return celular


app.jinja_env.filters['celular'] = formatar_celular


# Injeta dados globais em todos os templates
@app.context_processor
def inject_global_data():
    return dict(
        nome_sistema=NOME_SISTEMA,
        perfil=session.get('perfil'),
        nome_usuario=session.get('user_name', 'Visitante'),
        imagens_exercicios=IMAGENS_EXERCICIOS,
        usuarios=usuarios
    )


# --- Controle de Acesso e ROTAS DE AUTENTICAÇÃO ---

def login_required(perfil_minimo=None):
    """Verifica se o usuário está logado e se atende ao perfil mínimo."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    perfil_atual = session.get('perfil')

    if perfil_minimo:
        ordem_perfis = {'aluno': 1, 'professor': 2, 'admin': 3}
        if ordem_perfis.get(perfil_atual, 0) < ordem_perfis.get(perfil_minimo, 0):
            flash(f'Acesso negado. Apenas usuários com perfil "{perfil_minimo.title()}" ou superior podem acessar.',
                  'error')

            if perfil_atual == 'admin':
                return redirect(url_for('admin_area'))
            elif perfil_atual == 'professor':
                return redirect(url_for('index'))
            else:
                return redirect(url_for('area_aluno'))

    return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        celular = request.form.get('celular').strip()
        senha = request.form.get('senha')

        usuario = usuarios.get(celular)
        senha_hashed = hash_senha_simples(senha)

        if usuario and usuario['senha_hash'] == senha_hashed:
            session['logged_in'] = True
            session['perfil'] = usuario['perfil']
            session['user_celular'] = celular
            session['user_name'] = usuario['nome_completo']

            flash(f"Bem-vindo(a), {usuario['nome_completo']}! Perfil: {usuario['perfil'].title()}.", 'success')

            if usuario['perfil'] == 'admin':
                return redirect(url_for('admin_area'))
            elif usuario['perfil'] == 'professor':
                return redirect(url_for('index'))
            else:  # aluno
                return redirect(url_for('area_aluno'))
        else:
            flash('Celular ou senha incorretos.', 'error')

    if session.get('logged_in'):
        if session.get('perfil') == 'admin':
            return redirect(url_for('admin_area'))
        elif session.get('perfil') == 'professor':
            return redirect(url_for('index'))
        else:
            return redirect(url_for('area_aluno'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome_completo = request.form.get('nome_completo')
        celular = request.form.get('celular').strip()
        senha = request.form.get('senha')
        perfil = 'aluno'

        if not nome_completo or not celular or not senha:
            flash('Preencha todos os campos.', 'error')
            return redirect(url_for('register'))

        if not celular.isdigit() or len(celular) < 10 or len(celular) > 11:
            flash('Celular inválido. Use apenas números (DDD + Número).', 'error')
            return redirect(url_for('register'))

        sucesso, mensagem = cadastrar_usuario(nome_completo, celular, senha, perfil)

        if sucesso:
            flash(f'✅ {mensagem}. Faça login para acessar. Avise seu professor para te vincular a um plano!', 'success')
            return redirect(url_for('login'))
        else:
            flash(f'⚠️ {mensagem}', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('perfil', None)
    session.pop('user_celular', None)
    session.pop('user_name', None)
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('login'))


# No arquivo app.py, localize e substitua a rota /admin:

@app.route('/admin', methods=['GET', 'POST'])
def admin_area():
    if login_required('admin'): return login_required('admin')

    if request.method == 'POST':
        if 'add_user' in request.form:
            # Lógica de adicionar usuário...
            nome = request.form.get('nome')
            celular = request.form.get('celular').strip()
            senha = request.form.get('senha')
            perfil = request.form.get('perfil')

            if perfil not in ['professor', 'admin']:
                flash('Perfil inválido para cadastro administrativo.', 'error')
            elif not celular.isdigit() or len(celular) < 10 or len(celular) > 11:
                flash('Celular inválido. Use apenas números (DDD + Número).', 'error')
            else:
                sucesso, mensagem = cadastrar_usuario(nome, celular, senha, perfil)
                flash(f'{"✅" if sucesso else "⚠️"} {mensagem}', 'success' if sucesso else 'error')
            return redirect(url_for('admin_area'))

        elif 'remove_user' in request.form:
            # Lógica de remover usuário...
            celular_alvo = request.form.get('remove_user')
            sucesso, mensagem = remover_usuario(celular_alvo)
            flash(f'{"✅" if sucesso else "⚠️"} {mensagem}', 'success' if sucesso else 'error')
            return redirect(url_for('admin_area'))

        elif 'update_payment' in request.form:
            # Lógica de atualização de pagamento com Motivo e Tipo (funciona para Aluno e Professor)
            celular_alvo = request.form.get('celular_alvo')
            novo_status = request.form.get('novo_status')
            tipo_pagamento = request.form.get('tipo_pagamento')
            motivo_pagamento = request.form.get('motivo_pagamento')

            if celular_alvo in usuarios:
                # O Admin não pode alterar o próprio status, nem o status de outro Admin
                if usuarios[celular_alvo]['perfil'] == 'admin':
                    flash("⚠️ Você não pode alterar o status de pagamento de um Administrador.", 'error')
                    return redirect(url_for('admin_area'))

                usuarios[celular_alvo]['status_pagamento'] = novo_status
                # Estas chaves são mais relevantes para alunos, mas as salvaremos
                # para o professor também caso sejam preenchidas.
                usuarios[celular_alvo]['tipo_pagamento'] = tipo_pagamento
                usuarios[celular_alvo]['motivo_pagamento'] = motivo_pagamento
                _salvar_usuarios()
                flash(
                    f"✅ Status de pagamento de {usuarios[celular_alvo]['nome_completo']} ({usuarios[celular_alvo]['perfil'].title()}) atualizado para '{novo_status}'.",
                    'success')
            else:
                flash("⚠️ Usuário não encontrado.", 'error')
            return redirect(url_for('admin_area'))

    lista_usuarios = sorted(usuarios.values(), key=lambda u: u['perfil'], reverse=True)
    return render_template('admin.html', lista_usuarios=lista_usuarios)

# --- ROTAS DA ÁREA DO PROFESSOR (Gerenciamento de Clientes) ---

@app.route('/')
def index():
    if login_required('professor'): return login_required('professor')

    professor_celular = session.get('user_celular')

    # Filtra os clientes: só mostra os clientes vinculados a este professor
    clientes_do_professor = {
        cid: c for cid, c in clientes.items()
        if c.get('professor_celular') == professor_celular
    }

    # Lista de alunos registrados que AINDA NÃO SÃO clientes
    alunos_disponiveis = [
        u for u in usuarios.values()
        if u['perfil'] == 'aluno' and not any(c.get('aluno_celular') == u['celular'] for c in clientes.values())
    ]

    return render_template('index.html',
                           clientes=clientes_do_professor.values(),
                           alunos_disponiveis=alunos_disponiveis)


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if login_required('professor'): return login_required('professor')

    professor_celular = session.get('user_celular')
    alunos_disponiveis = [
        u for u in usuarios.values()
        if u['perfil'] == 'aluno' and not any(c.get('aluno_celular') == u['celular'] for c in clientes.values())
    ]

    if request.method == 'POST':
        nome_cliente_manual = request.form.get('nome')
        objetivo = request.form.get('objetivo')
        aluno_celular = request.form.get('aluno_celular')

        if not objetivo:
            flash('Preencha o campo Objetivo.', 'error')
            return redirect(url_for('cadastro'))

        aluno_celular_final = aluno_celular if aluno_celular else None

        # Lógica de Assunção de Nome:
        if aluno_celular_final and aluno_celular_final in usuarios:
            # Se um aluno foi selecionado, assume o nome completo dele como nome do Cliente
            nome_final = usuarios[aluno_celular_final]['nome_completo']
        elif nome_cliente_manual:
            # Se nenhum aluno foi selecionado, usa o nome digitado manualmente
            nome_final = nome_cliente_manual
        else:
            flash('O nome do cliente é obrigatório (se não estiver vinculando um aluno).', 'error')
            return redirect(url_for('cadastro'))

        cliente = cadastrar_cliente(
            nome_final,
            objetivo,
            professor_celular=professor_celular,
            aluno_celular=aluno_celular_final
        )

        flash(f"✅ Cliente {cliente['nome']} cadastrado e vinculado a você. ID {cliente['id']}!", 'success')
        return redirect(url_for('index'))

    return render_template('cadastro.html', alunos_disponiveis=alunos_disponiveis)


@app.route('/remover_cliente/<int:cliente_id>', methods=['POST'])
def remover_cliente_route(cliente_id):
    if login_required('professor'): return login_required('professor')
    nome, sucesso = remover_cliente(cliente_id)
    if sucesso:
        flash(f"❌ Cliente {nome} removido permanentemente.", 'success')
    else:
        flash(f"⚠️ {nome}", 'error')
    return redirect(url_for('index'))


@app.route('/pagamentos', methods=['GET', 'POST'])
def pagamentos():
    if login_required('professor'): return login_required('professor')

    if request.method == 'POST':
        user_celular = request.form.get('user_celular')
        novo_status = request.form.get('status')

        if user_celular in usuarios:
            usuarios[user_celular]['status_pagamento'] = novo_status
            _salvar_usuarios()
            flash(
                f"✅ Status de pagamento de {usuarios[user_celular]['nome_completo']} atualizado para '{novo_status}'.",
                'success')
        else:
            flash("⚠️ Usuário aluno não encontrado.", 'error')

        return redirect(url_for('pagamentos'))

    alunos_para_pagamento = [u for u in usuarios.values() if u['perfil'] == 'aluno']
    return render_template('pagamentos.html', alunos=alunos_para_pagamento)


# --- ROTAS COMPARTILHADAS (Progresso e Treinos) ---

@app.route('/progresso/<int:cliente_id>', methods=['GET', 'POST'])
def progresso(cliente_id):
    if login_required(): return login_required()
    cliente = clientes.get(cliente_id)
    if not cliente:
        flash('Cliente não encontrado.', 'error')
        return redirect(url_for('index' if session.get('perfil') != 'aluno' else 'area_aluno'))

    # Verifica permissão de acesso (Professor ou Aluno vinculado)
    is_professor = session.get('perfil') in ['professor', 'admin']
    is_aluno = session.get('perfil') == 'aluno' and cliente.get('aluno_celular') == session.get('user_celular')

    if not is_professor and not is_aluno:
        flash('Acesso negado. Cliente não vinculado ao seu perfil.', 'error')
        return redirect(url_for('index' if is_professor else 'area_aluno'))

    if request.method == 'POST':
        # Permissões de Edição
        if not is_professor:
            flash('Acesso negado. Apenas o Professor/Admin pode editar progresso.', 'error')
            return redirect(url_for('progresso', cliente_id=cliente_id))

        if 'remover_data' in request.form:
            data_registro = request.form.get('remover_data')
            if remover_registro_progresso(cliente_id, data_registro):
                flash(f"Registro de progresso da data {data_registro} removido.", 'success')
            else:
                flash("Falha ao remover registro.", 'error')
            return redirect(url_for('progresso', cliente_id=cliente_id))

        # Registro de novo progresso
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
        return redirect(url_for('index' if session.get('perfil') != 'aluno' else 'area_aluno'))

    # Verifica permissão de acesso (Professor ou Aluno vinculado)
    is_professor = session.get('perfil') in ['professor', 'admin']
    is_aluno = session.get('perfil') == 'aluno' and cliente.get('aluno_celular') == session.get('user_celular')

    if not is_professor and not is_aluno:
        flash('Acesso negado. Cliente não vinculado ao seu perfil.', 'error')
        return redirect(url_for('index' if is_professor else 'area_aluno'))

    treinos_cliente = cliente.get('treinos', {})
    treino_atual = None

    if treinos_cliente:
        if nome_treino_selecionado and nome_treino_selecionado in treinos_cliente:
            treino_atual = nome_treino_selecionado
        elif treinos_cliente:
            treino_atual = list(treinos_cliente.keys())[0]

    if request.method == 'POST':
        # Permissões de Edição
        if not is_professor:
            flash('Acesso negado. Apenas o Professor/Admin pode editar treinos.', 'error')
            return redirect(url_for('treinos', cliente_id=cliente_id))

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
    if login_required('aluno'): return login_required('aluno')

    user_celular = session.get('user_celular')
    user_data = usuarios.get(user_celular)

    # Busca o cliente que está vinculado ao celular deste aluno
    cliente_associado = next(
        (c for c in clientes.values() if c.get('aluno_celular') == user_celular),
        None
    )

    return render_template('area_aluno.html', user_data=user_data, cliente=cliente_associado)


# --- FUNÇÃO E INICIALIZAÇÃO DO AGENDADOR (NOVO) ---

def resetar_status_pagamento():
    """Reseta o status de pagamento de todos os alunos para 'Pendente'."""
    global usuarios

    print("\n--- EXECUTANDO TAREFA AGENDADA: Reset de Pagamentos ---")

    contador = 0
    for celular, usuario in usuarios.items():
        if usuario['perfil'] == 'aluno' and usuario['status_pagamento'] != 'Pendente':
            usuario['status_pagamento'] = 'Pendente'
            contador += 1

    if contador > 0:
        _salvar_usuarios()
        print(f"--- {contador} status de alunos resetados para 'Pendente' e salvos. ---")
    else:
        print("--- Nenhum status de aluno precisava ser alterado. ---")


def iniciar_agendador():
    """Configura e inicia o agendador de tarefas."""
    scheduler = BackgroundScheduler()

    # Agendamento: Todo dia 1º de cada mês, à 00:01 (minuto 1, hora 0).
    scheduler.add_job(
        func=resetar_status_pagamento,
        trigger='cron',
        day='1',
        hour='0',
        minute='1'
    )

    scheduler.start()
    print("\n✅ Agendador de Pagamentos iniciado. Próximo reset: Todo dia 1º do mês à 00:01.")

    # Garante que o agendador pare quando o processo Flask sair
    atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':
    # Inicializa o agendador *antes* de rodar o app
    iniciar_agendador()
    # use_reloader=False é NECESSÁRIO para que o agendador não duplique a tarefa.
    app.run(debug=True, use_reloader=False)