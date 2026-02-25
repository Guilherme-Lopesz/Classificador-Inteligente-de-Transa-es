# ========== IMPORT ==========
import sqlite3 as lite

# ========== FUNÇÃO PRINCIPAL ==========
def inicializar_banco():
    # Conecta ao banco (cria se não existir)
    con = lite.connect('Classificador Inteligente de Transações.db')
    cur = con.cursor()

    # ========== TABELA USERS ==========
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')

    # ========== TABELA TRANSACTIONS ==========
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            suggested_category TEXT,
            suggested_confidence REAL,
            confirmed_category TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # ========== TABELA RULES ==========
    cur.execute('''
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            category TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # ========== TABELA AUDIT_LOG ==========
    cur.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            previous_category TEXT,
            new_category TEXT,
            source TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Confirma e fecha
    con.commit()
    con.close()
    print("Base de dados inicializada com sucesso!")

if __name__ == "__main__":
    inicializar_banco()