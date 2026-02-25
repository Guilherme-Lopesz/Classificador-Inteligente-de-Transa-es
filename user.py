# ========== IMPORTS ==========
# Importa a biblioteca hashlib para criptografar senhas (transformar em código)
import hashlib

# Importa SQLite3 (banco de dados local)
# "as lite" = apelido curto para usar em todo o código
import sqlite3 as lite


# ========== FUNÇÃO VALIDAR SENHA ==========
# Função que verifica se a senha é forte (segura)
# Retorna: True se OK, False se fraca
def validar_senha(senha):
    """
    Verifica se a senha atende aos requisitos de segurança.
    
    Requisitos:
    - Mínimo 8 caracteres
    - Pelo menos 1 letra maiúscula (A-Z)
    - Pelo menos 1 caractere especial (!@#$%^&* etc)
    """
    
    # Verifica se tem pelo menos uma letra maiúscula
    # any() = True se PELO MENOS UMA condição é verdadeira
    # c.isupper() = pergunta se o caractere 'c' é maiúsculo
    # for c in senha = loopa por CADA caractere da senha
    tem_maiuscula = any(c.isupper() for c in senha)
    
    # Verifica se tem caracteres especiais (não só números e letras)
    # senha.isalnum() = True se tem APENAS números e letras
    # not ... = inverte (se é só alnum, vira False; se tem especiais, vira True)
    tem_especial = not senha.isalnum()
    
    # Retorna True SOMENTE se TODAS as condições forem verdadeiras:
    # 1. len(senha) > 7 = tem mais de 7 caracteres (mínimo 8)
    # 2. AND tem_especial = TEM caracteres especiais
    # 3. AND tem_maiuscula = TEM letra maiúscula
    # Se todas passarem, retorna True (senha válida)
    # Se alguma falhar, retorna False (senha fraca)
    return len(senha) > 7 and tem_especial and tem_maiuscula


# ========== FUNÇÃO GERAR HASH ==========
# Função que transforma a senha em um código irreversível
# Exemplo: "Abc@1234" → "8a7f3b2c9e1d4f6a..." (nunca volta)
def gerar_hash(senha):
    """    
    Por que hash?
    - Mesmo que banco seja roubado, senha não é visível
    - É impossível voltar: hash → senha (unidirecional)
    - Mesma senha SEMPRE gera mesmo hash (determinístico)
    """
    
    # Passo 1: .encode() = converte texto em bytes (números)
    # Passo 2: hashlib.sha256() = aplica algoritmo SHA-256
    # Passo 3: .hexdigest() = retorna como string hexadecimal (0-9, A-F)
    # Resultado: 64 caracteres de código irreversível
    return hashlib.sha256(senha.encode()).hexdigest()


# ========== FUNÇÃO LOGIN ==========
# Função que autentica um usuário (verifica se email e senha estão corretos)
def login_usuario(email, senha_digitada):
    """
    Autentica usuário verificando email e senha no banco.
    
    Retorna:
    - (True, id_usuario) = Sucesso! ID armazenado para manter logado
    - (False, "mensagem_erro") = Falha com explicação
    """
    
    # Try-except = tenta executar, se erro, captura e trata
    try:
        # PASSO 1: Abre conexão com banco de dados
        # lite.connect() = conecta (se não existir, cria arquivo vazio)
        con = lite.connect('Classificador Inteligente de Transações.db')
        
        # PASSO 2: Configura para acessar colunas por nome
        # Sem isso: usuario[0], usuario[1]... (confuso)
        # Com isso: usuario['email'], usuario['senha']... (claro!)
        con.row_factory = lite.Row
        
        # PASSO 3: Cria cursor (ferramenta para rodar SQL)
        cur = con.cursor()
        
        # PASSO 4: Executa query SQL para BUSCAR usuário pelo email
        # SELECT * = pega TODAS as colunas
        # FROM users = da tabela users
        # WHERE email = ? = onde email seja igual ao inserido
        # (email,) = substitui o "?" (seguro contra SQL injection)
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        
        # PASSO 5: Pega o PRIMEIRO resultado
        # fetchone() = primeira linha encontrada (ou None se não achou)
        usuario = cur.fetchone()
        
        # PASSO 6: IMPORTANTE - Fecha conexão IMEDIATAMENTE
        # Bom hábito: não deixa conexões abertas desnecessariamente
        con.close()
        
        # PASSO 7: Verifica se usuário existe no banco
        if usuario:
            # CASO 1: Usuário encontrado!
            # Compara o HASH da senha digitada com o HASH guardado no banco
            # gerar_hash(senha_digitada) = transforma o que digitou em hash
            # usuario['password_hash'] = hash guardado no banco
            # Se forem iguais, senhas são iguais!
            if gerar_hash(senha_digitada) == usuario['password_hash']:
                # ✅ SUCESSO! Retorna (True, ID_usuario)
                # ID é usado para identificar o usuário nas próximas requisições
                return True, usuario['id']
            
            # CASO 2: Email existe, mas senha está ERRADA
            # Retorna erro específico (não expõe que email existe por segurança)
            return False, "Senha incorreta"
        
        # CASO 3: Email NÃO existe no banco
        # Retorna erro (usuário não existe)
        return False, "E-mail não encontrado"
        
    # Se algo der erro (banco offline, disco cheio, etc)
    except Exception as e:
        # Retorna erro genérico (não expõe detalhes internos)
        return False, f"Erro: {str(e)}"


# ========== FUNÇÃO 4: CADASTRO ==========
# Função que registra um novo usuário no banco de dados
def cadastrar_usuario(nome, email, senha_nova):
    """
    Registra novo usuário no banco de dados.
    
    Validações:
    - Senha deve ser forte (função validar_senha)
    - Email deve ser único (não pode repetir)
    
    Retorna:
    - (True, "Cadastro realizado!") = Sucesso
    - (False, "mensagem_erro") = Falha com motivo
    """
    
    # PASSO 1: Valida força da senha ANTES de tudo
    # Se não passou na validação, retorna erro (sem salvar no banco)
    if not validar_senha(senha_nova):
        # ❌ Senha fraca
        # Explica ao usuário por que foi rejeitada
        return False, "Senha inválida (mínimo 8 caracteres, 1 maiúscula, 1 especial)"
    
    try:
        # PASSO 2: Abre conexão com banco
        con = lite.connect('Classificador Inteligente de Transações.db')
        
        # PASSO 3: Cria cursor para executar SQL
        cur = con.cursor()
        
        # PASSO 4: Gera hash da senha (transforma em código)
        # Exemplo: "Abc@1234" → "8a7f3b2c..."
        # NUNCA armazena senha em texto plano! Sempre hash!
        senha_hash = gerar_hash(senha_nova)
        
        # PASSO 5: Tenta INSERIR novo usuário no banco
        # INSERT INTO users = insere nova linha na tabela users
        # (nome, email, password_hash) = colunas a preencher
        # VALUES (?, ?, ?) = valores (? é placeholder seguro)
        # (nome, email, senha_hash) = substitui os placeholders
        cur.execute(
            "INSERT INTO users (nome, email, password_hash) VALUES (?, ?, ?)", 
            (nome, email, senha_hash)
        )
        # ⚠️ Se email já existe, SQLite gera IntegrityError (violou constraint UNIQUE)
        
        # PASSO 6: Se chegou aqui, não teve erro
        # commit() = CONFIRMA a inserção (salva no banco)
        # Sem commit, as mudanças ficam em memória e são perdidas
        con.commit()
        
        # PASSO 7: Fecha conexão
        con.close()
        
        # ✅ SUCESSO!
        return True, "Cadastro realizado!"
        
        # TRATAMENTO DE ERRO ESPECÍFICO
    except lite.IntegrityError:
        return False, "E-mail já cadastrado."