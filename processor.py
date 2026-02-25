import sqlite3 as lite
import time
from ai_agent import classificar_transacao_com_ia

def connectar_bd():
    con = lite.connect('Classificador Inteligente de Transações.db', timeout=15)
    con.row_factory = lite.Row  
    return con

def aplicar_regras_automaticas(user_id):
    con = connectar_bd()
    cur = con.cursor()

    regras = cur.execute("SELECT * FROM rules WHERE user_id = ?", (user_id,)).fetchall()
    transacoes = cur.execute("SELECT * FROM transactions WHERE user_id = ? AND status = 'pending'", (user_id,)).fetchall()

    for t in transacoes:
        for r in regras:
            if r['keyword'].lower() in t['description'].lower():
                cur.execute('''
                    UPDATE transactions 
                    SET suggested_category = ?, suggested_confidence = 100
                    WHERE transaction_id = ?
                ''', (r['category'], t['transaction_id']))

                cur.execute('''
                    INSERT INTO audit_log (transaction_id, user_id, action, new_category, source)
                    VALUES (?, ?, 'rule_applied', ?, 'rule')
                ''', (t['transaction_id'], user_id, r['category']))
                break  
    con.commit()
    con.close()

def processar_com_ia(user_id):
    con = connectar_bd()
    cur = con.cursor()

    try:
        # Pega apenas quem não tem categoria ainda (as novas)
        transacoes = cur.execute("SELECT * FROM transactions WHERE user_id = ? AND status = 'pending' AND suggested_category IS NULL", (user_id,)).fetchall()

        for t in transacoes:
            sucesso, resposta_ia = classificar_transacao_com_ia(t['description'], t['amount'])

            if sucesso and resposta_ia:
                categoria_sugerida = resposta_ia.get('category')
                # Se a IA por algum motivo devolver None vazio, forçamos 'Outros'
                if not categoria_sugerida:
                    categoria_sugerida = 'Outros'
                confianca = resposta_ia.get('confidence', 0)
            else:
                categoria_sugerida = "Outros"
                confianca = 0
                
            cur.execute('''
                UPDATE transactions 
                SET suggested_category = ?, suggested_confidence = ?
                WHERE transaction_id = ?
            ''', (categoria_sugerida, confianca, t['transaction_id']))

            cur.execute('''
                INSERT INTO audit_log (transaction_id, user_id, action, new_category, source)
                VALUES (?, ?, 'ai_suggested', ?, 'ai')
            ''', (t['transaction_id'], user_id, categoria_sugerida))
            
            # Salva no banco passo a passo
            con.commit() 
            
            # Pausa vital para não levar ban gratuito da API
            time.sleep(3.5)
            
    except Exception as e:
        print(f"Erro na Thread da IA: {e}")
    finally:
        # Garante que a conexão será fechada de qualquer forma
        con.close()