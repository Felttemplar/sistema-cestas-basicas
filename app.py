import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from core.database import init_db, get_connection
from core.engine import calcular_custo_cesta, obter_parametros

init_db()
st.set_page_config(page_title="Cestas Bom Dia - Boa Vista", page_icon="🛒", layout="wide")
st.title("🛒 Cestas Bom Dia - Montagem Personalizada & Precificação Pós-Composição")

TAXAS_CANAL = {"Online - Instagram": 0.0, "Online - Pigz": 10.0, "Online - iFood": 12.0, "Online - Zé Delivery": 8.0, "Presencial - Venda Física": 0.0}

menu = st.sidebar.radio("Navegabilidade:", ["🧩 Montagem & Precificação da Cesta", "📦 Cadastrar Produtos & Marcas", "🏭 Fornecedores & Preços", "📊 Cotações & Histórico"])
params = obter_parametros()

if menu == "🧩 Montagem & Precificação da Cesta":
    st.header("🧩 Montagem Personalizada do Kit & Cálculo de Custo")
    conn = get_connection()
    tipos_cesta = pd.read_sql_query("SELECT id, nome FROM tipos_cesta", conn)
    produtos_df = pd.read_sql_query("SELECT id, (nome || ' - ' || marca || ' [' || unidade || ']') AS desc_item FROM produtos", conn)
    conn.close()
    
    if tipos_cesta.empty:
        st.warning("Cadastre um modelo de cesta.")
    else:
        c1, c2 = st.columns([1, 2])
        with c1:
            cesta_esc = st.selectbox("Kit Alvo", tipos_cesta['nome'])
            cesta_id = int(tipos_cesta[tipos_cesta['nome'] == cesta_esc]['id'].values[0])
            with st.form("form_add"):
                p_sel = st.selectbox("Produto/Marca", produtos_df['id'], format_func=lambda x: produtos_df[produtos_df['id'] == x]['desc_item'].values[0])
                qtd = st.number_input("Quantidade", value=1.0, step=1.0)
                if st.form_submit_button("➕ Adicionar à Cesta"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO composicao_cesta (tipo_cesta_id, produto_id, quantidade) VALUES (?, ?, ?)", (cesta_id, p_sel, qtd))
                    conn.commit()
                    conn.close()
                    st.success("Item adicionado!")
                    st.rerun()
        with c2:
            st.subheader(f"Custo Calculado: {cesta_esc}")
            m_l = st.slider("Margem de Lucro (%)", 5.0, 60.0, 25.0)
            df_itens, c_ins, c_tot, v_luc, p_sug = calcular_custo_cesta(cesta_id, m_l)
            if df_itens.empty:
                st.info("Nenhum item montado nesta cesta ainda.")
            else:
                st.metric("Custo Total", f"R$ {c_tot:.2f}", f"Lucro: R$ {v_luc:.2f}")
                st.dataframe(df_itens[['produto', 'quantidade', 'unidade', 'menor_preco', 'fornecedor', 'subtotal']], use_container_width=True)

elif menu == "📦 Cadastrar Produtos & Marcas":
    st.header("📦 Cadastro de Produtos e Marcas")
    with st.form("form_prod"):
        n = st.text_input("Nome do Produto")
        m = st.text_input("Marca")
        u = st.selectbox("Unidade", ["KG", "PCT", "UN", "FR", "LT", "CX"])
        g = st.text_input("Grupo/Categoria")
        if st.form_submit_button("Salvar"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)", (n, m, u, g))
            conn.commit()
            conn.close()
            st.success("Cadastrado!")
            st.rerun()

elif menu == "🏭 Fornecedores & Preços":
    st.header("🏭 Cotações por Atacadista")
    conn = get_connection()
    prods = pd.read_sql_query("SELECT id, (nome || ' - ' || marca) AS item FROM produtos", conn)
    fornecs = pd.read_sql_query("SELECT id, nome FROM fornecedores", conn)
    conn.close()
    if not prods.empty and not fornecs.empty:
        with st.form("form_cot"):
            p = st.selectbox("Produto", prods['id'], format_func=lambda x: prods[prods['id'] == x]['item'].values[0])
            f = st.selectbox("Atacadista", fornecs['id'], format_func=lambda x: fornecs[fornecs['id'] == x]['nome'].values[0])
            pr = st.number_input("Preço R$", min_value=0.01)
            dt = st.date_input("Data", value=datetime.now())
            if st.form_submit_button("Salvar Cotação"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, ?)", (p, f, pr, dt.strftime("%Y-%m-%d")))
                conn.commit()
                conn.close()
                st.success("Salvo!")
                st.rerun()

elif menu == "📊 Cotações & Histórico":
    st.header("📊 Histórico Temporal")
    conn = get_connection()
    df = pd.read_sql_query("SELECT c.data_cotacao, (p.nome || ' - ' || p.marca) AS prod, f.nome AS atac, c.preco FROM cotacoes c JOIN produtos p ON c.produto_id=p.id JOIN fornecedores f ON c.fornecedor_id=f.id", conn)
    conn.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sem cotações registradas.")
