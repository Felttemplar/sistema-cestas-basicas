import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from core.database import init_db, get_connection
from core.engine import calcular_custo_cesta, obter_parametros

init_db()
st.set_page_config(page_title="Cestas Bom Dia - Boa Vista", page_icon="🛒", layout="wide")
st.title("🛒 Cestas Bom Dia - Gestão Operacional & Precificação")

# Navegação organizada na ordem exata solicitada
menu = st.sidebar.radio("Navegabilidade:", [
    "📦 Cadastrar Produtos & Marcas", 
    "🏭 Fornecedores & Preços", 
    "📊 Cotações & Histórico",
    "🧩 Montagem & Precificação da Cesta"
])
params = obter_parametros()

# 1. CADASTRAR PRODUTOS & MARCAS
if menu == "📦 Cadastrar Produtos & Marcas":
    st.header("📦 Cadastro de Produtos e Marcas")
    st.markdown("Cadastre os insumos, alimentos, itens de higiene e limpeza especificando suas marcas e unidades.")
    
    with st.form("form_prod"):
        n = st.text_input("Nome do Produto (Ex: Arroz 1kg, Sabonete 80g)")
        m = st.text_input("Marca (Ex: Camil, Kicaldo, Pilão)")
        u = st.selectbox("Unidade", ["KG", "PCT", "UN", "FR", "LT", "CX", "SC"])
        g = st.text_input("Grupo / Categoria (Ex: Arroz, Feijão, Café)")
        if st.form_submit_button("Salvar Produto"):
            if n and m:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)", (n, m, u, g))
                conn.commit()
                conn.close()
                st.success("Produto cadastrado com sucesso!")
                st.rerun()
            else:
                st.warning("Preencha o nome e a marca do produto.")

# 2. FORNECEDORES & PREÇOS
elif menu == "🏭 Fornecedores & Preços":
    st.header("🏭 Cotações por Atacadista")
    st.markdown("Insira os preços atuais praticados pelos atacadistas de Boa Vista para cada produto e marca.")
    
    conn = get_connection()
    prods = pd.read_sql_query("SELECT id, (nome || ' - Marca: ' || marca) AS item FROM produtos", conn)
    fornecs = pd.read_sql_query("SELECT id, nome FROM fornecedores", conn)
    conn.close()
    
    if prods.empty or fornecs.empty:
        st.warning("Cadastre produtos e fornecedores primeiro.")
    else:
        with st.form("form_cot"):
            p = st.selectbox("Produto / Marca", prods["id"], format_func=lambda x: prods[prods["id"] == x]["item"].values[0])
            f = st.selectbox("Atacadista / Fornecedor", fornecs["id"], format_func=lambda x: fornecs[fornecs["id"] == x]["nome"].values[0])
            pr = st.number_input("Preço Unitário (R$)", min_value=0.01, step=0.10)
            dt = st.date_input("Data da Cotação", value=datetime.now())
            if st.form_submit_button("Salvar Cotação"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, ?)", (p, f, pr, dt.strftime("%Y-%m-%d")))
                conn.commit()
                conn.close()
                st.success("Cotação salva com sucesso!")
                st.rerun()

# 3. COTAÇÕES & HISTÓRICO
elif menu == "📊 Cotações & Histórico":
    st.header("📊 Histórico Temporal de Preços")
    st.markdown("Acompanhe a variação e o histórico de preços registrados entre os atacadistas.")
    
    conn = get_connection()
    df = pd.read_sql_query("SELECT c.data_cotacao, (p.nome || ' - ' || p.marca) AS prod, f.nome AS atac, c.preco FROM cotacoes c JOIN produtos p ON c.produto_id=p.id JOIN fornecedores f ON c.fornecedor_id=f.id ORDER BY c.data_cotacao DESC", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Ainda não há cotações registradas.")

# 4. MONTAGEM & PRECIFICAÇÃO DA CESTA
elif menu == "🧩 Montagem & Precificação da Cesta":
    st.header("🧩 Montagem Personalizada do Kit & Cálculo de Custo Pós-Composição")
    st.markdown("Selecione o kit, adicione os produtos e marcas desejados, e o sistema calculará o custo real com base no menor preço da praça.")
    
    conn = get_connection()
    tipos_cesta = pd.read_sql_query("SELECT id, nome FROM tipos_cesta", conn)
    produtos_df = pd.read_sql_query("SELECT id, (nome || ' - ' || marca || ' [' || unidade || ']') AS desc_item FROM produtos", conn)
    conn.close()
    
    if tipos_cesta.empty:
        st.warning("Cadastre um modelo de cesta.")
    else:
        c1, c2 = st.columns([1, 2])
        with c1:
            cesta_esc = st.selectbox("Kit Alvo", tipos_cesta["nome"])
            cesta_id = int(tipos_cesta[tipos_cesta["nome"] == cesta_esc]["id"].values[0])
            
            with st.form("form_add"):
                p_sel = st.selectbox("Produto / Marca", produtos_df["id"], format_func=lambda x: produtos_df[produtos_df["id"] == x]["desc_item"].values[0])
                qtd = st.number_input("Quantidade no Kit", value=1.0, step=1.0, min_value=0.1)
                if st.form_submit_button("➕ Adicionar à Cesta"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO composicao_cesta (tipo_cesta_id, produto_id, quantidade) VALUES (?, ?, ?)", (cesta_id, p_sel, qtd))
                    conn.commit()
                    conn.close()
                    st.success("Item adicionado com sucesso!")
                    st.rerun()
                    
        with c2:
            st.subheader(f"Custo Calculado: {cesta_esc}")
            m_l = st.slider("Margem de Lucro (%)", 5.0, 60.0, float(params.get("margem_lucro_padrao", 25.0)))
            
            df_itens, c_ins, c_tot, v_luc, p_sug = calcular_custo_cesta(cesta_id, m_l)
            if df_itens.empty:
                st.info("Nenhum item montado nesta cesta ainda. Use o painel ao lado para adicionar os produtos.")
            else:
                st.metric("Custo Total de Produção", f"R$ {c_tot:.2f}", f"Lucro Estimado: R$ {v_luc:.2f}")
                st.markdown("---")
                st.dataframe(df_itens[["produto", "quantidade", "unidade", "menor_preco", "fornecedor", "subtotal"]], use_container_width=True)
