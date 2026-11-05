import re
import sqlite3
import unicodedata
from contextlib import closing
from pathlib import Path

DB_NAME = Path(__file__).resolve().parent.parent / "cesta_basica.db"


def normalizar_fornecedor(valor):
    texto = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode("ascii").upper()
    partes = re.sub(r"[^A-Z0-9]+", " ", texto).split()
    while partes and partes[0] in {"SUPERMERCADO", "MERCADO", "DISTRIBUIDORA"}:
        partes.pop(0)
    while partes and partes[-1] in {"ATACADISTA", "ATACADO"}:
        partes.pop()
    return " ".join(partes)


def get_connection():
    conn = sqlite3.connect(str(DB_NAME), check_same_thread=False, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def _garantir_coluna(cursor, tabela, coluna, definicao):
    atuais = {row[1] for row in cursor.execute(f"PRAGMA table_info({tabela})")}
    if coluna not in atuais:
        cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")


def init_db():
    with closing(get_connection()) as conn, conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                marca TEXT NOT NULL DEFAULT 'VARIÁVEL',
                unidade TEXT NOT NULL,
                grupo_equivalencia TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fornecedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                telefone TEXT,
                tipo TEXT,
                cidade TEXT,
                bairro TEXT,
                nome_normalizado TEXT
            )
        """)
        for coluna, definicao in (
            ("tipo", "TEXT"), ("cidade", "TEXT"), ("bairro", "TEXT"),
            ("nome_normalizado", "TEXT"),
        ):
            _garantir_coluna(cursor, "fornecedores", coluna, definicao)
        for fornecedor in cursor.execute("SELECT id, nome, nome_normalizado FROM fornecedores").fetchall():
            chave = normalizar_fornecedor(fornecedor["nome"])
            if not fornecedor["nome_normalizado"]:
                cursor.execute("UPDATE fornecedores SET nome_normalizado = ? WHERE id = ?", (chave, fornecedor["id"]))

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cotacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                fornecedor_id INTEGER NOT NULL,
                preco REAL NOT NULL CHECK (preco > 0),
                data_cotacao TEXT NOT NULL,
                marca TEXT,
                origem TEXT,
                FOREIGN KEY(produto_id) REFERENCES produtos(id),
                FOREIGN KEY(fornecedor_id) REFERENCES fornecedores(id)
            )
        """)
        _garantir_coluna(cursor, "cotacoes", "marca", "TEXT")
        _garantir_coluna(cursor, "cotacoes", "origem", "TEXT")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_lote TEXT UNIQUE,
                nome_lote TEXT,
                data_compra TEXT NOT NULL,
                fornecedor_id INTEGER,
                observacao TEXT,
                custo_total REAL NOT NULL DEFAULT 0,
                custo_total_insumos REAL NOT NULL DEFAULT 0,
                custo_embalagem REAL NOT NULL DEFAULT 0,
                frete_lote REAL NOT NULL DEFAULT 0,
                margem_lucro_perc REAL NOT NULL DEFAULT 25,
                preco_venda_calculado REAL NOT NULL DEFAULT 0,
                ativo INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(fornecedor_id) REFERENCES fornecedores(id)
            )
        """)
        for coluna, definicao in (
            ("numero_lote", "TEXT"), ("nome_lote", "TEXT"),
            ("custo_total", "REAL NOT NULL DEFAULT 0"),
            ("custo_total_insumos", "REAL NOT NULL DEFAULT 0"),
            ("fornecedor_id", "INTEGER"), ("observacao", "TEXT"),
            ("custo_embalagem", "REAL NOT NULL DEFAULT 0"),
            ("frete_lote", "REAL NOT NULL DEFAULT 0"),
            ("margem_lucro_perc", "REAL NOT NULL DEFAULT 25"),
            ("preco_venda_calculado", "REAL NOT NULL DEFAULT 0"),
            ("ativo", "INTEGER NOT NULL DEFAULT 1"),
        ):
            _garantir_coluna(cursor, "lotes", coluna, definicao)
        cursor.execute("UPDATE lotes SET nome_lote = numero_lote WHERE nome_lote IS NULL AND numero_lote IS NOT NULL")
        cursor.execute("UPDATE lotes SET custo_total = custo_total_insumos WHERE custo_total = 0 AND custo_total_insumos > 0")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS itens_lote (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id INTEGER NOT NULL,
                produto_id INTEGER NOT NULL,
                fornecedor_id INTEGER,
                cotacao_id INTEGER,
                quantidade REAL NOT NULL CHECK (quantidade > 0),
                preco_unitario REAL NOT NULL CHECK (preco_unitario >= 0),
                subtotal REAL NOT NULL DEFAULT 0,
                FOREIGN KEY(lote_id) REFERENCES lotes(id),
                FOREIGN KEY(produto_id) REFERENCES produtos(id),
                FOREIGN KEY(fornecedor_id) REFERENCES fornecedores(id),
                FOREIGN KEY(cotacao_id) REFERENCES cotacoes(id)
            )
        """)
        _garantir_coluna(cursor, "itens_lote", "subtotal", "REAL NOT NULL DEFAULT 0")
        _garantir_coluna(cursor, "itens_lote", "fornecedor_id", "INTEGER")
        _garantir_coluna(cursor, "itens_lote", "cotacao_id", "INTEGER")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes_estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                lote_id INTEGER,
                tipo TEXT NOT NULL CHECK (tipo IN ('ENTRADA', 'SAIDA', 'AJUSTE_ENTRADA', 'AJUSTE_SAIDA')),
                quantidade REAL NOT NULL CHECK (quantidade > 0),
                custo_unitario REAL,
                data_hora TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                observacao TEXT,
                FOREIGN KEY(produto_id) REFERENCES produtos(id),
                FOREIGN KEY(lote_id) REFERENCES lotes(id)
            )
        """)
        _garantir_coluna(cursor, "movimentacoes_estoque", "custo_unitario", "REAL")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tipos_cesta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS composicao_cesta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_cesta_id INTEGER NOT NULL,
                produto_id INTEGER NOT NULL,
                quantidade REAL NOT NULL CHECK (quantidade > 0),
                UNIQUE(tipo_cesta_id, produto_id),
                FOREIGN KEY(tipo_cesta_id) REFERENCES tipos_cesta(id),
                FOREIGN KEY(produto_id) REFERENCES produtos(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parametros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chave TEXT NOT NULL UNIQUE,
                valor REAL NOT NULL
            )
        """)
        for chave, valor in (("custo_embalagem", 3.50), ("frete_medio", 0.0), ("margem_lucro_padrao", 25.0), ("imposto_padrao", 0.0)):
            cursor.execute("INSERT OR IGNORE INTO parametros (chave, valor) VALUES (?, ?)", (chave, valor))

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS montagens_cesta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_cesta_id INTEGER NOT NULL,
                data_montagem TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                quantidade INTEGER NOT NULL CHECK (quantidade > 0),
                custo_produtos_unitario REAL NOT NULL,
                custo_embalagem_unitario REAL NOT NULL DEFAULT 0,
                frete_unitario REAL NOT NULL DEFAULT 0,
                margem_bruta REAL NOT NULL DEFAULT 0,
                preco_venda_sugerido REAL NOT NULL,
                observacao TEXT,
                FOREIGN KEY(tipo_cesta_id) REFERENCES tipos_cesta(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS itens_montagem (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                montagem_id INTEGER NOT NULL,
                produto_id INTEGER NOT NULL,
                quantidade_por_cesta REAL NOT NULL,
                quantidade_total REAL NOT NULL,
                custo_unitario REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY(montagem_id) REFERENCES montagens_cesta(id),
                FOREIGN KEY(produto_id) REFERENCES produtos(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vendas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_cesta_id INTEGER NOT NULL,
                quantidade_vendida INTEGER NOT NULL,
                preco_unitario_praticado REAL NOT NULL,
                canal_venda TEXT NOT NULL,
                vendedor TEXT DEFAULT 'Venda Direta',
                zona_entrega TEXT DEFAULT 'Boa Vista',
                taxa_canal_percentual REAL DEFAULT 0,
                comissao_percentual REAL DEFAULT 0,
                imposto_percentual REAL DEFAULT 0,
                data_venda TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(tipo_cesta_id) REFERENCES tipos_cesta(id)
            )
        """)

        # Nomes normalizados impedem criar o mesmo mercado com/sem prefixo e acentos diferentes.
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_fornecedor_nome_normalizado ON fornecedores(nome_normalizado)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_produtos_nome_unidade_unique ON produtos(upper(trim(nome)), CASE WHEN upper(trim(unidade)) IN ('UN','UND','UNID','UNIDADE') THEN 'UN' WHEN upper(trim(unidade)) IN ('PC','PCT','PACOTE') THEN 'PC' WHEN upper(trim(unidade)) IN ('FR','FRASCO') THEN 'FR' WHEN upper(trim(unidade)) IN ('LT','L','LITRO') THEN 'LT' WHEN upper(trim(unidade)) IN ('G','GR','GRAMA','GRAMAS') THEN 'G' WHEN upper(trim(unidade)) IN ('KG','QUILOGRAMA','QUILOGRAMAS') THEN 'KG' ELSE upper(trim(unidade)) END)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cotacoes_produto_preco ON cotacoes(produto_id, preco, data_cotacao)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cotacoes_fornecedor_data ON cotacoes(fornecedor_id, data_cotacao)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movimentos_produto_data ON movimentacoes_estoque(produto_id, data_hora)")

        if cursor.execute("SELECT COUNT(*) FROM tipos_cesta").fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO tipos_cesta (nome, descricao) VALUES (?, ?)",
                [("Cesta Econômica", "Cesta para revenda"), ("Cesta Família", "Cesta completa"), ("Kit Higiene", "Itens de higiene"), ("Kit Limpeza", "Itens de limpeza")],
            )
