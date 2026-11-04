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
                    "Assaí Atacadista": 4,
                    "Atacadão": 6
                }
                
                for idx, row in df_up.iterrows():
                    if len(row) < 2:
                        continue
                    
                    val_prod = str(row.iloc[1]).strip() if not pd.isna(row.iloc[1]) else ""
                    val_up = val_prod.upper()
                    
                    if not val_prod or val_up in ["NAN", "NONE", "PRODUTO", "ITEM", "ALIMENTOS", "HIGIENE", "LIMPEZA", "RESFRIADOS/CONGELADOS"]:
                        continue
                    if val_up.startswith("ALIMENTOS") or val_up.startswith("HIGIENE") or val_up.startswith("LIMPEZA"):
                        continue
                        
                    nome_prod = val_prod
                    unidade = str(row.iloc[2]).strip() if len(row) > 2 and not pd.isna(row.iloc[2]) else "UN"
                    if unidade.upper() in ["NAN", "NONE", ""]:
                        unidade = "UN"
                        
                    marca = str(row.iloc[3]).strip() if len(row) > 3 and not pd.isna(row.iloc[3]) else "Geral"
                    if marca.upper() in ["NAN", "NONE", ""]:
                        marca = "Geral"

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
                st.success(f"✅ Importação concluída com sucesso! {count_prods} produtos válidos e {count_cots} cotações inseridos.")
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
        qtde_itens = st.number_input("Quantos itens compõem este lote de compra?", min_value=1, max_value=50, value=7, step=1)
        
        with st.form("form_lote"):
            st.subheader("Itens e Quantidades do Lote")
            
            itens_lote_dados = []
            for i in range(int(qtde_itens)):
                cols = st.columns([3, 2, 2])
                with cols[0]:
                    prod_sel = st.selectbox(f"Produto {i+1}", df_prods["id"], format_func=lambda x: df_prods[df_prods["id"] == x]["item"].values[0], key=f"lote_prod_{i}")
                with cols[1]:
                    qtd_compra = st.number_input(f"Qtd Comprada {i+1}", min_value=0.1, value=10.0, key=f"lote_qtd_{i}")
                with cols[2]:
                    custo_unit = st.number_input(f"Custo Unit. {i+1} (R$)", min_value=0.01, value=5.00, key=f"lote_custo_{i}")
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
    st.header("🧩 Cálculo Automático de Rendimento de Cestas & Precificação")
    st.markdown("O sistema analisa a quantidade de cada produto disponível no lote e calcula o **número máximo de cestas** que podem ser montadas.")
    
    conn = get_connection()
    df_lotes = pd.read_sql_query("SELECT id, nome_lote, custo_total FROM lotes ORDER BY id DESC", conn)
    conn.close()
    
    if not df_lotes.empty:
        lote_escolhido = st.selectbox("Selecione o Lote de Referência", df_lotes["id"], format_func=lambda x: df_lotes[df_lotes["id"] == x]["nome_lote"].values[0])
        
        modelo_cesta = st.selectbox("Selecione o Modelo da Cesta", ["Cesta Econômica (12-14 itens)", "Cesta Família (20-30 itens)", "Cesta Turbinada (35-60 itens)", "Kit Higiene", "Sacola Limpeza"])
        
        margem = st.slider("Margem de Lucro Desejada (%)", min_value=0.0, max_value=100.0, value=25.0, step=1.0)
        
        conn = get_connection()
        df_itens = pd.read_sql_query(f"SELECT p.id, (p.nome || ' - ' || p.marca) AS produto, il.quantidade, il.preco_unitario FROM itens_lote il JOIN produtos p ON il.produto_id = p.id WHERE il.lote_id = {lote_escolhido}", conn)
        conn.close()
        
        if not df_itens.empty:
            st.subheader("📋 Definição da Receita (Quantos de cada item vai em 1 Cesta)")
            
            receita = {}
            custo_cesta_unitario = 0.0
            capacidades_maximas = []
            
            for idx, row in df_itens.iterrows():
                col_rec1, col_rec2, col_rec3 = st.columns([3, 2, 2])
                with col_rec1:
                    st.write(f"**{row['produto']}** (Estoque no Lote: `{int(row['quantidade'])}` un)")
                with col_rec2:
                    qtd_na_cesta = st.number_input(f"Qtd por Cesta", min_value=1, value=1, key=f"rec_{row['id']}")
                with col_rec3:
                    subtotal_item = qtd_na_cesta * row['preco_unitario']
                    st.write(f"Custo no Kit: **R$ {subtotal_item:.2f}**")
                    
                custo_cesta_unitario += subtotal_item
                
                # Cálculo da capacidade limite por item (Gargalo de Estoque)
                cap_item = int(row['quantidade'] // qtd_na_cesta)
                capacidades_maximas.append(cap_item)
            
            # O menor valor de capacidade define o total máximo de cestas completas
            max_cestas_possiveis = min(capacidades_maximas) if capacidades_maximas else 0
            preco_venda_sugerido = custo_cesta_unitario * (1 + (margem / 100))
            lucro_unitario = preco_venda_sugerido - custo_cesta_unitario
            lucro_total = lucro_unitario * max_cestas_possiveis
            
            st.markdown("---")
            st.subheader("📊 Resultado do Rendimento Automático do Lote")
            
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("Cestas Possíveis (Gargalo)", f"{max_cestas_possiveis} Cestas", help="Definido pelo item de menor estoque no lote")
            with col_m2:
                st.metric("Custo de Produção (1 Cesta)", f"R$ {custo_cesta_unitario:.2f}")
            with col_m3:
                st.metric("Preço de Venda Sugerido", f"R$ {preco_venda_sugerido:.2f}", delta=f"{margem}% Margem")
            with col_m4:
                st.metric("Lucro Total Estimado", f"R$ {lucro_total:.2f}")

            st.markdown("---")
            st.subheader("Composição Detalhada do Lote no Banco de Dados")
            st.dataframe(df_itens[["produto", "quantidade", "preco_unitario"]], use_container_width=True)
    else:
        st.info("Nenhum lote cadastrado. Vá na aba 'Gestão de Lotes & Precificação' para registrar a primeira compra.")
