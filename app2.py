# ========== IMPORTS (BIBLIOTECAS EXTERNAS) ==========
# Importa "os" para acessar variáveis de ambiente e manipular arquivos
import os
import threading
# Importa Flask e seus decompositores
# Flask = framework web para criar aplicação
# render_template = mostra arquivos HTML com dados
# request = pega dados dos formulários/requisições HTTP
# redirect = redireciona para outra página
# url_for = gera URLs automaticamente (mais seguro)
# flash = mostra mensagens temporárias ao usuário
# session = guarda dados do usuário logado (cookies)
from flask import Flask, render_template, request, redirect, url_for, flash, session

# Importa SQLite3 para conectar ao banco de dados
import sqlite3

# Importa funções de autenticação e cadastro de user.py
from user import login_usuario, cadastrar_usuario             

# Importa função que processa CSV de transactions.py
from transactions import upload_to_csv_db

# Importa funções de processor.py:
# aplicar_regras_automaticas = aplica regras do usuário
# processar_com_ia = classifica com IA
from processor import aplicar_regras_automaticas, processar_com_ia

# ========== CONFIGURAÇÃO FLASK ==========
# Cria instância de aplicação Flask
# __name__ = nome do módulo (usado para encontrar templates)
app = Flask(__name__)

# Define chave secreta para criptografar dados da sessão
# IMPORTANTE: Nunca deixar no código em produção! Use variável de ambiente
app.secret_key = 'chave_secreta_para_desafio'

# ========== CONSTANTES ==========
# Lista de categorias permitidas (padrão)
# Usada para validação em vários locais
CATEGORIAS_PERMITIDAS = ["Transporte", "Assinaturas", "Alimentação", "Receita", "Compras Online", "Outros"]

# ========== FUNÇÃO HELPER: CONECTAR BANCO ==========
# Função auxiliar para abrir conexão com banco em cada rota
# Isso garante que cada requisição tem conexão fresca
def conectar_bd():
    """Abre e configura conexão com banco de dados."""
    
    # Conecta ao banco SQLite
    con = sqlite3.connect('Classificador Inteligente de Transações.db', timeout=30, check_same_thread=False)    
    # Configura para acessar por nome de coluna (Ex: row['email'])
    # Muito mais legível do que índices (row[0])
    con.row_factory = sqlite3.Row 
    
    # Retorna conexão configurada
    return con

# ========== ROTA ÍNDICE (RAIZ) ==========
# @app.route('/') = quando usuário acessa "http://localhost:5000/"
# methods=['GET'] = padrão (aceita apenas GET)
@app.route('/')
def index():
    """Redireciona raiz para dashboard."""
    # Redireciona imediatamente para dashboard
    # url_for('dashboard') = gera URL da função dashboard() automaticamente
    return redirect(url_for('dashboard'))

# ========== ROTA REGISTRO ==========
# @app.route('/register', methods=['GET', 'POST'])
# GET = mostra formulário
# POST = processa formulário preenchido
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registra novo usuário."""
    
    # Se método é POST (formulário foi enviado)
    if request.method == 'POST':
        # Pega dados do formulário HTML
        # request.form.get('nome') = extrai campo "nome" do form
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('password')
        
        # Chama função de cadastro do user.py
        # Retorna (sucesso: bool, mensagem: str)
        sucesso, msg = cadastrar_usuario(nome, email, senha)
        
        # Mostra mensagem (flash = notificação temporária)
        # 'success' ou 'error' = tipo de mensagem (para CSS estilizar)
        flash(msg, 'success' if sucesso else 'error')  
        
        # Se cadastro foi sucesso, redireciona para login
        if sucesso: 
            return redirect(url_for('login'))  
    
    # Se GET ou cadastro falhou, mostra template de registro
    # render_template('register.html') = carrega HTML da pasta "templates"
    return render_template('register.html')


# ========== ROTA LOGIN ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Autentica usuário."""
    
    # Se método é POST (formulário foi enviado)
    if request.method == 'POST':
        # Pega email e senha do formulário
        email_digitado = request.form.get('email')
        senha_digitada = request.form.get('password')
        
        # Chama função de login do user.py
        # Retorna (sucesso: bool, resultado: id ou mensagem_erro)
        sucesso, resultado = login_usuario(email_digitado, senha_digitada)
        
        # Se login foi sucesso
        if sucesso:
            # resultado = ID do usuário (número)
            user_id = resultado
            
            # Armazena ID em session (será mantido em cookies)
            # A partir de agora, usuário é identificado por este ID em todas as rotas
            session['user_id'] = user_id
            
            # Armazena email também
            session['user_email'] = email_digitado 
            
            # Abre banco para pegar dados adicionais do usuário
            db = conectar_bd()
            cur = db.cursor()
            
            # Busca nome do usuário no banco
            # SELECT nome = apenas a coluna "nome"
            # WHERE id = ? = deste usuário específico
            cur.execute("SELECT nome FROM users WHERE id = ?", (user_id,))
            
            # Pega primeira linha (só tem uma porque ID é único)
            usuario = cur.fetchone()
            
            # Fecha conexão
            db.close()
            
            # Se encontrou dados do usuário
            if usuario:
                # usuario[0] = primeira coluna do resultado (NOME)
                # Armazena nome em session para usar nas templates
                session['user_nome'] = usuario[0] 
            
            # Redireciona para dashboard (página principal)
            return redirect(url_for('dashboard'))
        
        # Se login falhou, resultado = mensagem de erro
        # Mostra mensagem de erro
        flash(resultado, 'error')  
    
    # Se GET ou login falhou, mostra template de login
    return render_template('login.html')

# ========== ROTA DASHBOARD (PÁGINA PRINCIPAL) ==========
@app.route('/dashboard')
def dashboard():
    """Mostra dashboard com transações e gráfico."""
    
    # PROTEÇÃO: Se não tá logado, manda para login
    # 'user_id' não em session = não autenticado
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    # Abre banco de dados
    db = conectar_bd()
    
    # PASSO 1: Busca TODAS as transações do usuário
    # ORDER BY date DESC = mais recente primeiro
    transacoes = db.execute(
        'SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC', 
        (session['user_id'],)
    ).fetchall()
    
    # PASSO 2: Busca TODAS as categorias confirmadas do usuário
    # Usado para popular lista de categorias no dropdown
    categorias_usuario = db.execute(
        "SELECT DISTINCT confirmed_category FROM transactions WHERE user_id = ? AND confirmed_category IS NOT NULL", 
        (session['user_id'],)
    ).fetchall()

    # Começa com categorias padrão
    todas_categorias = set(CATEGORIAS_PERMITIDAS)
    
    # Adiciona categorias personalizadas (que o usuário criou)
    for c in categorias_usuario:
        todas_categorias.add(c['confirmed_category'])
    
    # Converte set para lista ordenada (A-Z)
    lista_categorias = sorted(list(todas_categorias))

    # PASSO 3: Prepara dados para gráfico
    # Somará TODAS as despesas por categoria
    dados_grafico = {}
    
    # Para cada transação
    for t in transacoes:
        # Se transação está confirmada E tem categoria confirmada
        if t['status'] == 'confirmed' and t['confirmed_category']:
            # Pega a categoria
            cat = t['confirmed_category']
            
            # Se é despesa (amount < 0), adiciona ao gráfico
            # abs() = valor absoluto (remove o -)
            # Faz: dados_grafico['Transporte'] += 45.90
            dados_grafico[cat] = dados_grafico.get(cat, 0) + abs(t['amount'])
    
    # Fecha conexão
    db.close()

    # PASSO 4: Retorna template com dados
    # render_template('dashboard.html', ...) = mostra HTML com dados
    return render_template('dashboard.html', 
                           # Todas as transações
                           transacoes=transacoes, 
                           # Lista de categorias para dropdown
                           categorias=lista_categorias,
                           # Nomes das categorias para gráfico (labels)
                           labels_chart=list(dados_grafico.keys()),
                           # Valores das categorias para gráfico (dados)
                           valores_chart=list(dados_grafico.values()))

# ========== ROTA LOGOUT ==========
@app.route('/logout')
def logout():
    """Desconecta usuário."""
    
    # session.clear() = remove TODOS os dados da sessão
    # Efetivamente "desconecta" o usuário
    session.clear()
    
    # Mostra mensagem informativa
    flash("Você saiu do sistema.", "info")
    
    # Redireciona para login
    return redirect(url_for('login'))

# ========== ROTA UPLOAD DE CSV ==========
@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session: return redirect(url_for('login'))
    arquivos = request.files.getlist('file')
    processou_algo = False
    mensagem_de_erro = "Nenhum arquivo CSV ou TXT válido enviado."
    
    for f in arquivos:
        if f.filename == '' or not f.filename.lower().endswith(('.csv', '.txt')): 
            continue
            
        caminho = os.path.join(app.root_path, f.filename)
        f.save(caminho)
        sucesso, msg = upload_to_csv_db(caminho, session['user_id'])
        
        if os.path.exists(caminho): os.remove(caminho)
        if sucesso: 
            processou_algo = True
        else:
            mensagem_de_erro = msg 
    
    if processou_algo:
        # Aplica as regras rápidas na hora
        aplicar_regras_automaticas(session['user_id'])
        
        # 🔥 A MÁGICA: Inicia a IA em SEGUNDO PLANO. A tela não trava mais!
        thread_ia = threading.Thread(target=processar_com_ia, args=(session['user_id'],))
        thread_ia.start()
        
        flash("Upload concluído! A IA está classificando os dados em segundo plano. Atualize a página em alguns segundos para ver as sugestões.", "success")
    else:
        flash(f"Falha no arquivo: {mensagem_de_erro}", "error")
        
    return redirect(url_for('dashboard'))
    
    # PROCESSAMENTO PÓS-UPLOAD
    if processou_algo:
        # Aplica regras automáticas (palavras-chave)
        # de processor.py
        aplicar_regras_automaticas(session['user_id'])
        
        # Classifica com IA as transações que não tiveram regra
        processar_com_ia(session['user_id'])
        
        # Mostra sucesso
        flash("Arquivo(s) processados com sucesso!", "success")
    else:
        # Nenhum arquivo válido
        flash("Nenhum arquivo CSV válido foi processado.", "error")
    
    # Volta ao dashboard
    return redirect(url_for('dashboard'))

# ========== ROTA CONFIRMAR TRANSAÇÃO ==========
@app.route('/confirmar', methods=['POST'])
def confirmar():
    """Confirma uma transação individual."""
    
    # Proteção: Se não logado
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    # Pega dados do formulário
    id_t = request.form.get('transaction_id')  # ID da transação
    cat = request.form.get('category')  # Categoria escolhida
    criar_regra = request.form.get('criar_regra')  # Checkbox marcado?
    palavra_chave = request.form.get('palavra_chave')  # Palavra para a regra
    user_id = session['user_id']
    
    # Abre banco
    db = conectar_bd()
    
    # Verifica se transação existe
    # Busca a descrição (será usada para extrair palavra-chave padrão)
    t = db.execute("SELECT description FROM transactions WHERE transaction_id = ?", (id_t,)).fetchone()
    
    # Se transação existe
    if t:
        # PASSO 1: Atualiza status e categoria da transação
        # confirmed_category = categoria que usuário escolheu
        # status = 'confirmed' (foi confirmada)
        db.execute(
            "UPDATE transactions SET confirmed_category = ?, status = 'confirmed' WHERE transaction_id = ?", 
            (cat, id_t)
        )
        
        # PASSO 2: Registra no audit log
        # action = 'user_confirmed' (usuário confirmou manualmente)
        # source = 'user' (veio do usuário, não da IA)
        db.execute(
            "INSERT INTO audit_log (transaction_id, user_id, action, new_category, source) VALUES (?, ?, 'user_confirmed', ?, 'user')", 
            (id_t, user_id, cat)
        )
        
        # PASSO 3: Cria regra se usuário marcou checkbox
        # criar_regra == 'on' = checkbox foi marcado
        # palavra_chave = texto da regra (ex: "UBER")
        if criar_regra == 'on' and palavra_chave:
            # Verifica se esta regra já existe (para não duplicar)
            existe = db.execute(
                "SELECT id FROM rules WHERE user_id = ? AND keyword = ?", 
                (user_id, palavra_chave)
            ).fetchone()
            
            # Se não existe, cria
            if not existe:
                # Insere nova regra
                # keyword = palavra a procurar
                # category = categoria automática
                db.execute(
                    "INSERT INTO rules (user_id, keyword, category) VALUES (?, ?, ?)", 
                    (user_id, palavra_chave, cat)
                )
        
        # Confirma mudanças
        db.commit()
        
        # Mostra sucesso
        flash("Transação confirmada com sucesso!", "success")
    else:
        # Transação não existe (erro raro)
        flash("Transação não encontrada.", "error")
    
    # Fecha conexão
    db.close()
    
    # Volta ao dashboard
    return redirect(url_for('dashboard'))

# ========== ROTA EDITAR TRANSAÇÃO ==========
@app.route('/editar', methods=['POST'])
def editar():
    """Edita categoria de uma transação."""
    
    # Proteção
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    # Pega dados
    id_t = request.form.get('transaction_id')
    nova_cat = request.form.get('category')
    criar_regra = request.form.get('criar_regra')
    palavra_chave = request.form.get('palavra_chave')
    user_id = session['user_id']
    
    # Abre banco
    db = conectar_bd()
    
    # Atualiza categoria e marca como confirmada
    db.execute(
        "UPDATE transactions SET confirmed_category = ?, status = 'confirmed' WHERE transaction_id = ?", 
        (nova_cat, id_t)
    )
    
    # Registra no audit log
    db.execute(
        "INSERT INTO audit_log (transaction_id, user_id, action, new_category, source) VALUES (?, ?, 'user_edited', ?, 'user')", 
        (id_t, user_id, nova_cat)
    )
    
    # Cria regra se marcou checkbox
    if criar_regra == 'on' and palavra_chave:
        db.execute(
            "INSERT INTO rules (user_id, keyword, category) VALUES (?, ?, ?)", 
            (user_id, palavra_chave, nova_cat)
        )
    
    # Confirma
    db.commit()
    db.close()
    
    # Mostra mensagem
    flash("Categoria editada com sucesso!", "success")
    
    # Volta ao dashboard
    return redirect(url_for('dashboard'))

# ========== ROTA EXCLUIR TRANSAÇÃO ==========
@app.route('/excluir', methods=['POST'])
def excluir():
    """Deleta uma transação."""
    
    # Proteção
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    # Pega dados
    id_t = request.form.get('transaction_id')
    user_id = session['user_id']
    
    # Abre banco
    db = conectar_bd()
    
    # PASSO 1: Deleta transação
    # WHERE user_id = ? garante que só pode deletar suas próprias transações
    db.execute(
        "DELETE FROM transactions WHERE transaction_id = ? AND user_id = ?", 
        (id_t, user_id)
    )
    
    # PASSO 2: Registra no audit log
    # action = 'user_deleted' (usuário deletou)
    # new_category = 'DELETED' (foi deletada)
    db.execute(
        "INSERT INTO audit_log (transaction_id, user_id, action, new_category, source) VALUES (?, ?, 'user_deleted', 'DELETED', 'user')", 
        (id_t, user_id)
    )
    
    # Confirma
    db.commit()
    db.close()
    
    # Mostra mensagem
    flash("Transação excluída com sucesso.", "info")
    
    # Volta ao dashboard
    return redirect(url_for('dashboard'))

# ========== ROTA AÇÃO EM LOTE ==========
@app.route('/acao_lote', methods=['POST'])
def acao_lote():
    """Aplica ação em múltiplas transações."""
    
    # Proteção
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    # Pega dados
    # request.form.getlist() = pega VÁRIOS valores com mesmo name
    # Exemplo: checkboxes marcadas
    ids = request.form.getlist('transacao_ids')
    
    # Qual ação fazer? 'confirmar' ou 'excluir'
    acao = request.form.get('acao_lote')
    user_id = session['user_id']
    
    # Abre banco
    db = conectar_bd()
    
    # Para CADA ID selecionado
    for id_t in ids:
        if acao == 'excluir':
            # Deleta a transação
            db.execute(
                "DELETE FROM transactions WHERE transaction_id = ? AND user_id = ?", 
                (id_t, user_id)
            )
        elif acao == 'confirmar':
            # Busca transação com sua categoria sugerida
            t = db.execute(
                "SELECT description, suggested_category FROM transactions WHERE transaction_id = ?", 
                (id_t,)
            ).fetchone()
            
            # Se transação existe
            if t:
                # Usa categoria sugerida (pela regra ou IA)
                # Se não tiver sugestão, usa 'Outros'
                cat_final = t['suggested_category'] or 'Outros'
                
                # Atualiza como confirmada
                db.execute(
                    "UPDATE transactions SET confirmed_category = ?, status = 'confirmed' WHERE transaction_id = ?", 
                    (cat_final, id_t)
                )
                
                # Registra no audit log
                db.execute(
                    "INSERT INTO audit_log (transaction_id, user_id, action, new_category, source) VALUES (?, ?, 'batch_confirmed', ?, 'user')", 
                    (id_t, user_id, cat_final)
                )
    
    # Confirma mudanças
    db.commit()
    db.close()
    
    # Mostra sucesso
    flash(f"Ação em lote aplicada!", "success")
    
    # Volta ao dashboard
    return redirect(url_for('dashboard'))


# ========== ROTA ADICIONAR TRANSAÇÃO MANUAL ==========
@app.route('/adicionar', methods=['POST'])
def adicionar_transacao():
    """Adiciona transação manualmente (sem upload)."""
    
    # Proteção
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Pega dados do formulário
    data = request.form.get('data')  # DD/MM/YYYY
    descricao = request.form.get('descricao')  # Descrição
    valor = request.form.get('valor')  # Valor em R$
    user_id = session['user_id']

    # Valida se todos os campos foram preenchidos
    if not data or not descricao or not valor:
        flash("Preencha todos os campos.", "error")
        return redirect(url_for('dashboard'))

    # Tenta converter valor para número
    try:
        # replace(',', '.') = transforma formato brasileiro em universal
        # float() = converte para decimal
        valor_float = float(valor.replace(',', '.'))
    except:
        # Se falhar, valor tem formato inválido
        flash("Valor inválido.", "error")
        return redirect(url_for('dashboard'))

    # Abre banco
    db = conectar_bd()
    cur = db.cursor()
    
    # Insere nova transação manual
    # status = 'pending' = não confirmada ainda
    cur.execute('''
        INSERT INTO transactions (user_id, date, description, amount, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (user_id, data, descricao, valor_float))
    
    # Pega ID da transação que foi criada (para audit log)
    id_nova = cur.lastrowid
    
    # Registra no audit log
    # action = 'created' (transação criada)
    # new_category = 'MANUAL' (foi criada manualmente, não por upload)
    # source = 'user' (criada pelo usuário)
    cur.execute('''
        INSERT INTO audit_log (transaction_id, user_id, action, new_category, source)
        VALUES (?, ?, 'created', 'MANUAL', 'user')
    ''', (id_nova, user_id))
    
    # Confirma mudanças
    db.commit()
    db.close()
    
    # Mostra sucesso
    flash("Transação adicionada manualmente.", "success")
    
    # Volta ao dashboard
    return redirect(url_for('dashboard'))


# ========== ROTA PÁGINA DE CATEGORIAS ==========
@app.route('/categorias')
def categorias():
    """Mostra resumo de gastos por categoria."""
    
    # Proteção
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Pega ID do usuário logado
    user_id = session['user_id']
    
    # Abre banco
    db = conectar_bd()
    
    # Busca TODAS as categorias (confirmadas e sugeridas)
    # UNION = combina dois SELECT
    # DISTINCT = remove duplicatas
    categorias = db.execute('''
        SELECT DISTINCT confirmed_category as cat FROM transactions 
        WHERE user_id = ? AND confirmed_category IS NOT NULL
        UNION
        SELECT DISTINCT suggested_category FROM transactions 
        WHERE user_id = ? AND suggested_category IS NOT NULL
    ''', (user_id, user_id)).fetchall()
    
    # Lista para armazenar dados formatados de cada categoria
    dados_categorias = []
    
    # Para CADA categoria encontrada
    for cat in categorias:
        # Extrai nome da categoria
        nome = cat['cat']
        
        # Pula se estiver vazia
        if not nome:
            continue
        
        # Busca TODAS as transações desta categoria
        # confirmed_category = confirmas do usuário
        # suggested_category = sugestões da IA/regras
        trans = db.execute('''
            SELECT * FROM transactions 
            WHERE user_id = ? AND (confirmed_category = ? OR suggested_category = ?)
            ORDER BY date DESC
        ''', (user_id, nome, nome)).fetchall()
        
        # Calcula TOTAL de gastos desta categoria
        # sum() = soma
        # abs(t['amount']) = valor absoluto (remove -)
        # if t['amount'] < 0 = apenas gastos (negativos)
        # Não conta receitas (positivas)
        total = sum(abs(t['amount']) for t in trans if t['amount'] < 0)
        
        # Adiciona dados desta categoria à lista
        dados_categorias.append({
            'nome': nome,  # Nome da categoria
            'transacoes': trans,  # Lista de transações
            'total': total,  # Total gasto
            'quantidade': len(trans)  # Quantas transações
        })
    
    # Fecha conexão
    db.close()
    
    # Retorna template com dados
    return render_template('categorias.html', categorias=dados_categorias)


# ========== INICIALIZA E EXECUTA ==========
# Este bloco roda se arquivo for executado diretamente
# if __name__ == "__main__" = true apenas se executado direto (não importado)
if __name__ == '__main__':
    # debug=True = modo debug (recarrega automaticamente, mostra erros det alhe)
    app.run(debug=True)