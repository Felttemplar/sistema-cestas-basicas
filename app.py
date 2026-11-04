import streamlit as st
import pandas as pd
from datetime import datetime
from core.database import init_db, get_connection

init_db()
st.set_page_config(page_title="Cestas Bom Dia - Gestão por Lotes", page_icon="🛒", layout="wide")
st.title("🛒 Cestas Bom Dia - Gestão Operacional por Lotes & Precificação")

menu = st.sidebar.radio("Navegabilidade:", [
    "📦 Gestão de Lotes & Precificação", 
    "📦 Cadastrar Produtos & Marcas", 
    "🏭 Fornecedores & Preços", 
    "📊 Cotações & Histórico",
    "🧩 Montagem de Kits"
])

if menu == "📦 Gestão de Lotes & Precificação":
    st.header("📦 Cadastro e Controle de Lotes de Compra")
    st.markdown("Cada compra de mercadoria forma um lote isolado com seus custos reais, frete e margem de lucro exclusiva.")
    
    conn = get_connection()
    fornecs = pd.read_sql_query("SELECT id, nome FROM fornecedores", conn)
    prods = pd.read_sql_query("SELECT id, (nome || ' - ' || marca || ' (' || unidade || ')') AS item FROM produtos", conn)
    lotes_cadastrados = pd.read_sql_query("SELECT id, numero_lote, data_compra FROM lotes WHERE ativo = 1", conn)
    conn.close()

    tab1, tab2 = st.tabs(["➕ Criar / Gerenciar Lote", "📊 Análise de Precificação por Lote"])
    
    with tab1:
        with st.form("form_lote_novo"):
            col1, col2, col3 = st.columns(3)
            with col1:
                num_lote = st.text_input("Identificação do Lote (Ex: LOTE-ASSIN-2026-11)", value=f"LOTE-{datetime.now().strftime('%Y%m%d-%H%M')}")
            with col2:
                data_c = st.date_input("Data da Compra", value=datetime.now())
            with col3:
                forn_lote = st.selectbox("Fornecedor Principal do Lote", fornecs["id"] if not fornecs.empty else [0], format_func=lambda x: fornecs[fornecs["id"] == x]["nome"].values[0] if not fornecs.empty else "Nenhum")
            
            obs = st.text_input("Observações do Lote (Ex: Compra quinzenal de reposição)")
            
            c_emb = st.number_input("Custo de Embalagem (R$)", value=3.50)
            c_frete = st.number_input("Frete do Lote (R$)", value=10.00)
            m_lucro = st.slider("Margem de Lucro Alvo (%)", 5.0, 60.0, 25.0)
            
            if st.form_submit_button("Criar Novo Lote"):
                if num_lote:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO lotes (numero_lote, data_compra, fornecedor_id, observacao, custo_embalagem, frete_lote, margem_lucro_perc)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (num_lote, data_c.strftime("%Y-%m-%d"), forn_lote, obs, c_emb, c_frete, m_lucro))
                    conn.commit()
                    conn.close()
                    st.success(f"Lote {num_lote} criado com sucesso! Agora adicione os itens abaixo.")
                    st.rerun()
                else:
                    st.error("Informe a identificação do lote.")
                    
        st.markdown("---")
        st.subheader("Adicionar Itens ao Lote Selecionado")
        if not lotes_cadastrados.empty:
            lote_esc = st.selectbox("Selecione o Lote Ativo", lotes_cadastrados["id"], format_func=lambda x: lotes_cadastrados[lotes_cadastrados["id"] == x]["numero_lote"].values[0])
            
            with st.form("form_item_lote"):
                prod_lote = st.selectbox("Produto", prods["id"] if not prods.empty else [0], format_func=lambda x: prods[prods["id"] == x]["item"].values[0] if not prods.empty else "Nenhum")
                q_lote = st.number_input("Quantidade Comprada", value=10.0, step=1.0)
                p_unit = st.number_input("Preço Unitário Pago (R$)", value=5.00, step=0.10)
                
                if st.form_submit_button("Adicionar Item ao Lote"):
                    sub = q_lote * p_unit
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO itens_lote (lote_id, produto_id, quantidade, preco_unitario, subtotal) VALUES (?, ?, ?, ?, ?)", (lote_esc, prod_lote, q_lote, p_unit, sub))
                    conn.commit()
                    conn.close()
                    st.success("Item adicionado ao lote!")
                    st.rerun()
                    
            # Mostrar itens atuais do lote
            conn = get_connection()
            df_itens_lote = pd.read_sql_query("SELECT il.id, (p.nome || ' - ' || p.marca) AS produto, il.quantidade, p.unidade, il.preco_unitario, il.subtotal FROM itens_lote il JOIN produtos p ON il.produto_id = p.id WHERE il.lote_id = ?", conn, params=(lote_esc,))
            conn.close()
            
            if not df_itens_lote.empty:
                st.dataframe(df_itens_lote, use_container_width=True)
        else:
            st.info("Crie um lote acima para começar a adicionar os produtos.")

    with tab2:
        st.header("📊 Precificação e Custos Fechados por Lote")
        if not lotes_cadastrados.empty:
            lote_rel = st.selectbox("Selecione o Lote para Análise", lotes_cadastrados["id"], format_func=lambda x: lotes_cadastrados[lotes_cadastrados["id"] == x]["numero_lote"].values[0], key="sel_lote_rel")
            
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
                col_b.metric("Custo Total (com Frete/Embalagem)", f"R$ {custo_total:.2f}")
                col_c.metric(f"Lucro Alvo ({lote_info['margem_lucro_perc']}%)", f"R$ {lucro_est:.2f}")
                col_d.metric("Preço de Venda Sugerido", f"R$ {preco_sugerido:.2f}")
                
                st.markdown("### Composição do Lote")
                st.dataframe(df_analise, use_container_width=True)
            else:
                st.info("Este lote ainda não possui itens cadastrados.")
        else:
            st.info("Nenhum lote disponível para análise.")

elif menu == "📦 Cadastrar Produtos & Marcas":
    st.header("📦 Cadastro de Produtos e Marcas")
    with st.form("form_prod"):
        n = st.text_input("Nome do Produto")
        m = st.text_input("Marca")
        u = st.selectbox("Unidade", ["KG", "PCT", "UN", "FR", "LT", "CX", "SC"])
        g = st.text_input("Grupo / Categoria")
        if st.form_submit_button("Salvar Produto"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)", (n, m, u, g))
            conn.commit()
            conn.close()
            st.success("Cadastrado com sucesso!")
            st.rerun()

elif menu == "🏭 Fornecedores & Preços":
    st.header("🏭 Cadastro de Fornecedores")
    with st.form("form_forn"):
        nf = st.text_input("Nome do Fornecedor / Atacadista")
        tf = st.text_input("Telefone / Contato")
        if st.form_submit_button("Salvar Fornecedor"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO fornecedores (nome, telefone) VALUES (?, ?)", (nf, tf))
            conn.commit()
            conn.close()
            st.success("Fornecedor salvo!")
            st.rerun()

elif menu == "📊 Cotações & Histórico":
    st.header("📊 Histórico de Cotações")
    conn = get_connection()
    df = pd.read_sql_query("SELECT c.data_cotacao, (p.nome || ' - ' || p.marca) AS prod, f.nome AS atac, c.preco FROM cotacoes c JOIN produtos p ON c.produto_id=p.id JOIN fornecedores f ON c.fornecedor_id=f.id", conn)
    conn.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sem cotações registradas.")

elif menu == "🧩 Montagem de Kits":
    st.header("🧩 Montagem de Kits e Cestas")
    conn = get_connection()
    cestas = pd.read_sql_query("SELECT id, nome FROM tipos_cesta", conn)
    conn.close()
    if not cestas.empty:
        st.selectbox("Selecione a Cesta", cestas["nome"])
        st.info("Funcionalidade de composição de kits integrada com os lotes de compra.")
