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
                    if len(row) < 5:
                        continue
                    
                    # Varre as colunas iniciais para isolar estritamente o produto real
                    nome_prod = ""
                    unidade = "UN"
                    marca = "Geral"
                    
                    for col_idx in [2, 1, 3]:
                        if col_idx < len(row) and not pd.isna(row.iloc[col_idx]):
                            val = str(row.iloc[col_idx]).strip()
                            val_up = val.upper()
                            # Rejeita termos de categorias, unidades puras ou cabeçalhos
                            if val and val_up not in ["NAN", "NONE", "PRODUTO", "ITEM", "KG", "UN", "LT", "PCT", "UND", "SC", "CX", "ALIMENTO", "LIMPEZA", "HIGIENE", "KG - ALIMENTO", "UN - ALIMENTO"]:
                                if not any(cat in val_up for cat in ["ALIMENTO", "LIMPEZA", "HIGIENE"]) and len(val) > 1:
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
    prods = pd.read_sql_query("SELECT id, (nome || ' - ' || marca) AS item FROM produtos", conn)
    fornecs = pd.read_sql_query("SELECT id, nome FROM fornecedores", conn)
    conn.close()
    if not prods.empty and not fornecs.empty:
        with st.form("form_cot"):
            p = st.selectbox("Produto / Marca", prods["id"], format_func=lambda x: prods[prods["id"] == x]["item"].values[0])
            f = st.selectbox("Atacadista", fornecs["id"], format_func=lambda x: fornecs[fornecs["id"] == x]["nome"].values[0])
            pr = st.number_input("Preço Unitário (R$)", min_value=0.01, step=0.10)
            if st.form_submit_button("Salvar Cotação"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, date('now'))", (p, f, pr))
                conn.commit()
                conn.close()
                st.success("Cotação salva!")
                st.rerun()

elif menu == "📊 Cotações & Histórico":
    st.header("📊 Histórico Temporal de Preços")
    conn = get_connection()
    df = pd.read_sql_query("SELECT c.data_cotacao, (p.nome || ' - ' || p.marca) AS prod, f.nome AS atac, c.preco FROM cotacoes c JOIN produtos p ON c.produto_id=p.id JOIN fornecedores f ON c.fornecedor_id=f.id ORDER BY c.data_cotacao DESC", conn)
    conn.close()
    if not df.empty: 
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhuma cotação registada.")

elif menu == "📦 Gestão de Lotes & Precificação":
    st.header("📦 Controle de Lotes de Compra & Custos Fechados")
    st.info("Aqui você gerencia os lotes semanais comprados com base nos menores preços e calcula o rendimento das cestas.")

elif menu == "🧩 Montagem de Kits":
    st.header("🧩 Montagem de Kits e Cestas")
    st.info("Montagem de kits e aplicação de margem de lucro ativa.")
