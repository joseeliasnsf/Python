import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import json
import os

# --- 1. Lógica de Dados e Persistência ---
DATA_FILE = 'personal_trainer_data.json'
clientes = {}  # {id: {nome, objetivo, treinos: {nome_treino: [exercicios]}}}
proximo_cliente_id = 1
exercicios_cadastrados = ["Supino Reto", "Agachamento Livre", "Remada Cavalinho", "Desenvolvimento Halteres",
                          "Cadeira Extensora", "Rosca Direta"]


def _carregar_dados():
    """Carrega dados do arquivo JSON, se existir."""
    global clientes, proximo_cliente_id
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            clientes = data.get('clientes', {})
            # Converte as chaves de volta para inteiros (JSON salva chaves como string)
            clientes = {int(k): v for k, v in clientes.items()}
            proximo_cliente_id = data.get('proximo_cliente_id', 1)


def _salvar_dados():
    """Salva dados no arquivo JSON."""
    with open(DATA_FILE, 'w') as f:
        data = {
            'clientes': clientes,
            'proximo_cliente_id': proximo_cliente_id
        }
        json.dump(data, f, indent=4)


def cadastrar_cliente(nome, objetivo):
    """Lógica de cadastro de cliente."""
    global proximo_cliente_id
    novo_cliente = {
        "id": proximo_cliente_id,
        "nome": nome.strip().title(),
        "objetivo": objetivo,
        "treinos": {}  # Treinos serão adicionados aqui
    }
    clientes[proximo_cliente_id] = novo_cliente
    proximo_cliente_id += 1
    _salvar_dados()
    return novo_cliente


def adicionar_exercicio_a_treino(cliente_id, nome_treino, nome_exercicio, series, reps, carga):
    """Adiciona um exercício a um treino específico do cliente."""
    cliente = clientes.get(cliente_id)
    if not cliente:
        return "Cliente não encontrado.", False

    if nome_treino not in cliente['treinos']:
        cliente['treinos'][nome_treino] = []

    exercicio_data = {
        "nome": nome_exercicio,
        "series": series,
        "reps": reps,
        "carga": carga
    }
    cliente['treinos'][nome_treino].append(exercicio_data)
    _salvar_dados()
    return f"Exercício '{nome_exercicio}' adicionado ao Treino '{nome_treino}' de {cliente['nome']}.", True


# --- 2. Interface Gráfica (Tkinter) ---

class SistemaPersonalTrainer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema Personal Trainer - Hashem")
        self.geometry("800x600")

        # Carrega dados ao iniciar
        _carregar_dados()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        self._criar_aba_clientes()
        self._criar_aba_treinos()

        # Chama a função de salvamento ao fechar a janela
        self.protocol("WM_DELETE_WINDOW", self._on_fechar)

    def _on_fechar(self):
        """Salva os dados antes de fechar a aplicação."""
        _salvar_dados()
        self.destroy()

    # --- ABA 1: CLIENTES ---

    def _criar_aba_clientes(self):
        tab_clientes = ttk.Frame(self.notebook)
        self.notebook.add(tab_clientes, text='👥 Clientes')

        # Lista de Clientes
        self.clientes_tree = ttk.Treeview(tab_clientes, columns=("ID", "Nome", "Objetivo"), show='headings')
        self.clientes_tree.heading("ID", text="ID", anchor="w")
        self.clientes_tree.heading("Nome", text="Nome")
        self.clientes_tree.heading("Objetivo", text="Objetivo")

        self.clientes_tree.column("ID", width=50, anchor="w")
        self.clientes_tree.column("Nome", width=200, anchor="w")
        self.clientes_tree.column("Objetivo", width=200, anchor="w")

        self.clientes_tree.bind('<<TreeviewSelect>>', self._selecionar_cliente)
        self.clientes_tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Frame de Cadastro
        cadastro_frame = ttk.LabelFrame(tab_clientes, text="Cadastrar Novo Cliente", padding="10")
        cadastro_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(cadastro_frame, text="Nome:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.nome_var = tk.StringVar()
        tk.Entry(cadastro_frame, textvariable=self.nome_var, width=30).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(cadastro_frame, text="Objetivo:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.objetivo_var = tk.StringVar()
        tk.Entry(cadastro_frame, textvariable=self.objetivo_var, width=30).grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(cadastro_frame, text="➕ Cadastrar", command=self._handle_cadastro_cliente).grid(row=2, column=0,
                                                                                                   columnspan=2,
                                                                                                   pady=10)

        self.atualizar_lista_clientes()

    def _handle_cadastro_cliente(self):
        """Trata o clique no botão Cadastrar."""
        nome = self.nome_var.get()
        objetivo = self.objetivo_var.get()

        if not nome or not objetivo:
            messagebox.showwarning("Aviso", "Preencha Nome e Objetivo.")
            return

        novo_cliente = cadastrar_cliente(nome, objetivo)
        messagebox.showinfo("Sucesso", f"Cliente {novo_cliente['nome']} cadastrado!\nID: {novo_cliente['id']}")

        self.nome_var.set("")
        self.objetivo_var.set("")
        self.atualizar_lista_clientes()

    def atualizar_lista_clientes(self):
        """Limpa e preenche a Treeview com os clientes atuais."""
        for item in self.clientes_tree.get_children():
            self.clientes_tree.delete(item)

        for cliente_id, data in clientes.items():
            self.clientes_tree.insert('', tk.END, iid=cliente_id,
                                      values=(data['id'], data['nome'], data['objetivo']))

    # --- ABA 2: TREINOS ---

    def _criar_aba_treinos(self):
        self.tab_treinos = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_treinos, text='📝 Treinos')

        tk.Label(self.tab_treinos, text="Selecione um Cliente para Montar o Treino", font=("Arial", 12)).pack(pady=10)

        # Detalhes do Cliente Selecionado
        self.cliente_selecionado_label = tk.StringVar(value="Nenhum cliente selecionado.")
        tk.Label(self.tab_treinos, textvariable=self.cliente_selecionado_label, font=("Arial", 10, "bold")).pack(pady=5)

        # Seção de Montagem de Treino
        treino_frame = ttk.LabelFrame(self.tab_treinos, text="Montar Treino", padding="10")
        treino_frame.pack(fill="x", padx=10, pady=10)

        # Nome do Treino (A, B, C...)
        tk.Label(treino_frame, text="Nome do Treino (Ex: A, B, Perna):").grid(row=0, column=0, padx=5, pady=5,
                                                                              sticky="w")
        self.nome_treino_var = tk.StringVar()
        tk.Entry(treino_frame, textvariable=self.nome_treino_var, width=15).grid(row=0, column=1, padx=5, pady=5)

        # Exercício
        tk.Label(treino_frame, text="Exercício:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.exercicio_var = tk.StringVar()
        ttk.Combobox(treino_frame, textvariable=self.exercicio_var, values=exercicios_cadastrados, state='readonly',
                     width=20).grid(row=1, column=1, padx=5, pady=5)

        # Parâmetros do Exercício
        tk.Label(treino_frame, text="Séries:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.series_var = tk.StringVar(value="3")
        tk.Entry(treino_frame, textvariable=self.series_var, width=5).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        tk.Label(treino_frame, text="Repetições:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        self.reps_var = tk.StringVar(value="10")
        tk.Entry(treino_frame, textvariable=self.reps_var, width=5).grid(row=2, column=3, padx=5, pady=5, sticky="w")

        tk.Label(treino_frame, text="Carga (Kg):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.carga_var = tk.StringVar(value="-")
        tk.Entry(treino_frame, textvariable=self.carga_var, width=5).grid(row=3, column=1, padx=5, pady=5, sticky="w")

        ttk.Button(treino_frame, text="Adicionar Exercício", command=self._handle_adicionar_exercicio).grid(row=4,
                                                                                                            column=0,
                                                                                                            columnspan=4,
                                                                                                            pady=10)

        # Visualização do Treino (Onde os exercícios aparecem)
        self.treino_view = ttk.Treeview(self.tab_treinos, columns=("Nome", "Séries", "Reps", "Carga"), show='headings')
        self.treino_view.heading("Nome", text="Nome do Exercício")
        self.treino_view.heading("Séries", text="Séries")
        self.treino_view.heading("Reps", text="Reps")
        self.treino_view.heading("Carga", text="Carga")
        self.treino_view.pack(fill="both", expand=True, padx=10, pady=10)

        self.cliente_selecionado_id = None

    def _selecionar_cliente(self, event):
        """Chama quando um cliente é selecionado na aba Clientes."""
        selected_item = self.clientes_tree.focus()
        if not selected_item:
            self.cliente_selecionado_id = None
            return

        # O iid é o ID do cliente
        cliente_id = int(selected_item)
        self.cliente_selecionado_id = cliente_id

        cliente_data = clientes[cliente_id]
        self.cliente_selecionado_label.set(f"Treino para: {cliente_data['nome']} (ID: {cliente_id})")

        # Muda para a aba de Treinos
        self.notebook.select(self.tab_treinos)

        # Limpa e exibe o último treino (ou nenhum)
        self.limpar_treino_view()
        self.exibir_treinos_cliente(cliente_id)

    def exibir_treinos_cliente(self, cliente_id):
        """Exibe o treino mais recente do cliente na Treeview."""
        self.limpar_treino_view()
        cliente = clientes[cliente_id]

        if not cliente['treinos']:
            self.treino_view.insert('', tk.END, values=("Nenhum treino cadastrado.", "", "", ""))
            return

        # Simplesmente exibe o primeiro treino encontrado para demonstração
        # Em um sistema real, você teria um seletor de treinos (A, B, C...)
        nome_primeiro_treino = next(iter(cliente['treinos']))

        for exercicio in cliente['treinos'][nome_primeiro_treino]:
            self.treino_view.insert('', tk.END, values=(exercicio['nome'], exercicio['series'], exercicio['reps'],
                                                        exercicio['carga']))

    def limpar_treino_view(self):
        for item in self.treino_view.get_children():
            self.treino_view.delete(item)

    def _handle_adicionar_exercicio(self):
        """Trata a adição de um exercício ao treino do cliente selecionado."""
        if self.cliente_selecionado_id is None:
            messagebox.showwarning("Aviso", "Selecione um cliente na aba 'Clientes' primeiro.")
            return

        cliente_id = self.cliente_selecionado_id
        nome_treino = self.nome_treino_var.get().strip().upper()
        nome_exercicio = self.exercicio_var.get()
        series = self.series_var.get().strip()
        reps = self.reps_var.get().strip()
        carga = self.carga_var.get().strip()

        if not nome_treino or not nome_exercicio:
            messagebox.showwarning("Aviso", "Preencha o Nome do Treino e selecione um Exercício.")
            return

        mensagem, sucesso = adicionar_exercicio_a_treino(cliente_id, nome_treino, nome_exercicio, series, reps, carga)

        if sucesso:
            messagebox.showinfo("Sucesso", mensagem)
            # Atualiza a visualização do treino
            self.limpar_treino_view()
            self.exibir_treinos_cliente(cliente_id)
        else:
            messagebox.showerror("Erro", mensagem)


# Inicia a aplicação
if __name__ == "__main__":
    app = SistemaPersonalTrainer()
    app.mainloop()