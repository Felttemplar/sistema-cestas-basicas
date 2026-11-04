import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cesta_basica.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de Produtos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            unidade TEXT NOT NULL,
            grupo_equivalencia TEXT NOT NULL
        )
    ''')
    
    # Tabela de Fornecedores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            telefone TEXT
        )
    ''')
    
    # Tabela de Cotações
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
    
    # Tabela de Tipos de Cesta
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tipos_cesta (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT
        )
    ''')
    
    # Tabela de Composição da Cesta
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
    
    # Tabela de Parâmetros Operacionais
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parametros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chave TEXT NOT NULL UNIQUE,
            valor REAL NOT NULL
        )
    ''')
    
    # Tabela de Vendas Atualizada (com Zonas, Vendedores e Tributos)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_cesta_id INTEGER NOT NULL,
            quantidade_vendida INTEGER NOT NULL,
            preco_unitario_praticado REAL NOT NULL,
            canal_venda TEXT NOT NULL,
            vendedor TEXT NOT NULL,
            zona_entrega TEXT NOT NULL,
            comissao_percentual REAL DEFAULT 0.0,
            imposto_percentual REAL DEFAULT 0.0,
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
        cursor.execute("INSERT INTO parametros (chave, valor) VALUES ('imposto_padrao', 5.0)")
        
    cestas_padrao = [
        ("Cesta Econômica (12-14 Itens)", "Cesta essencial de alimentos"),
        ("Cesta Família (20-30 Itens)", "Cesta completa familiar"),
        ("Cesta Turbinada (35-60 Itens)", "Cesta super completa"),
        ("Kit Higiene", "Essencial de higiene pessoal (7 itens)"),
        ("Kit Higiene Família", "Kit completo de higiene (12 itens)"),
        ("Sacola Limpeza 1", "Sacola essencial de limpeza (7 itens)"),
        ("Sacola Limpeza 2", "Sacola completa de limpeza (15 itens)"),
        ("Cesta Estudante", "Cesta focada em estudantes (18 itens)"),
        ("Cesta Natalina", "Cesta sazonal de fim de ano (10-16 itens)"),
        ("Cesta Natal Feliz", "Cesta premium de Natal (18 itens)")
    ]
    for nome, desc in cestas_padrao:
        cursor.execute("INSERT OR IGNORE INTO tipos_cesta (nome, descricao) VALUES (?, ?)", (nome, desc))
        
    fornecedores_padrao = [
        ("Atacadão", "Atacado"),
        ("Assaí Atacadista", "Atacado"),
        ("Supermercado Gavião", "Varejo/Atacado"),
        ("Supermercado Novo Tempo", "Varejo/Atacado"),
        ("Supermercado Nova Era", "Varejo/Atacado"),
        ("Supermercado Goiano", "Varejo/Atacado"),
        ("Distribuidora Local 1", "Distribuidora")
    ]
    for nome, tel in fornecedores_padrao:
        cursor.execute("INSERT OR IGNORE INTO fornecedores (nome, telefone) VALUES (?, ?)", (nome, tel))

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
