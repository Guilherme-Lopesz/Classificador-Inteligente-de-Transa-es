
# 📊 Giro · Classificador Inteligente de Transações

O **Giro** é uma solução inteligente para a organização de finanças pessoais e empresariais. Ele transforma arquivos de extratos bancários (CSV/TXT) – frequentemente confusos e poluídos – em dados categorizados e prontos para análise, utilizando o poder da Inteligência Artificial (**Google Gemini 1.5 Flash**) e um sistema robusto de heurísticas locais.

## 📋 Sumário

- [Visão Geral](##visão-geral)
- [Como Rodar o Projeto](##como-rodar-o-projeto)
- [Tecnologias Usadas](##tecnologias-usadas)
- [Decisões Técnicas](##decisões-técnicas)
- [O que faltou fazer](##o-que-faltou-fazer)
- [Próximos Passos](#%próximos-passos)

---

## 🎯 Visão Geral

O Giro permite que usuários façam upload de extratos bancários, recebam sugestões de categorias via IA e ajustem manualmente quando necessário. Tudo isso com foco em privacidade, performance e usabilidade.

### Funcionalidades Principais

- ✅ **Upload de arquivos CSV/TXT** com validação automática
- ✅ **Limpeza automática de dados sensíveis** (CPF, CNPJ, contas) usando regex – LGPD ready
- ✅ **Classificação híbrida**: heurísticas locais + IA (Google Gemini)
- ✅ **Processamento em segundo plano** com threads – sem travar a interface
- ✅ **Auditoria completa** de todas as alterações
- ✅ **Visualização gráfica** com Chart.js (gráfico de rosca)
- ✅ **Tema escuro persistente** (salvo no `localStorage`)

---

## 🚀 Como Rodar o Projeto

### Pré-requisitos

- Python 3.10 ou superior
- Uma **API Key do Google Gemini** (obtenha em [Google AI Studio](https://aistudio.google.com/))

### Passo a Passo

1. **Clone o repositório**
   ```bash
   git clone (https://github.com/Guilherme-Lopesz/Classificador-Inteligente-de-Transa-es)
   cd giro
   ```

2. **Crie e ative um ambiente virtual** (Opcional)
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

3. **Instale as dependências**
   ```bash
   pip install flask pandas google-genai python-dotenv
   ```

4. **Configure as variáveis de ambiente**  
   Crie um arquivo `.env` na raiz do projeto:
   ```env
   GOOGLE_API_KEY=sua_chave_aqui
   FLASK_SECRET_KEY=uma_chave_segura_para_sessoes
   ```

5. **Inicialize o banco de dados**
   ```bash
   python database.py
   ```

6. **Execute a aplicação**
   ```bash
   python app2.py
   ```

7. Acesse no navegador: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🛠 Tecnologias Usadas

| Tecnologia            | Finalidade |
|-----------------------|------------|
| Python                | Linguagem core do sistema |
| Flask                 | Framework web para roteamento e gerenciamento de sessões |
| Google Gemini 1.5 Flash | LLM para classificação contextual de descrições bancárias |
| SQLite                | Banco de dados relacional leve e portátil |
| Pandas                | Processamento e normalização de dados de arquivos CSV |
| Chart.js              | Visualização dinâmica de dados com gráficos de rosca |
| HTML5/CSS3 (Dark Mode)| Interface responsiva com persistência de tema via `localStorage` |
| `python-dotenv`       | Gerenciamento seguro de variáveis de ambiente |

---

## 🔧 Decisões Técnicas

### 1. **Privacidade e LGPD – Limpeza automática com Regex**
- **Decisão:** Utilizar expressões regulares para remover CPF, CNPJ, números de agência e conta das descrições antes de qualquer processamento.
- **Por quê:** Garantir que dados sensíveis não sejam enviados para a IA nem armazenados, atendendo a requisitos de privacidade desde a concepção.

### 2. **Arquitetura Híbrida (IA + Heurísticas)**
- **Decisão:** Implementar um sistema de fallback: primeiro tenta categorizar por regras locais (palavras‑chave); se não encontrar, chama a IA; se a IA falhar (ex.: erro 429 de cota), mantém a transação como "pendente" para revisão manual.
- **Por quê:** Evita que limites de API interrompam o fluxo do usuário e reduz custos com chamadas desnecessárias.

### 3. **Processamento Não‑Bloqueante com Threading**
- **Decisão:** Disparar a classificação por IA em uma thread separada durante o upload.
- **Por quê:** O dashboard continua responsivo enquanto a IA trabalha em segundo plano, melhorando a experiência do usuário com grandes volumes de dados.

### 4. **Auditoria Completa (Audit Log)**
- **Decisão:** Criar uma tabela `audit_log` que registra toda ação sobre transações (criação, edição, classificação automática).
- **Por quê:** Rastreabilidade total – é possível saber exatamente quem ou o que alterou cada dado e quando.

### 5. **Segurança – Hash de Senha com SHA‑256**
- **Decisão:** Utilizar SHA‑256 com requisitos de senha forte (8+ caracteres, maiúscula, caractere especial).
- **Por quê:** Solução simples e adequada para um MVP; em produção recomenda‑se trocar por bcrypt/argon2.

---

## ⚠️ O que faltou fazer

- **Suporte a OFX:** Embora planejado, o processamento de arquivos `.ofx` ainda não foi implementado.
- **Recuperação de Senha:** Fluxo de "Esqueci minha senha" não está integrado.
- **Testes Unitários:** Criar uma suíte com Pytest para validar funções de parsing e limpeza de dados.
- **Validação de Email:** Validar Email para confirmar se realmente existe

---

## 📈 Próximos Passos

- **Exportação de Relatórios:** Gerar arquivos PDF ou Excel com gastos filtrados por categoria e período.
- **Open Banking:** Conexão direta com APIs bancárias para importação automática.
- **Metas de Gastos (Budgets):** Permitir que o usuário defina limites por categoria e receba alertas.
- **Multi‑Moeda:** Suporte a transações em dólar/euro com conversão automática via API de cotação.
- **Tornar o Projeto mais escalonável com melhorias na criptografia de senha, no banco de Dados
