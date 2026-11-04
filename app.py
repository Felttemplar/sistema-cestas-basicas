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

if menu == "📥 Upload & Importação":
    st.header("📥 Importação Automatizada via Planilha Padrão")
    st.markdown("Faça o upload da planilha padronizada para atualizar produtos e cotações de forma limpa.")
    
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
            df_up = pd.read_excel(uploaded_file, sheet_name=0, engine="openpyxl")
            st.success(f"Planilha carregada com sucesso! {len(df_up)} linhas encontradas.")
            
            if st.button("🚀 Processar e Alimentar Banco de Dados (Limpeza Total e Recarga)"):
                conn = get_connection()
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM cotacoes")
                cursor.execute("DELETE FROM itens_lote")
                cursor.execute("DELETE FROM produtos")
                conn.commit()
                
                count_prods = 0
                count_cots = 0
                
                atacadistas_indices = {
                    "Assaí Atacadista": 5,
                    "Atacadão": 6,
                    "Supermercado Gavião": 7,
                    "Novo Tempo": 8,
                    "Nova Era": 9,
                    "Goiano": 10,
                    "Aguiar": 11,
                    "Distribuidora 1": 12
                }
                
                for idx, row in df_up.iterrows():
                    if len(row) < 3:
                        continue
                    
                    # Procura estritamente a célula que contém o nome real do produto
                    nome_prod = ""
                    unidade = "UN"
                    marca = "Geral"
                    
                    # Testa colunas da esquerda para a direita ignorando unidades/categorias conhecidas
                    for col_idx in [2, 1, 3, 0]:
                        if col_idx < len(row) and not pd.isna(row.iloc[col_idx]):
                            val = str(row.iloc[col_idx]).strip()
                            val_up = val.upper()
                            
                            # Lista negra de termos que NÃO podem ser nomes de produtos
                            termos_proibidos = [
                                "NAN", "NONE", "PRODUTO", "ITEM", "KG", "UN", "LT", "PCT", 
                                "UND", "SC", "CX", "FR", "ALIMENTO", "LIMPEZA", "HIGIENE", 
                                "KG - ALIMENTO", "UN - ALIMENTO", "PC - ALIMENTO", "SC/G - ALIMENTO", "FR - ALIMENTO"
                            ]
                            
                            if val and val_up not in termos_proibidos and not val_up.endswith("- ALIMENTO") and not val_up.endswith("- LIMPEZA"):
                                if len(val) > 2:
                                    nome_prod = val
                                    break
                    
                    if not nome_prod:
                        continue
                        
                    if len(row) > 3 and not pd.isna(row.iloc[3]):
                        u_cand = str(row.iloc[3]).strip()
                        if u_cand.upper() in ["KG", "UN", "PCT", "LT", "CX", "SC", "UND", "FR"]:
                            unidade = u_cand
                            
                    if len(row) > 4 and not pd.isna(row.iloc[4]):
                        m_cand = str(row.iloc[4]).strip()
                        if m_cand.upper() not in ["NAN", "NONE"]:
                            marca = m_cand

                    cursor.execute(
                        "INSERT INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)",
                        (nome_prod.upper(), marca.upper(), unidade.upper(), nome_prod.upper())
                    )
                    conn.commit()
                    count_prods += 1
                    
                    cursor.execute("SELECT id FROM produtos WHERE nome = ? AND marca = ?", (nome_prod.upper(), marca.upper()))
                    p_res = cursor.fetchone()
                    if not p_res:
                        continue
                    produto_db_id = p_res[0]
                    
                    for atac_nome, col_idx in atacadistas_indices.items():
                        if col_idx < len(row):
                            preco_val = row.iloc[col_idx]
                            if not pd.isna(preco_val) and isinstance(preco_val, (int, float)) and preco_val > 0:
                                cursor.execute("SELECT id FROM fornecedores WHERE nome = ?", (atac_nome,))
                                f_res = cursor.fetchone()
                                if f_res:
                                    forn_id = f_res[0]
                                    cursor.execute(
                                        "INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, date('now'))",
                                        (produto_db_id, forn_id, float(preco_val))
                                    )
                                    count_cots += 1
                conn.commit()
                conn.close()
                st.success(f"✅ Importação limpa concluída com sucesso! {count_prods} produtos válidos e {count_cots} cotações inseridos.")
        except Exception as e:
            st.error(f"Erro crítico ao processar a planilha: {e}")

elif menu == "📦 Cadastrar Produtos & Marcas":
    st.header("📦 Cadastro de Produtos e Marcas")
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

elif menu == "🏭 Fornecedores & Preços":
    st.header("🏭 Cotações por Atacadista & Menor Preço")
    conn = get_connection()
    df_cot = pd.read_sql_query("""
        SELECT (p.nome || ' - ' || p.marca) AS produto, p.unidade, f.nome AS fornecedor, c.preco, c.data_cotacao
        FROM cotacoes c 
        JOIN produtos p ON c.produto_id = p.id 
        JOIN fornecedores f ON c.fornecedor_id = f.id
        ORDER BY c.preco ASC
    """, conn)
    conn.close()
    
    if not df_cot.empty:
        st.dataframe(df_cot, use_container_width=True)
    else:
        st.info("Nenhuma cotação registada. Faça o upload da planilha primeiro.")

elif menu == "📊 Cotações & Histórico":
    st.header("📊 Histórico Temporal de Preços")
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT c.data_cotacao, (p.nome || ' - ' || p.marca) AS prod, f.nome AS atac, c.preco 
        FROM cotacoes c 
        JOIN produtos p ON c.produto_id=p.id 
        JOIN fornecedores f ON c.fornecedor_id=f.id 
        ORDER BY c.data_cotacao DESC
    """, conn)
    conn.close()
    if not df.empty: 
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhuma cotação registada.")

elif menu == "📦 Gestão de Lotes & Precificação":
    st.header("📦 Controle de Lotes de Compra & Custos Fechados")
    st.markdown("Registre o lote semanal de compras com base nas melhores cotações.")
    
    nome_lote_input = st.text_input("Identificação do Lote (Ex: Lote Semana 01 - Novembro)", value=f"Lote - {datetime.now().strftime('%d/%m/%Y')}")
    
    conn = get_connection()
    df_prods = pd.read_sql_query("SELECT id, (nome || ' - ' || marca) AS item FROM produtos", conn)
    conn.close()
    
    if not df_prods.empty:
        with st.form("form_lote"):
            st.subheader("Itens e Quantidades do Lote")
            qtde_itens = st.number_input("Quantos itens compõem este lote de compra?", min_value=1, max_value=50, value=5)
            
            itens_lote_dados = []
            for i in range(int(qtde_itens)):
                cols = st.columns([3, 2, 2])
                with cols[0]:
                    prod_sel = st.selectbox(f"Produto {i+1}", df_prods["id"], format_func=lambda x: df_prods[df_prods["id"] == x]["item"].values[0], key=f"lote_prod_{i}")
                with cols[1]:
                    qtd_compra = st.number_input(f"Qtd Comprada", min_value=0.1, value=10.0, key=f"lote_qtd_{i}")
                with cols[2]:
                    custo_unit = st.number_input(f"Custo Unit. (R$)", min_value=0.01, value=5.00, key=f"lote_custo_{i}")
                itens_lote_dados.append((prod_sel, qtd_compra, custo_unit))
                
            if st.form_submit_button("💾 Salvar Lote no Estoque"):
                conn = get_connection()
                cursor = conn.cursor()
                custo_total_lote = sum([q * c for _, q, c in itens_lote_dados])
                
                cursor.execute("INSERT INTO lotes (nome_lote, data_compra, custo_total) VALUES (?, date('now'), ?)", (nome_lote_input, custo_total_lote))
                lote_id = cursor.lastrowid
                
                for p_id, qtd, custo in itens_lote_dados:
                    cursor.execute("INSERT INTO itens_lote (lote_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)", (lote_id, p_id, qtd, custo))
                
                conn.commit()
                conn.close()
                st.success(f"✅ Lote '{nome_lote_input}' salvo com sucesso! Custo total: R$ {custo_total_lote:.2f}")
    else:
        st.warning("Cadastre ou importe produtos antes de gerenciar lotes.")

elif menu == "🧩 Montagem de Kits":
    st.header("🧩 Montagem de Kits e Cestas Básicas")
    st.markdown("Calcule o custo de montagem das cestas aplicando margem de lucro e rendimento.")
    
    conn = get_connection()
    df_lotes = pd.read_sql_query("SELECT id, nome_lote, custo_total FROM lotes ORDER BY id DESC", conn)
    conn.close()
    
    if not df_lotes.empty:
        lote_escolhido = st.selectbox("Selecione o Lote de Referência", df_lotes["id"], format_func=lambda x: df_lotes[df_lotes["id"] == x]["nome_lote"].values[0])
        
        margem = st.slider("Margem de Lucro Desejada (%)", min_value=0.0, max_value=100.0, value=25.0, step=1.0)
        qtd_cestas = st.number_input("Quantas cestas serão montadas com este lote?", min_value=1, value=50)
        
        conn = get_connection()
        df_itens = pd.read_sql_query(f"SELECT (p.nome || ' - ' || p.marca) AS produto, il.quantidade, il.preco_unitario FROM itens_lote il JOIN produtos p ON il.produto_id = p.id WHERE il.lote_id = {lote_escolhido}", conn)
        conn.close()
        
        if not df_itens.empty:
            st.subheader("Composição do Lote Selecionado")
            st.dataframe(df_itens, use_container_width=True)
            
            custo_total_lote_sel = sum(df_itens["quantidade"] * df_itens["preco_unitario"])
            custo_por_cesta = custo_total_lote_sel / qtd_cestas
            preco_venda_cesta = custo_por_cesta * (1 + (margem / 100))
            
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Custo Total do Lote", f"R$ {custo_total_lote_sel:.2f}")
            with col2:
                st.metric("Custo Unitário da Cesta", f"R$ {custo_por_cesta:.2f}")
            with col3:
                st.metric("Preço de Venda Sugerido", f"R$ {preco_venda_cesta:.2f}", delta=f"{margem}% de Lucro")
    else:
        st.info("Nenhum lote cadastrado. Vá na aba 'Gestão de Lotes & Precificação' para registrar a primeira compra.")
