import streamlit as st
import pandas as pd
from datetime import datetime
from core.database import init_db, get_connection

init_db()
st.set_page_config(page_title="Cestas Bom Dia - Boa Vista", page_icon="🛒", layout="wide")
st.title("🛒 Cestas Bom Dia - Gestão Operacional & Lotes")

menu = st.sidebar.radio("Navegabilidade:", [
    "📥 Upload & Importação",
    "📦 Cadastrar Produtos & Marcas", 
    "🏭 Fornecedores & Preços", 
    "📊 Cotações & Histórico",
    "📦 Gestão de Lotes & Precificação",
    "🧩 Montagem de Kits"
])

# 0. UPLOAD & IMPORTAÇÃO DE PLANILHA
if menu == "📥 Upload & Importação":
    st.header("📥 Importação Automatizada via Planilha Padrão")
    st.markdown("Faça o upload da planilha padronizada (`Cestas_Bom_Dia_Template_Upload.xlsx`) para atualizar instantaneamente todos os produtos, marcas e cotações dos atacadistas no sistema.")
    
    try:
        with open("Cestas_Bom_Dia_Template_Upload.xlsx", "rb") as f:
            st.download_button(
                label="⬇️ Baixar Planilha Modelo Padrão",
                data=f,
                file_name="Cestas_Bom_Dia_Template_Upload.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception:
        st.info("Planilha modelo não encontrada na raiz.")
        
    st.markdown("---")
    uploaded_file = st.file_uploader("Carregar Planilha Preenchida (.xlsx)", type=["xlsx"])
    
    if uploaded_file is not None:
        try:
            df_up = pd.read_excel(uploaded_file, sheet_name=0)
            st.success(f"Planilha carregada com sucesso! {len(df_up)} linhas encontradas.")
            
            if st.button("🚀 Processar e Alimentar Banco de Dados"):
                conn = get_connection()
                cursor = conn.cursor()
                
                atacadistas_cols = {
                    "Assaí Atacadista": 5,
                    "Atacadão": 6,
                    "Supermercado Gavião": 7,
                    "Novo Tempo": 8,
                    "Nova Era": 9,
                    "Goiano": 10,
                    "Aguiar": 11,
                    "Distribuidora 1": 12
                }
                
                count_prods = 0
                count_cots = 0
                
                for idx, row in df_up.iterrows():
                    if len(row) < 5:
                        continue
                    nome_prod = row.iloc[2]
                    unidade = row.iloc[3]
                    marca = row.iloc[4]
                    
                    if pd.isna(nome_prod) or str(nome_prod).strip() == "":
                        continue
                        
                    nome_clean = str(nome_prod).strip()
                    unidade_str = str(unidade).strip() if not pd.isna(unidade) else "UN"
                    marca_str = str(marca).strip() if not pd.isna(marca) and str(marca).strip() != "" else "Geral"
                    
                    cursor.execute(
                        "INSERT OR IGNORE INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)",
                        (nome_clean, marca_str, unidade_str, nome_clean)
                    )
                    conn.commit()
                    count_prods += 1
                    
                    cursor.execute("SELECT id FROM produtos WHERE nome = ? AND marca = ?", (nome_clean, marca_str))
                    p_res = cursor.fetchone()
                    if not p_res:
                        continue
                    produto_db_id = p_res[0]
                    
                    for atac_nome, col_idx in atacadistas_cols.items():
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
                                    count_cots += 1
                conn.commit()
                conn.close()
                st.success(f"✅ Importação concluída! {count_prods} produtos e {count_cots} cotações atualizados no sistema.")
        except Exception as e:
            st.error(f"Erro ao processar a planilha: {e}")

# 1. CADASTRAR PRODUTOS & MARCAS
elif menu == "📦 Cadastrar Produtos & Marcas":
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
    st.markdown("Registre ou consulte os preços de mercado praticados pelos atacadistas de Boa Vista.")
    
    conn = get_connection()
    prods = pd.read_sql_query("SELECT id, (nome || ' - ' || marca) AS item FROM produtos", conn)
    fornecs = pd.read_sql_query("SELECT id, nome FROM fornecedores", conn)
    conn.close()
    
    if prods.empty or fornecs.empty:
        st.warning("Cadastre produtos e fornecedores primeiro ou faça o upload da planilha.")
    else:
        with st.form("form_cot"):
            p = st.selectbox("Produto / Marca", prods["id"], format_func=lambda x: prods[prods["id"] == x]["item"].values[0])
            f = st.selectbox("Atacadista", fornecs["id"], format_func=lambda x: fornecs[fornecs["id"] == x]["nome"].values[0])
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
    st.markdown("Acompanhe o histórico de cotações registradas por produto e atacadista.")
    conn = get_connection()
    df = pd.read_sql_query("SELECT c.data_cotacao AS Data, (p.nome || ' - ' || p.marca) AS Produto, f.nome AS Atacadista, c.preco AS 'Preço (R$)' FROM cotacoes c JOIN produtos p ON c.produto_id=p.id JOIN fornecedores f ON c.fornecedor_id=f.id ORDER BY c.data_cotacao DESC", conn)
    conn.close()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhuma cotação registrada até o momento.")

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
