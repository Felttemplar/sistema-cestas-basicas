import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cesta_basica.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Criar tabelas se não existirem
    cursor.execute("CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, marca TEXT DEFAULT 'Geral', unidade TEXT NOT NULL, grupo_equivalencia TEXT NOT NULL, estoque_atual REAL DEFAULT 100.0, estoque_minimo REAL DEFAULT 10.0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS fornecedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, telefone TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS cotacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER NOT NULL, fornecedor_id INTEGER NOT NULL, preco REAL NOT NULL, data_cotacao TEXT NOT NULL, FOREIGN KEY (produto_id) REFERENCES produtos (id), FOREIGN KEY (fornecedor_id) REFERENCES fornecedores (id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS tipos_cesta (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, descricao TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS composicao_cesta (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo_cesta_id INTEGER NOT NULL, produto_id INTEGER NOT NULL, quantidade REAL NOT NULL, FOREIGN KEY (tipo_cesta_id) REFERENCES tipos_cesta (id), FOREIGN KEY (produto_id) REFERENCES produtos (id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS parametros (id INTEGER PRIMARY KEY AUTOINCREMENT, chave TEXT NOT NULL UNIQUE, valor REAL NOT NULL)")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_lote TEXT NOT NULL UNIQUE,
            data_compra TEXT NOT NULL,
            fornecedor_id INTEGER,
            observacao TEXT,
            custo_total_insumos REAL DEFAULT 0.0,
            custo_embalagem REAL DEFAULT 3.50,
            frete_lote REAL DEFAULT 0.0,
            margem_lucro_perc REAL DEFAULT 25.0,
            ativo INTEGER DEFAULT 1,
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores (id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_lote (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lote_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade REAL NOT NULL,
            preco_unitario REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (lote_id) REFERENCES lotes (id),
            FOREIGN KEY (produto_id) REFERENCES produtos (id)
        )
    """)

    conn.commit()
    conn.close()
    _seed_initial_data()

def _seed_initial_data():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM parametros")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO parametros (chave, valor) VALUES ('custo_embalagem', 3.50)")
        cursor.execute("INSERT INTO parametros (chave, valor) VALUES ('frete_medio', 5.00)")
        cursor.execute("INSERT INTO parametros (chave, valor) VALUES ('margem_lucro_padrao', 25.0)")
    
    cestas = [
        ("Cesta Econômica (12-14 Itens)", "Essencial"), 
        ("Cesta Família (20-30 Itens)", "Completa"), 
        ("Cesta Turbinada (35-60 Itens)", "Super"),
        ("Kit Higiene", "Higiene"),
        ("Kit Higiene Família", "Higiene Família"),
        ("Sacola Limpeza 1", "Limpeza 1"),
        ("Sacola Limpeza 2", "Limpeza 2")
    ]
    for n, d in cestas: 
        cursor.execute("INSERT OR IGNORE INTO tipos_cesta (nome, descricao) VALUES (?, ?)", (n, d))
    
    fornecedores = [
        ("Assaí Atacadista", "Atacado"), 
        ("Atacadão", "Atacado"), 
        ("Supermercado Gavião", "Varejo"),
        ("Novo Tempo", "Varejo"),
        ("Nova Era", "Varejo")
    ]
    for n, t in fornecedores: 
        cursor.execute("INSERT OR IGNORE INTO fornecedores (nome, telefone) VALUES (?, ?)", (n, t))

    # Popular produtos padrões se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        produtos_iniciais = [
            ("ARROZ 1KG", "PRATO CHIC", "KG", "Alimento"),
            ("FEIJÃO 1KG", "KICALDO", "KG", "Alimento"),
            ("AÇÚCAR 1KG", "CRISTAL SONORA", "KG", "Alimento"),
            ("FARINHA", "MANDIOCA DONA", "KG", "Alimento"),
            ("TRIGO 1KG", "TRIGOLAR", "KG", "Alimento"),
            ("ÓLEO 900ML", "SERRA VERDE", "FR", "Alimento"),
            ("CAFÉ 250G", "PILÃO", "PCT", "Alimento"),
            ("MACARRÃO 400G", "BOM SABOR", "PCT", "Alimento")
        ]
        for p_nome, p_marca, p_un, p_grupo in produtos_iniciais:
            cursor.execute("INSERT INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)", (p_nome, p_marca, p_un, p_grupo))

    conn.commit()
    conn.close()
