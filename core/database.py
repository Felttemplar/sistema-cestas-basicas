import sqlite3
import os
import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "cesta_basica.db")
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "..", "CESTA DA FAMILIA bom dia (3).xlsx")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Criação das tabelas
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
    _importar_planilha_automatica()

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
        ("Nova Era", "Varejo"),
        ("Goiano", "Varejo"),
        ("Aguiar", "Varejo"),
        ("Distribuidora 1", "Distribuidora")
    ]
    for n, t in fornecedores: 
        cursor.execute("INSERT OR IGNORE INTO fornecedores (nome, telefone) VALUES (?, ?)", (n, t))
        
    conn.commit()
    conn.close()

def _importar_planilha_automatica():
    if not os.path.exists(EXCEL_PATH):
        return
        
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        df = pd.read_excel(EXCEL_PATH, sheet_name="CONCORRENTES COTAÇÃO", header=4)
        atacadistas_map = {
            5: "Assaí Atacadista",
            7: "Atacadão",
            11: "Supermercado Gavião",
            13: "Novo Tempo",
            17: "Nova Era",
            19: "Goiano",
            21: "Aguiar",
            23: "Distribuidora 1"
        }
        
        for idx, row in df.iterrows():
            if len(row) < 3:
                continue
            nome_prod = row.iloc[2]
            unidade = row.iloc[3]
            
            if pd.isna(nome_prod) or str(nome_prod).strip() == "" or str(nome_prod).upper() in ["ALIMENTO", "HIGIENE", "LIMPEZA"]:
                continue
                
            unidade_str = str(unidade).strip() if not pd.isna(unidade) else "UN"
            marca_principal = str(row.iloc[4]).strip() if not pd.isna(row.iloc[4]) else "Geral"
            nome_clean = str(nome_prod).strip()
            
            cursor.execute(
                "INSERT OR IGNORE INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)",
                (nome_clean, marca_principal, unidade_str, nome_clean)
            )
            conn.commit()
            
            cursor.execute("SELECT id FROM produtos WHERE nome = ? AND marca = ?", (nome_clean, marca_principal))
            p_res = cursor.fetchone()
            if not p_res:
                continue
            produto_db_id = p_res[0]
            
            for col_idx, atac_nome in atacadistas_map.items():
                if col_idx < len(row):
                    preco_val = row.iloc[col_idx]
                    if not pd.isna(preco_val) and isinstance(preco_val, (int, float)) and preco_val > 0:
                        cursor.execute("SELECT id FROM fornecedores WHERE nome = ?", (atac_nome,))
                        f_res = cursor.fetchone()
                        if f_res:
                            forn_id = f_res[0]
                            cursor.execute(
                                "INSERT OR IGNORE INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, date('now'))",
                                (produto_db_id, forn_id, float(preco_val))
                            )
        conn.commit()
    except Exception as e:
        print(f"Erro na importação automática da planilha: {e}")
    finally:
        conn.close()
