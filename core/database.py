import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cesta_basica.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, marca TEXT DEFAULT 'Geral', unidade TEXT NOT NULL, grupo_equivalencia TEXT NOT NULL, estoque_atual REAL DEFAULT 100.0, estoque_minimo REAL DEFAULT 10.0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS fornecedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, telefone TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS cotacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, produto_id INTEGER NOT NULL, fornecedor_id INTEGER NOT NULL, preco REAL NOT NULL, data_cotacao TEXT NOT NULL, FOREIGN KEY (produto_id) REFERENCES produtos (id), FOREIGN KEY (fornecedor_id) REFERENCES fornecedores (id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS tipos_cesta (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, descricao TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS composicao_cesta (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo_cesta_id INTEGER NOT NULL, produto_id INTEGER NOT NULL, quantidade REAL NOT NULL, FOREIGN KEY (tipo_cesta_id) REFERENCES tipos_cesta (id), FOREIGN KEY (produto_id) REFERENCES produtos (id))")
    cursor.execute("CREATE TABLE IF NOT EXISTS parametros (id INTEGER PRIMARY KEY AUTOINCREMENT, chave TEXT NOT NULL UNIQUE, valor REAL NOT NULL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS vendas (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo_cesta_id INTEGER NOT NULL, quantidade_vendida INTEGER NOT NULL, preco_unitario_praticado REAL NOT NULL, canal_venda TEXT NOT NULL, vendedor TEXT DEFAULT 'Venda Direta', zona_entrega TEXT DEFAULT 'Zona 1 - Centro', taxa_canal_percentual REAL DEFAULT 0.0, comissao_percentual REAL DEFAULT 0.0, imposto_percentual REAL DEFAULT 5.0, data_venda TEXT NOT NULL, FOREIGN KEY (tipo_cesta_id) REFERENCES tipos_cesta (id))")
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
        cursor.execute("INSERT INTO parametros (chave, valor) VALUES ('imposto_padrao', 5.0)")
    
    cestas = [
        ("Cesta Econômica (12-14 Itens)", "Essencial"), 
        ("Cesta Família (20-30 Itens)", "Completa"), 
        ("Cesta Turbinada (35-60 Itens)", "Super"), 
        ("Kit Higiene", "Higiene"), 
        ("Kit Higiene Família", "Higiene Família"), 
        ("Sacola Limpeza 1", "Limpeza 1"), 
        ("Sacola Limpeza 2", "Limpeza 2"), 
        ("Cesta Estudante", "Estudante"), 
        ("Cesta Natalina", "Natalina"), 
        ("Cesta Natal Feliz", "Natal Feliz")
    ]
    for n, d in cestas: 
        cursor.execute("INSERT OR IGNORE INTO tipos_cesta (nome, descricao) VALUES (?, ?)", (n, d))
    
    fornecedores = [
        ("Assaí Atacadista", "Atacado"), 
        ("Atacadão", "Atacado"), 
        ("Supermercado Gavião", "Varejo"), 
        ("Supermercado Novo Tempo", "Varejo"), 
        ("Supermercado Nova Era", "Varejo"), 
        ("Supermercado Goiano", "Varejo"), 
        ("Distribuidora Local 1", "Distribuidora")
    ]
    for n, t in fornecedores: 
        cursor.execute("INSERT OR IGNORE INTO fornecedores (nome, telefone) VALUES (?, ?)", (n, t))

    # Popular produtos padrão e cotações se estiver vazio
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        produtos_iniciais = [
            ("ARROZ 1KG", "PRATO CHIC", "KG", "Arroz"),
            ("FEIJÃO 1KG", "KICALDO", "KG", "Feijão"),
            ("AÇUCAR 1KG", "CRISTAL SONORA", "KG", "Açúcar"),
            ("FARINHA", "MANDIOCA DONA", "KG", "Farinha"),
            ("TRIGO 1KG", "TRIGOLAR", "KG", "Trigo"),
            ("OLEO 900ML", "SERRA VERDE", "FR", "Óleo")
        ]
        for p_nome, p_marca, p_un, p_grupo in produtos_iniciais:
            cursor.execute("INSERT INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)", (p_nome, p_marca, p_un, p_grupo))
        
        # Adicionar cotações padrão para espelhar a planilha
        cursor.execute("SELECT id, nome FROM produtos")
        prods = cursor.fetchall()
        cursor.execute("SELECT id, nome FROM fornecedores")
        fornecs = cursor.fetchall()
        
        for p_id, p_nome in prods:
            for f_id, f_name in fornecs:
                preco_ex = 4.50 if "ASSAL" in f_name.upper() or "ASSAÍ" in f_name.upper() else 5.20
                cursor.execute("INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, date('now'))", (p_id, f_id, preco_ex))

    conn.commit()
    conn.close()

def deletar_fornecedor(fornecedor_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cotacoes WHERE fornecedor_id = ?", (fornecedor_id,))
    cursor.execute("DELETE FROM fornecedores WHERE id = ?", (fornecedor_id,))
    conn.commit()
    conn.close()
