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
    st.markdown("Faça o upload da planilha padronizada para atualizar produtos e cotações da data.")
    
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
            
            if st.button("🚀 Processar e Salvar Cotações da Data"):
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
                st.success(f"✅ Cotações salvas com sucesso! {count_prods} produtos e {count_cots} preços registrados.")
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
    st.header("📦 Sugestão de Compra: Menores Preços da Cotação")
    st.markdown("O sistema puxa automaticamente os produtos com os **menores preços** das cotações vigentes para montar o seu lote.")
    
    nome_lote_input = st.text_input("Identificação do Lote", value=f"Lote - {datetime.now().strftime('%d/%m/%Y')}")
    
    conn = get_connection()
    # Puxa automaticamente o menor preço de cada produto entre os fornecedores da cotação
    df_sugestao = pd.read_sql_query("""
        SELECT p.id as produto_id, (p.nome || ' - ' || p.marca) AS item, MIN(c.preco) as menor_preco, f.nome as fornecedor
        FROM cotacoes c
        JOIN produtos p ON c.produto_id = p.id
        JOIN fornecedores f ON c.fornecedor_id = f.id
        GROUP BY p.id
        ORDER BY p.nome ASC
    """, conn)
    conn.close()
    
    if not df_sugestao.empty:
        with st.form("form_lote_auto"):
            st.subheader("Itens Sugeridos (Baseados no Menor Preço)")
            
            lote_itens_salvar = []
            for idx, row in df_sugestao.iterrows():
                cols = st.columns([3, 2, 2, 2])
                with cols[0]:
                    st.markdown(f"**{row['item']}**  \n*Fornecedor:* `{row['fornecedor']}`")
                with cols[1]:
                    qtd_compra = st.number_input(f"Qtd", min_value=0.0, value=10.0, key=f"lote_qtd_{idx}")
                with cols[2]:
                    preco_sugerido = st.number_input(f"Preço Unit.", min_value=0.01, value=float(row['menor_preco']), key=f"lote_preco_{idx}")
                with cols[3]:
                    st.markdown(f"**Subtotal:**  \nR$ {qtd_compra * preco_sugerido:.2f}")
                
                if qtd_compra > 0:
                    lote_itens_salvar.append((row['produto_id'], qtd_compra, preco_sugerido))
                
            if st.form_submit_button("💾 Salvar Lote Fechado no Estoque"):
                conn = get_connection()
                cursor = conn.cursor()
                custo_produtos = sum([q * p for _, q, p in lote_itens_salvar])
                custo_total_lote = custo_produtos # O frete será adicionado na visão do kit
                
                cursor.execute("INSERT INTO lotes (nome_lote, data_compra, custo_total) VALUES (?, date('now'), ?)", (nome_lote_input, custo_total_lote))
                lote_id = cursor.lastrowid
                
                for p_id, qtd, preco in lote_itens_salvar:
                    cursor.execute("INSERT INTO itens_lote (lote_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)", (lote_id, p_id, qtd, preco))
                
                conn.commit()
                conn.close()
                st.success(f"✅ Lote '{nome_lote_input}' salvo com sucesso! Custo de produtos: R$ {custo_produtos:.2f}")
    else:
        st.warning("Nenhuma cotação encontrada. Faça o upload da planilha primeiro.")

elif menu == "🧩 Montagem de Kits":
    st.header("🧩 Cálculo Automático de Rendimento, Frete & Sugestão de Venda")
    st.markdown("O sistema contabiliza automaticamente o número de cestas possíveis, adiciona o **frete fixo de R$ 10,89** e exibe o preço sugerido com margem.")
    
    conn = get_connection()
    df_lotes = pd.read_sql_query("SELECT id, nome_lote, custo_total FROM lotes ORDER BY id DESC", conn)
    conn.close()
    
    if not df_lotes.empty:
        lote_escolhido = st.selectbox("Selecione o Lote de Referência", df_lotes["id"], format_func=lambda x: df_lotes[df_lotes["id"] == x]["nome_lote"].values[0])
        
        modelo_cesta = st.selectbox("Selecione o Modelo da Cesta", ["Cesta Econômica (12-14 itens)", "Cesta Família (20-30 itens)", "Cesta Turbinada (35-60 itens)", "Kit Higiene", "Sacola Limpeza"])
        
        margem = st.slider("Margem de Lucro Desejada (%)", min_value=0.0, max_value=200.0, value=25.0, step=1.0)
        
        conn = get_connection()
        df_itens = pd.read_sql_query(f"SELECT p.id, (p.nome || ' - ' || p.marca) AS produto, il.quantidade, il.preco_unitario FROM itens_lote il JOIN produtos p ON il.produto_id = p.id WHERE il.lote_id = {lote_escolhido}", conn)
        conn.close()
        
        if not df_itens.empty:
            st.markdown("---")
            st.subheader("📋 Composição da Receita por Cesta")
            
            custo_produtos_cesta = 0.0
            capacidades_maximas = []
            
            for idx, row in df_itens.iterrows():
                with st.container():
                    col_p, col_c, col_q, col_sub = st.columns([3, 2, 2, 2])
                    with col_p:
                        st.markdown(f"**{row['produto']}**  \n*(Estoque Lote: {int(row['quantidade'])} un)*")
                    with col_c:
                        custo_real_unit = st.number_input(f"Custo Unit.", min_value=0.01, value=float(row['preco_unitario']), key=f"custo_{idx}_{row['id']}")
                    with col_q:
                        qtd_na_cesta = st.number_input(f"Qtd por Cesta", min_value=0, value=1, key=f"rec_{idx}_{row['id']}")
                    with col_sub:
                        subtotal_item = qtd_na_cesta * custo_real_unit
                        st.markdown(f"**Subtotal:**  \nR$ {subtotal_item:.2f}")
                    
                    custo_produtos_cesta += subtotal_item
                    
                    if qtd_na_cesta > 0:
                        cap_item = int(row['quantidade'] // qtd_na_cesta)
                        capacidades_maximas.append(cap_item)
                    
                    st.divider()
            
            max_cestas_possiveis = min(capacidades_maximas) if capacidades_maximas else 0
            
            # Adiciona o frete fixo de R$ 10,89 rateado por cesta (ou total somado)
            frete_fixo = 10.89
            custo_frete_por_cesta = frete_fixo / max_cestas_possiveis if max_cestas_possiveis > 0 else 0.0
            custo_total_unitario_cesta = custo_produtos_cesta + custo_frete_por_cesta
            
            preco_venda_sugerido = custo_total_unitario_cesta * (1 + (margem / 100))
            
            st.markdown("---")
            st.subheader("📊 Painel de Sugestão de Venda e Custos")
            
            # Quadrado / Card em destaque com o preço sugerido
            st.markdown(f"""
            <div style="background-color: #1e2530; padding: 25px; border-radius: 12px; border: 2px solid #28a745; text-align: center; margin-bottom: 20px;">
                <h3 style="color: #ffffff; margin: 0; font-size: 20px;">PREÇO SUGERIDO DE VENDA POR CESTA</h3>
                <h1 style="color: #28a745; font-size: 42px; margin: 10px 0;">R$ {preco_venda_sugerido:.2f}</h1>
                <p style="color: #adb5bd; margin: 0; font-size: 14px;">Com base em {max_cestas_possiveis} cestas possíveis | Margem de {margem}% | Frete incluso (R$ 10,89)</p>
            </div>
            """, unsafe_allow_html=True)
            
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("Cestas Possíveis", f"{max_cestas_possiveis} Cestas")
            with col_m2:
                st.metric("Custo dos Produtos", f"R$ {custo_produtos_cesta:.2f}")
            with col_m3:
                st.metric("Frete Rateado", f"R$ {custo_frete_por_cesta:.2f}")
            with col_m4:
                st.metric("Custo Total Unitário", f"R$ {custo_total_unitario_cesta:.2f}")
    else:
        st.info("Nenhum lote cadastrado. Vá na aba 'Gestão de Lotes & Precificação' para registrar a compra.")
