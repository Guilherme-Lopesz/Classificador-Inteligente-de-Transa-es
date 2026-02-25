# Importa Pandas: biblioteca para ler e processar arquivos CSV
import pandas as pd

# Importa SQLite3 com apelido "lite" (banco de dados local)
import sqlite3 as lite

# Importa "re" (regular expressions) para procurar/remover padrões de texto
# Usado para limpar descrições (remover CPF, CNPJ, etc)
import re

# ========== FUNÇÃO LIMPAR DESCRIÇÃO ==========
# Função que remove informações sensíveis da descrição
# Exemplo: "IFOOD - CPF: 123.456.789-01 - Agência: 0001" → "IFOOD"
def limpar_descricao(desc):
    
    # Verifica se DESC é realmente um texto
    # Se for número, None, ou outro tipo, retorna padrão
    if not isinstance(desc, str):
        return "Transação"
    
    # Remove padrão: "Agência: 0001 Conta: 12345-6"
    # r'...' = "raw string" (interpreta \ literalmente)
    # (?i) = case-insensitive (ignora maiúscula/minúscula)
    # \d+ = um ou mais dígitos
    # \s* = zero ou mais espaços
    # '' = substitui por vazio (remove)
    desc = re.sub(r'(?i)Agência:\s*\d+\s*Conta:\s*[\d\-]+', '', desc)
    
    # Remove CPF em formato "123•456•789-01" ou similar
    # \s* = espaços
    # [-•]+ = um ou mais hífen ou bullet
    # \d{3} = exatamente 3 dígitos
    desc = re.sub(r'\s*[-•]+\s*\d{3}\.\d{3}\.\d{3}[-•]\d{2}\s*', '', desc)
    
    # Remove CNPJ em formato "12.345.678/0001-99"
    # \d{2} = 2 dígitos
    # \. = ponto literal
    # / = barra literal
    # - = hífen literal
    desc = re.sub(r'\s*\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\s*', '', desc)
    
    # Remove CPF sem separador completo: "123•456•789"
    desc = re.sub(r'\s*[-•]+\s*\d{3}\.\d{3}\.\d{3}\s*', '', desc)
    
    # Remove espaços nas pontas e hífers soltos que ficaram
    # strip() = remove das extremidades
    return desc.strip(' -')

# ========== FUNÇÃO CONVERTER PARA REAL ==========
# Função que transforma formato brasileiro em número
# Exemplo: "R$ 1.234,56" → 1234.56
def parse_brl(val):
    """
    Converte string no formato brasileiro (R$ 1.234,56) para float.
    
    Casos tratados:
    - "R$ 1.234,56" → 1234.56 (com símbolo)
    - "1.234,56" → 1234.56 (sem símbolo)
    - "1,50" → 1.5 (apenas vírgula)
    - 100 → 100.0 (já é número)
    """
    
    # Se já é número (int ou float), apenas converte para float
    if isinstance(val, (int, float)):
        return float(val)
    
    #Transforma para string e remove símbolo R$ e espaços
    s = str(val).replace('R$', '').replace(' ', '').strip()
    
    #Determina o formato (. e , podem aparecer juntos)
    # Caso 1: se tem AMBOS (ponto e vírgula)
    # Exemplo: "1.234,56"
    # . = separador de milhar (remove)
    # , = separador decimal (troca por .)
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    
    # Caso 2: Tem APENAS vírgula
    # Exemplo: "1,50" (sem milhar)
    # , = separador decimal (troca por .)
    elif ',' in s:
        s = s.replace(',', '.')
    
    # PASSO 3: Converte string em número decimal
    # Agora s está em formato universal (ex: "1234.56")
    # float() converte para número
    return float(s)

# ========== FUNÇÃO UPLOAD CSV PARA BANCO ==========
# Função principal que lê CSV e insere no banco de dados
def upload_to_csv_db(file_path, user_id):
    """
    Lê arquivo CSV e insere transações no banco de dados.
    
    Passos:
    1. Lê arquivo (tenta vários separadores/encodings)
    2. Valida colunas obrigatórias
    3. Processa valores monetários
    4. Limpa descrições
    5. Insere no banco com criação de audit log
    
    Retorna:
    - (True, "mensagem") = Sucesso
    - (False, "erro") = Falha com motivo
    """
    
    #Abre conexão com banco
    con = lite.connect("Classificador Inteligente de Transações.db", timeout=30, check_same_thread=False)    
    cur = con.cursor()
    
    try:
        #Tenta ler CSV com diferentes separadores
        # Problema: diferentes bancos usam , ou ;
        # Solução: tenta todos até um funcionar
        df = None
        for sep in [',', ';', '\t']:  # Tenta vírgula, ponto-e-vírgula, tab
            try:
                # Lê usando pandas (biblioteca para dados)
                # sep = separador de colunas
                # encoding='utf-8-sig' = formato texto universal
                df = pd.read_csv(file_path, sep=sep, encoding='utf-8-sig')
                break  # Se funcionou, SAI do loop
            except:
                # Separador não funcionou, tenta o próximo
                continue
        
        # Se nenhum separador funcionou, df ainda é None
        if df is None:
            return False, "Não foi possível ler o CSV. Verifique o formato (separador e encoding)."

        #Normaliza nomes de colunas
        # .columns = pega nomes das colunas
        # .str.strip() = remove espaços nas pontas
        # .str.lower() = transforma em minúscula
        # Exemplo: " Data " → "data"
        df.columns = df.columns.str.strip().str.lower()
        
        # Cria dicionário para renomear colunas (aceita várias formas)
        # Usuários podem digitar "Data" ou "data" ou "Descrição" ou "descricao"
        rename_map = {
            'data': 'date',  # Aceita "data" também
            'descrição': 'description',  # Aceita com acento
            'descricao': 'description',  # Aceita sem acento
            'valor': 'amount'  # Aceita "valor" também
        }
        
        # Aplica renomeação (in place = modifica o df original)
        df.rename(columns=rename_map, inplace=True)

        #Valida se tem as 3 colunas obrigatórias
        # .issubset() = verifica se está contido em
        # {'date', 'description', 'amount'} = conjunto de colunas necessárias
        if not {'date', 'description', 'amount'}.issubset(df.columns):
            # Faltam colunas, mostra o que foi encontrado
            return False, f"Colunas necessárias: date, description, amount. Encontradas: {list(df.columns)}"

        #Processa coluna de AMOUNT (valores)
        # .apply(parse_brl) = aplica função parse_brl em CADA linha
        # Transforma "R$ 1.234,56" em 1234.56
        df['amount'] = df['amount'].apply(parse_brl)
        
        # Remove linhas com valores vazios/inválidos
        # .dropna() = remove "not a number"
        df = df.dropna(subset=['amount'])
        
        # Se não sobrou nenhuma linha, erro!
        if df.empty:
            return False, "Nenhuma transação válida encontrada."

        #Limpa descrições (remove CPF, CNPJ, etc)
        # .apply(limpar_descricao) = aplica limpeza em CADA descrição
        df['description'] = df['description'].apply(limpar_descricao)

        #Insere CADA linha do CSV no banco
        # .iterrows() = itera (loopa) por cada linha
        # _, row = ignora índice, pega apenas os dados
        for _, row in df.iterrows():
            # Insere na tabela transactions
            # (user_id, date, description, amount, status)
            # Status começa como 'pending' (aguardando confirmação)
            cur.execute('''
                INSERT INTO transactions (user_id, date, description, amount, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (user_id, row['date'], row['description'], row['amount']))
            
            #Registra no AUDIT LOG
            # Rastreia que esta transação foi criada (para auditoria)
            # cur.lastrowid = ID da linha que acabou de ser criada
            cur.execute('''
                INSERT INTO audit_log (transaction_id, user_id, action, new_category, source)
                VALUES (?, ?, 'created', 'NEW_UPLOAD', 'user')
            ''', (cur.lastrowid, user_id))

        #Confirma todas as mudanças no banco
        con.commit()
        
        # Retorna sucesso
        return True, "Upload concluído"
        
    # Se algum erro não previsto acontecer
    except Exception as e:
        # Retorna erro com explicação (não quebra o programa)
        return False, f"Erro: {str(e)}"
    
    # FINALLY: Garante que fecha conexão (mesmo se der erro)
    finally:
        con.close()