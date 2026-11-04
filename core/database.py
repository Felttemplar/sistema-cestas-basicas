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
    
    # Auto-seed: se a tabela produtos estiver vazia, insere a base padrão imediatamente
    cursor.execute("SELECT COUNT(*) FROM produtos")
    if cursor.fetchone()[0] == 0:
        produtos_iniciais = [
            ("ARROZ 1KG", "PRATO CHIC", "KG", "ALIMENTO"),
            ("FEIJÃO 1KG", "KICALDO", "KG", "ALIMENTO"),
            ("AÇUCAR 1KG", "CRISTAL SONORA", "KG", "ALIMENTO"),
            ("FARINHA MANDIOCA", "DONA", "KG", "ALIMENTO"),
            ("TRIGO 1KG", "FINNA", "KG", "ALIMENTO"),
            ("OLEO 900ML", "SERRA VERDE", "FR", "ALIMENTO"),
            ("SAL 1KG", "RN", "KG", "ALIMENTO"),
            ("MACARRÃO ESPAG. 400G", "BOM SABOR", "PC", "ALIMENTO"),
            ("MOLHO TOMATE 300G", "BOM SABOR", "SC/G", "ALIMENTO"),
            ("VINAGRE 500ML", "VIRROSA", "FR", "ALIMENTO"),
            ("CAFE 250GR", "PILÃO", "PC", "ALIMENTO"),
            ("SARDINHA 125G", "PALMEIRA", "LT", "ALIMENTO"),
            ("BOLACHA DOCE RECHEADA", "TRIGOLIN", "PC", "ALIMENTO"),
            ("BISCOITO SALGADO CREM", "RACHEIRO", "PC", "ALIMENTO"),
            ("COMPOSTO LACTEO 400G", "PURIBON", "PC", "ALIMENTO"),
            ("FLOCÃO 500GR", "LIVRE FLOCOS", "GR", "ALIMENTO"),
            ("SELETA LEGUMES 170G", "PREDILECTA", "LT", "ALIMENTO"),
            ("ACHOCOLATADO 200GR", "APITI POWER", "PC", "ALIMENTO"),
            ("MARGARINA 250G", "PRIMOR", "UN", "ALIMENTO"),
            ("MARGARINA 500G", "PRIMOR", "UN", "ALIMENTO"),
            ("PÃO FORMA 450G", "PÃES DELÍCIA", "UN", "ALIMENTO"),
            ("PASTA DE DENTES 70GR", "EVEN", "UN", "HIGIENE"),
            ("SABONETE 80GR", "FRANCIS", "UN", "HIGIENE"),
            ("PAPEL HIGIÊNICO 4UND", "GIRASOL", "UN", "HIGIENE"),
            ("ESCOVA DE DENTES", "CONDOR", "UN", "HIGIENE"),
            ("FIO DENTAL", "DENTRAT", "UN", "HIGIENE"),
            ("DESODORANTE NEUTRO", "ABOVE", "UN", "HIGIENE"),
            ("ÁGUA SANITÁRIA 1 LT", "BRINORT", "LT", "LIMPEZA"),
            ("DESINFETANTE 2LT", "BRINORT", "LT", "LIMPEZA"),
            ("SABÃO EM BARRA 450G", "MULTIUSO", "UN", "LIMPEZA"),
            ("SABÃO EM PÓ 400GR", "ABSOLUTO", "UN", "LIMPEZA"),
            ("AMACIANTE 2LT", "BRINORT", "LT", "LIMPEZA"),
            ("DETERGENTE 500ML", "BRILUX", "LT", "LIMPEZA")
        ]
        
        for p_nome, p_marca, p_unidade, p_grupo in produtos_iniciais:
            cursor.execute(
                "INSERT INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)",
                (p_nome, p_marca, p_unidade, p_grupo)
            )
            prod_id = cursor.lastrowid
            
            # Inserta cotações de exemplo para Assaí e Atacadão
            cursor.execute("SELECT id FROM fornecedores WHERE nome = 'Assaí Atacadista'")
            assai = cursor.fetchone()
            if assai:
                cursor.execute("INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, date('now'))", (prod_id, assai[0], 4.50))
                
            cursor.execute("SELECT id FROM fornecedores WHERE nome = 'Atacadão'")
            atacadão = cursor.fetchone()
            if atacadão:
                cursor.execute("INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, date('now'))", (prod_id, atacadão[0], 4.20))
                
        conn.commit()
    conn.close()
