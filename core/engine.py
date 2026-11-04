import pandas as pd
from core.database import get_connection

def obter_parametros():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT chave, valor FROM parametros")
    rows = cursor.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

def calcular_custo_cesta(tipo_cesta_id, margem_lucro_perc=25.0, custo_embalagem=3.50, frete_rateado=5.00):
    conn = get_connection()
    query_comp = '''SELECT cc.produto_id, p.nome AS produto, p.marca, p.grupo_equivalencia, p.unidade, cc.quantidade FROM composicao_cesta cc JOIN produtos p ON cc.produto_id = p.id WHERE cc.tipo_cesta_id = ?'''
    df_comp = pd.read_sql_query(query_comp, conn, params=(tipo_cesta_id,))
    if df_comp.empty:
        conn.close()
        return pd.DataFrame(), 0.0, (custo_embalagem + frete_rateado), 0.0, 0.0
    
    detalhes_itens = []
    custo_total_insumos = 0.0
    for idx, row in df_comp.iterrows():
        prod_id = row['produto_id']
        qtd = row['quantidade']
        cursor = conn.cursor()
        cursor.execute("SELECT c.preco, f.nome FROM cotacoes c JOIN fornecedores f ON c.fornecedor_id = f.id WHERE c.produto_id = ? ORDER BY c.preco ASC, c.data_cotacao DESC LIMIT 1", (prod_id,))
        res = cursor.fetchone()
        menor_preco = res[0] if res else 0.0
        atacadista = res[1] if res else "Sem cotação"
        subtotal = menor_preco * qtd
        custo_total_insumos += subtotal
        detalhes_itens.append({"produto_id": prod_id, "produto": f"{row['produto']} ({row['marca']})", "grupo_equivalencia": row['grupo_equivalencia'], "quantidade": qtd, "unidade": row['unidade'], "menor_preco": menor_preco, "fornecedor": atacadista, "subtotal": subtotal})
    conn.close()
    df_resultado = pd.DataFrame(detalhes_itens)
    custo_total = custo_total_insumos + custo_embalagem + frete_rateado
    valor_lucro = custo_total * (margem_lucro_perc / 100.0)
    preco_venda_sugerido = custo_total + valor_lucro
    return df_resultado, custo_total_insumos, custo_total, valor_lucro, preco_venda_sugerido
