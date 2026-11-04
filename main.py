import streamlit as st
import pandas as pd
from datetime import datetime
from core.database import init_db, get_connection
import io

init_db()
st.set_page_config(page_title="Cestas Bom Dia - Boa Vista", page_icon="🛒", layout="wide")
st.title("🛒 Cestas Bom Dia - Gestão Operacional & Lotes")

# Dados padronizados oficiais com os 43 produtos e preços do Assaí e Atacadão
dados_completos = [
    {"Nome do Produto": "ARROZ 1KG", "Unidade": "KG", "Marca": "PRATO CHIC", "Preço Assaí": 3.39, "Preço Atacadão": 4.49},
    {"Nome do Produto": "FEIJÃO 1KG", "Unidade": "KG", "Marca": "KICALDO", "Preço Assaí": 5.62, "Preço Atacadão": 5.69},
    {"Nome do Produto": "AÇUCAR 1KG", "Unidade": "KG", "Marca": "CRISTAL SONORA", "Preço Assaí": 2.79, "Preço Atacadão": 3.35},
    {"Nome do Produto": "FARINHA", "Unidade": "UN", "Marca": "MANDIOCA DONA", "Preço Assaí": None, "Preço Atacadão": 4.29},
    {"Nome do Produto": "TRIGO 1KG", "Unidade": "KG", "Marca": "TRIGOLAR", "Preço Assaí": 4.70, "Preço Atacadão": 4.69},
    {"Nome do Produto": "OLEO 900ML", "Unidade": "FR", "Marca": "SERRA VERDE", "Preço Assaí": 7.49, "Preço Atacadão": 6.95},
    {"Nome do Produto": "SAL 1KG", "Unidade": "KG", "Marca": "FELICIA", "Preço Assaí": 2.25, "Preço Atacadão": 1.79},
    {"Nome do Produto": "MACARRÃO ESPAG. 400G", "Unidade": "PC", "Marca": "BOM SABOR", "Preço Assaí": 1.89, "Preço Atacadão": 2.09},
    {"Nome do Produto": "MOLHO TOMATE SC300G", "Unidade": "SC/G", "Marca": "BONARE", "Preço Assaí": 1.59, "Preço Atacadão": 1.59},
    {"Nome do Produto": "VINAGRE 500ML", "Unidade": "FR", "Marca": "VIRROSAS", "Preço Assaí": 3.19, "Preço Atacadão": 2.59},
    {"Nome do Produto": "CAFE 250GR", "Unidade": "PC", "Marca": "PILÃO", "Preço Assaí": 8.09, "Preço Atacadão": 9.99},
    {"Nome do Produto": "SARDINHA 125G", "Unidade": "LT", "Marca": "PALMEIRA", "Preço Assaí": 4.89, "Preço Atacadão": 5.59},
    {"Nome do Produto": "BOLACHA DOCE RECHEADA 80G", "Unidade": "PC", "Marca": "TRIGOLINO", "Preço Assaí": 1.69, "Preço Atacadão": 1.39},
    {"Nome do Produto": "BISCOITO SALGADO CREMCKER 300G", "Unidade": "PC", "Marca": "RACHEIRO", "Preço Assaí": 2.99, "Preço Atacadão": 3.99},
    {"Nome do Produto": "COMPOSTO LACTEO 400G", "Unidade": "PC", "Marca": "PURIBON", "Preço Assaí": 8.39, "Preço Atacadão": 11.89},
    {"Nome do Produto": "MIOJO 74G DVS SABOR", "Unidade": "UND", "Marca": "NOSSO SABOR LAMEN", "Preço Assaí": 1.23, "Preço Atacadão": 1.49},
    {"Nome do Produto": "FLOCÃO 500GR", "Unidade": "G", "Marca": "LIVRE FLOCOS", "Preço Assaí": 3.89, "Preço Atacadão": 3.89},
    {"Nome do Produto": "SELETA LEGUMES 170G", "Unidade": "LT", "Marca": "PREDILECTA", "Preço Assaí": 2.79, "Preço Atacadão": 3.29},
    {"Nome do Produto": "ACHOCOLATADO 200GR", "Unidade": "PC", "Marca": "APITI POWER", "Preço Assaí": 4.30, "Preço Atacadão": 4.65},
    {"Nome do Produto": "BISCOITO ROSQUINHA DOCE 300G", "Unidade": "PC", "Marca": "TRIGOLINO", "Preço Assaí": 4.29, "Preço Atacadão": 3.69},
    {"Nome do Produto": "MARGARINA 250G", "Unidade": "UND", "Marca": "PRIMOR", "Preço Assaí": 2.95, "Preço Atacadão": 3.29},
    {"Nome do Produto": "MARGARINA 500G", "Unidade": "UND", "Marca": "PRIMOR", "Preço Assaí": 4.99, "Preço Atacadão": 6.00},
    {"Nome do Produto": "PÃO FORMA 450G", "Unidade": "UND", "Marca": "PÃES DELÍCIA", "Preço Assaí": 6.99, "Preço Atacadão": 8.00},
    {"Nome do Produto": "REFRESCO PÓ 8G", "Unidade": "UND", "Marca": "SUKKI", "Preço Assaí": None, "Preço Atacadão": 0.39},
    {"Nome do Produto": "BANDEJA DE OVOS 30UND", "Unidade": "UND", "Marca": "GSL", "Preço Assaí": None, "Preço Atacadão": 11.59},
    {"Nome do Produto": "PASTA DE DENTES 70GR", "Unidade": "UND", "Marca": "EVEN TRI PROT", "Preço Assaí": 2.09, "Preço Atacadão": 2.49},
    {"Nome do Produto": "SABONETE 80GR", "Unidade": "UND", "Marca": "FRANCIS INTENSO", "Preço Assaí": 1.59, "Preço Atacadão": 1.99},
    {"Nome do Produto": "PAPEL HIGIÊNICO 4UND.", "Unidade": "UND", "Marca": "FLORAL", "Preço Assaí": 3.99, "Preço Atacadão": 2.90},
    {"Nome do Produto": "KIT SHAMPOO/CONDIC.", "Unidade": "UND", "Marca": "DABELLE", "Preço Assaí": 17.49, "Preço Atacadão": 15.91},
    {"Nome do Produto": "ESCOVA DE DENTES", "Unidade": "UND", "Marca": "SORRISO", "Preço Assaí": 3.99, "Preço Atacadão": 2.79},
    {"Nome do Produto": "FIO DENTAL", "Unidade": "UND", "Marca": "JADE PRO", "Preço Assaí": 8.95, "Preço Atacadão": 4.99},
    {"Nome do Produto": "DESODORANTE NEUTRO", "Unidade": "UND", "Marca": "ABOVE CREME", "Preço Assaí": 3.39, "Preço Atacadão": None},
    {"Nome do Produto": "PAPEL HIGIENICO COM 8UND", "Unidade": "UND", "Marca": "GIRASSOL 30M NEUTRO", "Preço Assaí": 6.29, "Preço Atacadão": 6.29},
    {"Nome do Produto": "ÁGUA SANITÁRIA 1 LT", "Unidade": "UND", "Marca": "BRINORT", "Preço Assaí": 2.65, "Preço Atacadão": 2.29},
    {"Nome do Produto": "DESINFETANTE 2LT", "Unidade": "UND", "Marca": "BRINORT EUCALIPTO", "Preço Assaí": 5.45, "Preço Atacadão": 5.29},
    {"Nome do Produto": "SABÃO EM BARRA 450G / 180G", "Unidade": "UND", "Marca": "GUAMÁ", "Preço Assaí": 4.49, "Preço Atacadão": 2.35},
    {"Nome do Produto": "SABÃO EM PÓ 400GR", "Unidade": "UND", "Marca": "LAV ROUPA PÓ SONHO", "Preço Assaí": 3.39, "Preço Atacadão": 1.80},
    {"Nome do Produto": "AMACIANTE 2LT", "Unidade": "UND", "Marca": "AMAC HIPER PLUS", "Preço Assaí": 5.79, "Preço Atacadão": 5.39},
    {"Nome do Produto": "MULTIÚSO 500ML", "Unidade": "UND", "Marca": "BRILUX MULTIUSO", "Preço Assaí": 3.99, "Preço Atacadão": 4.15},
    {"Nome do Produto": "ESPONJA", "Unidade": "UND", "Marca": "ESFRELUX C/4", "Preço Assaí": 0.75, "Preço Atacadão": 0.55},
    {"Nome do Produto": "PALHA DE AÇO", "Unidade": "UND", "Marca": "LUSTRO", "Preço Assaí": 1.55, "Preço Atacadão": 1.55},
    {"Nome do Produto": "DETERGENTE 500ML", "Unidade": "UND", "Marca": "BRILUX", "Preço Assaí": 1.85, "Preço Atacadão": 2.05},
    {"Nome do Produto": "DESINFETANTE 500ML", "Unidade": "UND", "Marca": "BRILUX EUCALIPTO", "Preço Assaí": 1.99, "Preço Atacadão": 2.79}
]

menu = st.sidebar.radio("Navegabilidade:", [
    "📥 Upload & Importação",
    "📦 Cadastrar Produtos & Marcas", 
    "🏭 Fornecedores & Preços", 
    "📊 Cotações & Histórico",
    "📦 Gestão de Lotes & Precificação",
    "🧩 Montagem de Kits"
])

if menu == "📥 Upload & Importação":
    st.header("📥 Importação Automatizada via Planilha Oficial")
    st.markdown("Faça o upload da **Planilha Padrão Oficial** para atualizar produtos e cotações de forma limpa.")
    
    # Gerador dinâmico de planilha em memória
    output = io.BytesIO()
    df_m = pd.DataFrame(dados_completos)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_m.to_excel(writer, index=False, sheet_name='Cotações')
    excel_bytes = output.getvalue()
    
    st.download_button(
        label="⬇️ Baixar Planilha Modelo Padrão Oficial",
        data=excel_bytes,
        file_name="Cestas_Bom_Dia_Template_Upload.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
        
    st.markdown("---")
    uploaded_file = st.file_uploader("Carregar Planilha Oficial Preenchida (.xlsx)", type=["xlsx"])
    
    if uploaded_file is not None:
        try:
            df_up = pd.read_excel(uploaded_file, sheet_name=0, engine="openpyxl")
            st.success(f"Planilha carregada com sucesso! {len(df_up)} produtos encontrados.")
            
            if st.button("🚀 Processar e Salvar Cotações Oficiais"):
                conn = get_connection()
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM cotacoes")
                cursor.execute("DELETE FROM itens_lote")
                cursor.execute("DELETE FROM produtos")
                conn.commit()
                
                count_prods = 0
                count_cots = 0
                
                for idx, row in df_up.iterrows():
                    nome_prod = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else ""
                    if not nome_prod or nome_prod.upper() in ["NAN", "NONE", "PRODUTO", "ITEM", "NOME DO PRODUTO"]:
                        continue
                        
                    unidade = str(row.iloc[1]).strip().upper() if len(row) > 1 and not pd.isna(row.iloc[1]) else "UN"
                    if not unidade or unidade in ["NAN", "NONE"]:
                        unidade = "UN"
                        
                    marca = str(row.iloc[2]).strip().upper() if len(row) > 2 and not pd.isna(row.iloc[2]) else "GERAL"
                    if not marca or marca in ["NAN", "NONE"]:
                        marca = "GERAL"

                    cursor.execute(
                        "INSERT INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)",
                        (nome_prod.upper(), marca, unidade, nome_prod.upper())
                    )
                    conn.commit()
                    count_prods += 1
                    
                    cursor.execute("SELECT id FROM produtos WHERE nome = ? AND marca = ?", (nome_prod.upper(), marca))
                    p_res = cursor.fetchone()
                    if not p_res:
                        continue
                    produto_db_id = p_res[0]
                    
                    # Preço Assaí
                    if len(row) > 3:
                        preco_assai = row.iloc[3]
                        if not pd.isna(preco_assai) and isinstance(preco_assai, (int, float)) and preco_assai > 0:
                            cursor.execute("SELECT id FROM fornecedores WHERE nome = 'Assaí Atacadista'")
                            f_res = cursor.fetchone()
                            if f_res:
                                cursor.execute(
                                    "INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, date('now'))",
                                    (produto_db_id, f_res[0], float(preco_assai))
                                )
                                count_cots += 1
                            
                    # Preço Atacadão
                    if len(row) > 4:
                        preco_atacadao = row.iloc[4]
                        if not pd.isna(preco_atacadao) and isinstance(preco_atacadao, (int, float)) and preco_atacadao > 0:
                            cursor.execute("SELECT id FROM fornecedores WHERE nome = 'Atacadão'")
                            f_res = cursor.fetchone()
                            if f_res:
                                cursor.execute(
                                    "INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, date('now'))",
                                    (produto_db_id, f_res[0], float(preco_atacadao))
                                )
                                count_cots += 1
                            
                conn.commit()
                conn.close()
                st.success(f"✅ Importação oficial concluída com sucesso! {count_prods} produtos e {count_cots} cotações gravadas.")
        except Exception as e:
            st.error(f"Erro crítico ao processar a planilha oficial: {e}")

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
        st.info("Nenhuma cotação registada. Faça o upload da planilha oficial primeiro.")

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
                custo_total_lote = custo_produtos 
                
                cursor.execute("INSERT INTO lotes (nome_lote, data_compra, custo_total) VALUES (?, date('now'), ?)", (nome_lote_input, custo_total_lote))
                lote_id = cursor.lastrowid
                
                for p_id, qtd, preco in lote_itens_salvar:
                    cursor.execute("INSERT INTO itens_lote (lote_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)", (lote_id, p_id, preco))
                
                conn.commit()
                conn.close()
                st.success(f"✅ Lote '{nome_lote_input}' salvo com sucesso! Custo de produtos: R$ {custo_produtos:.2f}")
    else:
        st.warning("Nenhuma cotação encontrada. Faça o upload da planilha oficial primeiro.")

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
            
            frete_fixo = 10.89
            custo_frete_por_cesta = frete_fixo / max_cestas_possiveis if max_cestas_possiveis > 0 else 0.0
            custo_total_unitario_cesta = custo_produtos_cesta + custo_frete_por_cesta
            
            preco_venda_sugerido = custo_total_unitario_cesta * (1 + (margem / 100))
            
            st.markdown("---")
            st.subheader("📊 Painel de Sugestão de Venda e Custos")
            
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
