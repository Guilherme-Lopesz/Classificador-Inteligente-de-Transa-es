# ========== IMPORTS ==========
# Importa "os" para acessar variáveis de ambiente (como API keys)
import os

# Importa "json" para parse/conversão de JSON (formato de dados)
import json

# Importa "time" para pausar código (usado em retry com espera)
import time

# Importa "re" (regular expressions) para extrair texto/padrões
# Usado para encontrar tempo de retry nos erros da API
import re

# Importa cliente Google Generative AI (Gemini)
# genai = módulo do Google
from google import genai

# Importa tipos de configuração do cliente (resposta JSON, etc)
from google.genai import types

# Importa load_dotenv para ler arquivo .env
# O .env guarda variáveis sensíveis como GOOGLE_API_KEY
from dotenv import load_dotenv

# ========== CONFIGURAÇÃO ==========
# Carrega variáveis do arquivo .env
# Deve ter: GOOGLE_API_KEY=sua_chave_aqui
load_dotenv()

# Cache em memória para evitar reprocessamento
# Estrutura: {chave: resultado}
# Chave = "descricao_valor"
# Valor = resposta da IA armazenada
# Exemplo: {"UBER TRIP_-45.9": {"category": "Transporte", ...}}
_CACHE_CLASSIFICACOES = {}


# ========== FUNÇÃO HELPER 1: EXTRAIR TEMPO DE RETRY ==========
def _extrair_tempo_retry(erro_str):
    """
    Extrai o tempo de espera sugerido pela API no erro 429.
    
    Quando IA retorna erro 429 (quota excedida), diz:
    "Please retry in 16.6s" ou "Please retry in 500ms"
    
    Esta função extrai o número e converte para segundos.
    """
    
    # Usa regex para encontrar padrão "Please retry in X.Xs" ou "Please retry in Xms"
    # r'...' = raw string (não interpreta \ como escape)
    # ([\d.]+) = grupo 1: números e ponto (ex: 16.6, 500)
    # (s|ms)? = grupo 2: opcional "s" ou "ms" (ex: s, ms, ou nada)
    match = re.search(r'Please retry in ([\d.]+)(s|ms)?', str(erro_str))
    
    # Se encontrou o padrão
    if match:
        # match.group(1) = primeiro grupo capturado (número)
        valor = float(match.group(1))
        
        # match.group(2) = segundo grupo capturado (unidade)
        # or 's' = se não tiver unidade, assume segundos
        unidade = match.group(2) or 's'
        
        # Se for segundos, retorna direto
        # Se for milissegundos, divide por 1000 para converter
        return valor if unidade == 's' else valor / 1000
    
    # Se não encontrou padrão, retorna padrão 5 segundos
    # Melhor seguro do que nunca tentar
    return 5


# ========== FUNÇÃO HELPER 2: FALLBACK COM HEURÍSTICAS ==========
def _classificar_por_heuristica(description, amount):
    """
    Fallback: usa heurísticas locais quando IA falha.
    
    Quando IA não pode classificar (sem internet, quota, erro):
    - Usa palavras-chave automáticas
    - Simples mas eficaz
    - Mantém sistema funcionando
    """
    
    # Converte descrição para MAIÚSCULA (para comparar com keywords)
    # Exemplo: "Uber Trip" → "UBER TRIP"
    desc_upper = description.upper()
    
    # ========== CASO 1: RECEITA ==========
    # Se valor é positivo (> 0), é entrada de dinheiro
    # Exemplo: +1000 = salário, herança, etc
    if amount > 0:
        return {
            "category": "Receita",
            # Confiança alta (95%) porque valores positivos são muito específicos
            "confidence": 95,
            "reason": "Valor positivo identificado como receita (heurística)"
        }
    
    # ========== CASO 2: TRANSPORTE ==========
    # Procura por palavras-chave de transporte
    # any() = True se QUALQUER uma das palavras está em desc_upper
    if any(x in desc_upper for x in ["UBER", "99", "LYFT", "TAXI", "GASOLINA", "POSTO", "COMBUSTIVEL", "ESTACIONAMENTO"]):
        return {
            "category": "Transporte",
            # Confiança alta (90%) porque keywords são bem específicos
            "confidence": 90,
            "reason": "Palavras-chave de transporte detectadas"
        }
    
    # ========== CASO 3: ALIMENTAÇÃO ==========
    # Procura por palavras comuns de restaurantes/comida
    if any(x in desc_upper for x in ["IFOOD", "RESTAURANTE", "PADARIA", "SUPERMERcado", "MERCADO", "LANCHE", "COMIDA", "ALIMENT"]):
        return {
            "category": "Alimentação",
            "confidence": 88,
            "reason": "Palavras-chave de alimentação detectadas"
        }
    
    # ========== CASO 4: ASSINATURAS ==========
    if any(x in desc_upper for x in ["NETFLIX", "SPOTIFY", "AMAZON PRIME", "DISNEY", "HBO", "APPLE", "GOOGLE PLAY", "SUBSCRIPTION", "MENSALIDADE"]):
        return {
            "category": "Assinaturas",
            "confidence": 92,
            "reason": "Palavras-chave de assinaturas detectadas"
        }
    
    # ========== CASO 5: COMPRAS ONLINE ==========
    if any(x in desc_upper for x in ["AMAZON", "MERCADO LIVRE", "SHOPEE", "ALIEXPRESS", "EBAY", "ONLINE", "COMPRA"]):
        return {
            "category": "Compras Online",
            "confidence": 85,
            "reason": "Palavras-chave de compras online detectadas"
        }
    
    # ========== CASO PADRÃO: OUTROS ==========
    # Se nada se encaixar, "Outros"
    return {
        "category": "Outros",
        "confidence": 50,
        "reason": "Nenhuma categoria específica detectada (heurística)"
    }


# ========== FUNÇÃO PRINCIPAL: CLASSIFICAÇÃO COM IA ==========
def classificar_transacao_com_ia(description, amount):
    """
    Classifica uma transação usando Google Gemini AI.
    
    Com proteção contra:
    - Quota excedida (429) com retry automático
    - Cache para evitar reprocessamento
    - Fallback para heurísticas se IA falhar
    
    Returns:
        (sucesso: bool, resultado: dict)
        sucesso = True se IA respondeu, False se usou fallback
        resultado = {"category": "...", "confidence": 0-100, "reason": "..."}
    """
    
    # ========== PASSO 1: VERIFICAR CACHE ==========
    cache_key = f"{description}_{amount}"
    if cache_key in _CACHE_CLASSIFICACOES:
        return True, _CACHE_CLASSIFICACOES[cache_key]
    
    # ========== PASSO 2: PREPARAR LISTA DE CATEGORIAS ==========
    categorias_base = ["Transporte", "Assinaturas", "Alimentação", "Receita", "Compras Online", "Outros"]
    
    # ========== PASSO 3: MONTAR INPUT JSON ESTRITO ==========
    input_json = {
        "description": description,
        "amount": amount,
        "available_categories": categorias_base
    }
    input_str = json.dumps(input_json, ensure_ascii=False)
    
    # ========== PASSO 4: CONFIGURAR MODELO COM SYSTEM PROMPT ==========
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest",
        generation_config=types.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.2
        ),
        system_instruction="""
Você recebe um JSON com:
- "description": descrição da transação
- "amount": valor (negativo para saídas, positivo para entradas)
- "available_categories": lista de categorias válidas

Classifique a transação escolhendo UMA categoria de "available_categories".
Retorne SOMENTE um JSON válido com:
- "category": a categoria escolhida
- "confidence": inteiro de 0 a 100
- "reason": explicação breve

Se não puder classificar, use "Outros" com confidence 0.
Não retorne texto extra fora do JSON.
"""
    )
    
    # ========== PASSO 5: LOOP DE RETRY ==========
    max_tentativas = 3
    for tentativa in range(max_tentativas):
        try:
            # ========== TENTAR CHAMAR IA ==========
            response = model.generate_content(
                contents=[{"role": "user", "parts": [input_str]}]
            )
            
            # ========== PARSEAR RESPOSTA ==========
            resultado_json = json.loads(response.text)
            
            # ========== VALIDAÇÃO DE SEGURANÇA ==========
            if resultado_json.get("category") not in categorias_base:
                resultado_json["category"] = "Outros"
                resultado_json["confidence"] = 0
                resultado_json["reason"] = "A IA sugeriu uma categoria inválida. Marcado como Outros."
            
            # ========== SUCESSO! ==========
            _CACHE_CLASSIFICACOES[cache_key] = resultado_json
            return True, resultado_json
            
        except Exception as e:
            erro_str = str(e)
            
            if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
                if tentativa < max_tentativas - 1:
                    tempo_espera = _extrair_tempo_retry(erro_str)
                    print(f"⚠️ Quota da IA excedida. Aguardando {tempo_espera:.1f}s antes de tentar novamente... (tentativa {tentativa + 1}/{max_tentativas})")
                    time.sleep(tempo_espera)
                    continue
                else:
                    print(f"⚠️ Quota excedida após {max_tentativas} tentativas. Usando fallback com heurísticas.")
                    resultado = _classificar_por_heuristica(description, amount)
                    _CACHE_CLASSIFICACOES[cache_key] = resultado
                    return False, resultado
            
            else:
                print(f"⚠️ Erro na IA: {e}")
                resultado = _classificar_por_heuristica(description, amount)
                _CACHE_CLASSIFICACOES[cache_key] = resultado
                return False, resultado
    
    # ========== FALLBACK FINAL ==========
    resultado = _classificar_por_heuristica(description, amount)
    _CACHE_CLASSIFICACOES[cache_key] = resultado
    return False, resultado


# ========== TESTE (EXECUTAR DIRETO) ==========
if __name__ == "__main__":
    sucesso, res = classificar_transacao_com_ia("UBER TRIP", -45.90)
    print(res)