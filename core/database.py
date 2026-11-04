import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cesta_basica.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            unidade TEXT NOT NULL,
            grupo_equivalencia TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            telefone TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cotacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            fornecedor_id INTEGER NOT NULL,
            preco REAL NOT NULL,
            data_cotacao TEXT NOT NULL,
            FOREIGN KEY (produto_id) REFERENCES produtos (id),
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tipos_cesta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS composicao_cesta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_cesta_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade REAL NOT NULL,
            FOREIGN KEY (tipo_cesta_id) REFERENCES tipos_cesta (id),
            FOREIGN KEY (produto_id) REFERENCES produtos (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parametros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chave TEXT NOT NULL UNIQUE,
            valor REAL NOT NULL
        )
    ''')
    
    # Nova tabela para Registro de Vendas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_cesta_id INTEGER NOT NULL,
            quantidade_vendida INTEGER NOT NULL,
            preco_unitario_praticado REAL NOT NULL,
            canal_venda TEXT NOT NULL,
            data_venda TEXT NOT NULL,
            FOREIGN KEY (tipo_cesta_id) REFERENCES tipos_cesta (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    _seed_default_data()

def _seed_default_data():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM parametros")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO parametros (chave, valor) VALUES ('custo_embalagem', 3.50)")
        cursor.execute("INSERT INTO parametros (chave, valor) VALUES ('frete_medio', 5.00)")
        cursor.execute("INSERT INTO parametros (chave, valor) VALUES ('margem_lucro_padrao', 25.0)")
        
    cestas_padrao = [
        ("Cesta Básica 14 Itens", "Cesta econômica essencial"),
        ("Cesta Básica 23 Itens", "Cesta completa familiar"),
        ("Kit Higiene", "Itens de higiene pessoal"),
        ("Kit Limpeza", "Itens de limpeza doméstica")
    ]
    for nome, desc in cestas_padrao:
        cursor.execute("INSERT OR IGNORE INTO tipos_cesta (nome, descricao) VALUES (?, ?)", (nome, desc))
        
    conn.commit()
    conn.close()

def deletar_fornecedor(fornecedor_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cotacoes WHERE fornecedor_id = ?", (fornecedor_id,))
    cursor.execute("DELETE FROM fornecedores WHERE id = ?", (fornecedor_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
