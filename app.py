import streamlit as st
import pandas as pd
from datetime import datetime
from core.database import init_db, get_connection

init_db()
st.set_page_config(page_title="Cestas Bom Dia - Boa Vista", page_icon="🛒", layout="wide")
st.title("🛒 Cestas Bom Dia - Gestão Operacional & Lotes")

menu = st.sidebar.radio("Navegabilidade:", [
    "📦 Cadastrar Produtos & Marcas", 
    "🏭 Fornecedores & Preços", 
    "📊 Cotações & Histórico",
    "📦 Gestão de Lotes & Precificação",
    "🧩 Montagem de Kits"
])

# 1. CADASTRAR PRODUTOS & MARCAS
if menu == "📦 Cadastrar Produtos & Marcas":
    st.header("📦 Cadastro de Produtos e Marcas")
    st.markdown("Cadastre os insumos e alimentos com suas respectivas marcas e unidades de medida.")
    
    with st.form("form_prod"):
        n = st.text_input("Nome do Produto (Ex: Arroz 1kg, Feijão 1kg)")
        m = st.text_input("Marca (Ex: Prato Chic, Kicaldo, Pilão)")
        u = st.selectbox("Unidade", ["KG", "PCT", "UN", "FR", "LT", "CX", "SC"])
        g = st.text_input("Grupo / Categoria (Ex: Alimento, Higiene, Limpeza)")
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
                st.warning("Preencha o nome e a marca.")

# 2. FORNECEDORES & PREÇOS
elif menu == "🏭 Fornecedores & Preços":
    st.header("🏭 Cotações por Atacadista")
    st.markdown("Registre os preços de mercado praticados pelos atacadistas de Boa Vista.")
    
    conn = get_connection()
    prods = pd.read_sql_query("SELECT id, (nome || ' - ' || marca) AS item FROM produtos", conn)
    fornecs = pd.read_sql_query("SELECT id, nome FROM fornecedores", conn)
    conn.close()
    
    if prods.empty or fornecs.empty:
        st.warning("Cadastre produtos e fornecedores primeiro.")
    else:
        with st.form("form_cot"):
            p = st.selectbox("Produto / Marca", prods["id"], format_func=lambda x: prods[prods["id"] == x]["item"].values[0])
            f = st.selectbox("Atacadista", fornecs["id"], format_func=lambda x: fornecs[fornecs["id"] == x]["nome"].values[0])
            pr = st.number_input("Preço Unitário (R$)", min_value=0.01, step=0.10)
            dt = st.date_input("Data", value=datetime.now())
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
    conn = get_connection()
    df = pd.read_sql_query("SELECT c.data_cotacao, (p.nome || ' - ' || p.marca) AS prod, f.nome AS atac, c.preco FROM cotacoes c JOIN produtos p ON c.produto_id=p.id JOIN fornecedores f ON c.fornecedor_id=f.id ORDER BY c.data_cotacao DESC", conn)
    conn.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhuma cotação registrada.")

# 4. GESTÃO DE LOTES & PRECIFICAÇÃO
elif menu == "📦 Gestão de Lotes & Precificação":
    st.header("📦 Controle de Lotes de Compra & Custos Fechados")
    st.markdown("Cada compra define um lote independente com frete, embalagem e margem de lucro exclusiva.")
    
    conn = get_connection()
    fornecs = pd.read_sql_query("SELECT id, nome FROM fornecedores", conn)
    prods = pd.read_sql_query("SELECT id, (nome || ' - ' || marca || ' (' || unidade || ')') AS item FROM produtos", conn)
    lotes_cadastrados = pd.read_sql_query("SELECT id, numero_lote, data_compra FROM lotes WHERE ativo = 1", conn)
    conn.close()

    tab1, tab2 = st.tabs(["➕ Criar / Gerenciar Lote", "📊 Análise de Custos e Margens por Lote"])
    
    with tab1:
        with st.form("form_lote_novo"):
            c1, c2, c3 = st.columns(3)
            with c1:
                num_lote = st.text_input("Identificação do Lote", value=f"LOTE-{datetime.now().strftime('%Y%m%d-%H%M')}")
            with c2:
                data_c = st.date_input("Data da Compra", value=datetime.now())
            with c3:
                forn_lote = st.selectbox("Fornecedor", fornecs["id"] if not fornecs.empty else [0], format_func=lambda x: fornecs[fornecs["id"] == x]["nome"].values[0] if not fornecs.empty else "Nenhum")
            
            obs = st.text_input("Observações (Ex: Reposição quinzenal)")
            c_emb = st.number_input("Custo de Embalagem (R$)", value=3.50)
            c_frete = st.number_input("Frete do Lote (R$)", value=10.00)
            m_lucro = st.slider("Margem de Lucro Alvo (%)", 5.0, 60.0, 25.0)
            
            if st.form_submit_button("Criar Lote"):
                if num_lote:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO lotes (numero_lote, data_compra, fornecedor_id, observacao, custo_embalagem, frete_lote, margem_lucro_perc) VALUES (?, ?, ?, ?, ?, ?, ?)", (num_lote, data_c.strftime("%Y-%m-%d"), forn_lote, obs, c_emb, c_frete, m_lucro))
                    conn.commit()
                    conn.close()
                    st.success("Lote criado com sucesso!")
                    st.rerun()
                    
        st.markdown("---")
        st.subheader("Adicionar Produtos ao Lote")
        if not lotes_cadastrados.empty:
            lote_esc = st.selectbox("Lote Ativo", lotes_cadastrados["id"], format_func=lambda x: lotes_cadastrados[lotes_cadastrados["id"] == x]["numero_lote"].values[0])
            
            with st.form("form_item_lote"):
                prod_lote = st.selectbox("Produto", prods["id"] if not prods.empty else [0], format_func=lambda x: prods[prods["id"] == x]["item"].values[0] if not prods.empty else "Nenhum")
                q_lote = st.number_input("Quantidade Comprada", value=10.0, step=1.0)
                p_unit = st.number_input("Preço Unitário Pago (R$)", value=5.00, step=0.10)
                
                if st.form_submit_button("Adicionar Item"):
                    sub = q_lote * p_unit
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO itens_lote (lote_id, produto_id, quantidade, preco_unitario, subtotal) VALUES (?, ?, ?, ?, ?)", (lote_esc, prod_lote, q_lote, p_unit, sub))
                    conn.commit()
                    conn.close()
                    st.success("Item adicionado!")
                    st.rerun()
                    
            conn = get_connection()
            df_itens_lote = pd.read_sql_query("SELECT il.id, (p.nome || ' - ' || p.marca) AS produto, il.quantidade, p.unidade, il.preco_unitario, il.subtotal FROM itens_lote il JOIN produtos p ON il.produto_id = p.id WHERE il.lote_id = ?", conn, params=(lote_esc,))
            conn.close()
            if not df_itens_lote.empty:
                st.dataframe(df_itens_lote, use_container_width=True)
        else:
            st.info("Crie um lote acima para começar.")

    with tab2:
        st.header("📊 Análise de Custos e Precificação por Lote")
        if not lotes_cadastrados.empty:
            lote_rel = st.selectbox("Selecionar Lote", lotes_cadastrados["id"], format_func=lambda x: lotes_cadastrados[lotes_cadastrados["id"] == x]["numero_lote"].values[0], key="sel_lote_rel")
            
            conn = get_connection()
            lote_info = pd.read_sql_query("SELECT * FROM lotes WHERE id = ?", conn, params=(lote_rel,)).iloc[0]
            df_analise = pd.read_sql_query("SELECT (p.nome || ' - ' || p.marca) AS produto, il.quantidade, il.preco_unitario, il.subtotal FROM itens_lote il JOIN produtos p ON il.produto_id = p.id WHERE il.lote_id = ?", conn, params=(lote_rel,))
            conn.close()
            
            if not df_analise.empty:
                total_insumos = df_analise["subtotal"].sum()
                custo_total = total_insumos + lote_info["custo_embalagem"] + lote_info["frete_lote"]
                lucro_est = custo_total * (lote_info["margem_lucro_perc"] / 100.0)
                preco_sugerido = custo_total + lucro_est
                
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Custo dos Insumos", f"R$ {total_insumos:.2f}")
                col_b.metric("Custo Total (c/ Frete/Embalagem)", f"R$ {custo_total:.2f}")
                col_c.metric(f"Lucro Alvo ({lote_info['margem_lucro_perc']}%)", f"R$ {lucro_est:.2f}")
                col_d.metric("Preço de Venda Sugerido", f"R$ {preco_sugerido:.2f}")
                
                st.dataframe(df_analise, use_container_width=True)
            else:
                st.info("Lote sem itens.")
        else:
            st.info("Nenhum lote cadastrado.")

# 5. MONTAGEM DE KITS
elif menu == "🧩 Montagem de Kits":
    st.header("🧩 Montagem de Kits e Cestas")
    conn = get_connection()
    cestas = pd.read_sql_query("SELECT id, nome FROM tipos_cesta", conn)
    conn.close()
    if not cestas.empty:
        cesta_esc = st.selectbox("Tipo de Cesta", cestas["nome"])
        st.info(f"Gerenciando composição para: {cesta_esc} (Integração ativa com os lotes de compra).")
