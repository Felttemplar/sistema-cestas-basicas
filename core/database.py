import sqlite3
import os

DB_NAME = "cestas.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            marca TEXT NOT NULL,
            unidade TEXT NOT NULL,
            grupo_equivalencia TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cotacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER,
            fornecedor_id INTEGER,
            preco REAL,
            data_cotacao TEXT,
            FOREIGN KEY(produto_id) REFERENCES produtos(id),
            FOREIGN KEY(fornecedor_id) REFERENCES fornecedores(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_lote TEXT,
            data_compra TEXT,
            custo_total REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS itens_lote (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id INTEGER,
            produto_id INTEGER,
            quantidade REAL,
            preco_unitario REAL,
            FOREIGN KEY(lote_id) REFERENCES lotes(id),
            FOREIGN KEY(produto_id) REFERENCES produtos(id)
        )
    ''')
    
    fornecedores_iniciais = [
        "Assaí Atacadista", "Atacadão", "Supermercado Gavião", 
        "Novo Tempo", "Nova Era", "Goiano", "Aguiar", "Distribuidora 1"
    ]
    for f in fornecedores_iniciais:
        cursor.execute("INSERT OR IGNORE INTO fornecedores (nome) VALUES (?)", (f,))
        
    conn.commit()
    conn.close()
