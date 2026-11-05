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
    if margem_lucro_perc < 0 or margem_lucro_perc >= 100:
        raise ValueError("A margem bruta deve estar entre 0% e menos de 100%.")
    conn = get_connection()
    query_comp = '''SELECT cc.produto_id, p.nome AS produto, p.marca, p.grupo_equivalencia, p.unidade, cc.quantidade FROM composicao_cesta cc JOIN produtos p ON cc.produto_id = p.id WHERE cc.tipo_cesta_id = ?'''
    df_comp = pd.read_sql_query(query_comp, conn, params=(tipo_cesta_id,))
    if df_comp.empty:
        conn.close()
        return pd.DataFrame(), 0.0, 0.0, 0.0, 0.0

    detalhes_itens = []
    custo_total_insumos = 0.0
    for idx, row in df_comp.iterrows():
        prod_id = row['produto_id']
        qtd = row['quantidade']
        cursor = conn.cursor()
        cursor.execute("SELECT c.preco, f.nome FROM cotacoes c JOIN fornecedores f ON c.fornecedor_id = f.id WHERE c.produto_id = ? AND c.id = (SELECT c2.id FROM cotacoes c2 WHERE c2.produto_id = c.produto_id AND c2.fornecedor_id = c.fornecedor_id ORDER BY c2.data_cotacao DESC, c2.id DESC LIMIT 1) ORDER BY c.preco ASC, c.data_cotacao DESC, c.id DESC LIMIT 1", (prod_id,))
        res = cursor.fetchone()
        if not res:
            conn.close()
            raise ValueError(f"O produto {row['produto']} não possui cotação para calcular o custo da cesta.")
        menor_preco = res[0]
        atacadista = res[1]
        subtotal = menor_preco * qtd
        custo_total_insumos += subtotal
        detalhes_itens.append({"produto_id": prod_id, "produto": f"{row['produto']} ({row['marca']})", "grupo_equivalencia": row['grupo_equivalencia'], "quantidade": qtd, "unidade": row['unidade'], "menor_preco": menor_preco, "fornecedor": atacadista, "subtotal": subtotal})
    conn.close()
    df_resultado = pd.DataFrame(detalhes_itens)
    custo_total = custo_total_insumos + custo_embalagem + frete_rateado
    preco_venda_sugerido = custo_total / (1.0 - margem_lucro_perc / 100.0)
    valor_lucro = preco_venda_sugerido - custo_total
    return df_resultado, custo_total_insumos, custo_total, valor_lucro, preco_venda_sugerido
