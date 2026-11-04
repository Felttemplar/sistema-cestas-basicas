import pandas as pd
from core.database import get_connection

def calcular_custo_cesta(tipo_cesta_id: int, margem_lucro: float, custo_embalagem: float, frete: float):
    conn = get_connection()
    
    # Busca os itens da cesta e agrupa por grupo de equivalência para pegar sempre o mais barato entre os substitutos
    query = '''
        SELECT 
            p.id AS produto_id,
            p.nome AS produto,
            p.unidade,
            p.grupo_equivalencia,
            cc.quantidade,
            MIN(c.preco) AS menor_preco,
            f.nome AS fornecedor
        FROM composicao_cesta cc
        JOIN produtos p ON cc.produto_id = p.id
        LEFT JOIN cotacoes c ON p.id = c.produto_id
        LEFT JOIN fornecedores f ON c.fornecedor_id = f.id
        WHERE cc.tipo_cesta_id = ?
        GROUP BY p.grupo_equivalencia, cc.quantidade
    '''
    
    df = pd.read_sql_query(query, conn, params=(tipo_cesta_id,))
    conn.close()
    
    if df.empty or df['menor_preco'].isnull().all():
        return pd.DataFrame(), 0.0, 0.0, 0.0, 0.0

    df['subtotal'] = df['quantidade'] * df['menor_preco']
    custo_insumos = df['subtotal'].sum()
    
    custo_total = custo_insumos + custo_embalagem + frete
    valor_lucro = custo_total * (margem_lucro / 100.0)
    preco_venda = custo_total + valor_lucro
    
    return df, custo_insumos, custo_total, valor_lucro, preco_venda

def obter_parametros():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chave, valor FROM parametros")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def salvar_parametro(chave: str, valor: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO parametros (chave, valor) VALUES (?, ?)", (chave, valor))
    conn.commit()
    conn.close()