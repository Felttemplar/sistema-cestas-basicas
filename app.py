import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from core.database import init_db, get_connection, deletar_fornecedor
from core.engine import calcular_custo_cesta, obter_parametros, salvar_parametro

init_db()

st.set_page_config(page_title="Gestão Cestas Bom Dia - Boa Vista/RR", page_icon="🛒", layout="wide")

st.title("🛒 Cestas Bom Dia - Sistema de Cotação, Precificação e Vendas")
st.markdown("Gestão de fornecedores, frete por zonas, comissões, cotações, pedidos e estoque em Boa Vista/RR.")

# Tabela de Taxas dos Canais de Venda
TAXAS_CANAL = {
    "Online - Instagram": 0.0,
    "Online - Pigz": 10.0,
    "Online - iFood": 12.0,
    "Online - Zé Delivery": 8.0,
    "Online - Facebook Marketplace": 0.0,
    "Presencial - Venda Física (In Loco / PAP)": 0.0
}

st.sidebar.header("Navegação")
menu = st.sidebar.radio("Ir para:", [
    "📈 Dashboard & Projeções",
    "📦 Gestão & Alerta de Estoque",
    "📊 Cotações, Histórico & Precificação", 
    "🛒 Registro de Pedidos / Vendas",
    "📁 Importar Planilhas (Excel / CSV)",
    "📦 Cadastrar Produtos & Substitutos", 
    "🏭 Fornecedores & Preços", 
    "📋 Composição de Cestas & Kits"
])

params = obter_parametros()

# ==========================================
# ABA 0: DASHBOARD & PROJEÇÕES
# ==========================================
if menu == "📈 Dashboard & Projeções":
    st.header("📈 Dashboard Analítico & Desempenho Comercial")
    
    conn = get_connection()
    df_vendas = pd.read_sql_query('''
        SELECT 
            v.id, 
            t.nome AS cesta, 
            v.quantidade_vendida, 
            v.preco_unitario_praticado, 
            (v.quantidade_vendida * v.preco_unitario_praticado) AS faturamento_total,
            v.canal_venda, 
            v.vendedor,
            v.zona_entrega,
            v.taxa_canal_percentual,
            v.comissao_percentual,
            v.data_venda
        FROM vendas v
        JOIN tipos_cesta t ON v.tipo_cesta_id = t.id
    ''', conn)
    conn.close()
    
    if df_vendas.empty:
        st.info("⚠️ Nenhum pedido/venda registrado até o momento. Registre novos pedidos na aba 'Registro de Pedidos / Vendas'.")
    else:
        # Cálculo de Margem Líquida Real descontando taxas de canal e comissão
        df_vendas['valor_taxa_canal'] = df_vendas['faturamento_total'] * (df_vendas['taxa_canal_percentual'] / 100.0)
        df_vendas['valor_comissao'] = df_vendas['faturamento_total'] * (df_vendas['comissao_percentual'] / 100.0)
        df_vendas['faturamento_liquido'] = df_vendas['faturamento_total'] - df_vendas['valor_taxa_canal'] - df_vendas['valor_comissao']

        total_faturamento = df_vendas['faturamento_total'].sum()
        total_liquido = df_vendas['faturamento_liquido'].sum()
        total_unidades = df_vendas['quantidade_vendida'].sum()
        ticket_medio = total_faturamento / df_vendas['id'].count() if df_vendas['id'].count() > 0 else 0.0
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("💰 Faturamento Bruto", f"R$ {total_faturamento:.2f}")
        k2.metric("💵 Receita Líquida Real", f"R$ {total_liquido:.2f}")
        k3.metric("📦 Cestas/Kits Vendidos", f"{total_unidades} un")
        k4.metric("🎯 Ticket Médio por Venda", f"R$ {ticket_medio:.2f}")
        
        st.markdown("---")
        
        c_graf1, c_graf2 = st.columns(2)
        with c_graf1:
            st.subheader("📊 Faturamento por Vendedor")
            df_vendedor = df_vendas.groupby('vendedor')['faturamento_total'].sum().reset_index()
            st.bar_chart(df_vendedor.set_index('vendedor'))
            
        with c_graf2:
            st.subheader("📍 Vendas por Zona de Boa Vista")
            df_zonas = df_vendas.groupby('zona_entrega')['faturamento_total'].sum().reset_index()
            st.bar_chart(df_zonas.set_index('zona_entrega'))
            
        st.markdown("---")
        c_graf3, c_graf4 = st.columns(2)
        with c_graf3:
            st.subheader("📱 Rentabilidade Líquida por Canal de Venda")
            df_canais_liq = df_vendas.groupby('canal_venda')['faturamento_liquido'].sum().reset_index()
            fig_canal = px.bar(df_canais_liq, x='canal_venda', y='faturamento_liquido', 
                               labels={'canal_venda':'Canal', 'faturamento_liquido':'Receita Líquida (R$)'},
                               color='faturamento_liquido', color_continuous_scale='Greens')
            st.plotly_chart(fig_canal, use_container_width=True)
            
        with c_graf4:
            st.subheader("🏆 Kits Mais Vendidos")
            df_kits = df_vendas.groupby('cesta')['quantidade_vendida'].sum().reset_index()
            st.bar_chart(df_kits.set_index('cesta'))

# ==========================================
# ABA 1: GESTÃO & ALERTA DE ESTOQUE (SUGESTÃO 1)
# ==========================================
elif menu == "📦 Gestão & Alerta de Estoque":
    st.header("📦 Controle de Estoque & Alerta de Ruptura de Insumos")
    st.markdown("Monitore a quantidade disponível de cada insumo no estoque de Boa Vista e evite a falta de produtos nas cestas.")
    
    conn = get_connection()
    df_estoque = pd.read_sql_query("SELECT id, nome, grupo_equivalencia, unidade, estoque_atual, estoque_minimo FROM produtos", conn)
    conn.close()
    
    if df_estoque.empty:
        st.info("Nenhum produto cadastrado.")
    else:
        # Identifica produtos com risco de ruptura
        df_criticos = df_estoque[df_estoque['estoque_atual'] <= df_estoque['estoque_minimo']]
        
        if not df_criticos.empty:
            st.error(f"⚠️ **ATENÇÃO:** Existe(m) {len(df_criticos)} item(ns) com estoque crítico ou abaixo do mínimo de reposição!")
            st.dataframe(df_criticos.style.format({'estoque_atual': '{:.1f}', 'estoque_minimo': '{:.1f}'}), use_container_width=True)
            st.markdown("---")
            
        st.subheader("📋 Tabela Geral de Estoque de Insumos")
        st.dataframe(df_estoque.style.format({'estoque_atual': '{:.1f}', 'estoque_minimo': '{:.1f}'}), use_container_width=True)
        
        st.markdown("---")
        st.subheader("🔄 Entrada / Atualização de Estoque")
        with st.form("form_atualiza_estoque"):
            p_sel = st.selectbox("Selecione o Produto", df_estoque['nome'])
            p_id_est = int(df_estoque[df_estoque['nome'] == p_sel]['id'].values[0])
            qtd_adicionar = st.number_input("Adicionar ao Estoque (Un/Kg/Pct)", value=50.0, step=5.0)
            btn_est = st.form_submit_button("Atualizar Estoque")
            
            if btn_est:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE produtos SET estoque_atual = estoque_atual + ? WHERE id = ?", (qtd_adicionar, p_id_est))
                conn.commit()
                conn.close()
                st.success(f"Estoque do item '{p_sel}' atualizado com sucesso!")
                st.rerun()

# ==========================================
# ABA 2: COTAÇÕES, HISTÓRICO & PRECIFICAÇÃO (SUGESTÃO 3)
# ==========================================
elif menu == "📊 Cotações, Histórico & Precificação":
    st.header("📊 Análise de Custo, Impostos e Histórico de Preços")
    
    tab_p1, tab_p2 = st.tabs(["🏷️ Precificação de Kits", "📈 Histórico Temporal de Preços (Atacadistas)"])
    
    with tab_p1:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            margem = st.slider("Margem de Lucro (%)", 5.0, 60.0, float(params.get("margem_lucro_padrao", 25.0)), 1.0)
        with col2:
            embalagem = st.number_input("Custo Embalagem (R$)", value=float(params.get("custo_embalagem", 3.50)), step=0.50)
        with col3:
            frete = st.number_input("Frete Médio Rateado (R$)", value=float(params.get("frete_medio", 5.00)), step=0.50)
        with col4:
            imposto = st.number_input("Imposto Estimado - ICMS/CBS (%)", value=float(params.get("imposto_padrao", 5.0)), step=0.5)
            
        conn = get_connection()
        tipos_cesta = pd.read_sql_query("SELECT id, nome FROM tipos_cesta", conn)
        conn.close()
        
        if tipos_cesta.empty:
            st.warning("Cadastre tipos de cesta primeiro.")
        else:
            cesta_escolhida = st.selectbox("Selecione a Cesta ou Kit para Orçar", tipos_cesta['nome'])
            cesta_id = int(tipos_cesta[tipos_cesta['nome'] == cesta_escolhida]['id'].values[0])
            
            df_itens, custo_insumos, custo_total, valor_lucro, preco_venda = calcular_custo_cesta(cesta_id, margem, embalagem, frete)
            
            if df_itens.empty:
                st.info("⚠️ Nenhuma cotação cadastrada para os itens desta cesta ainda. Vá na aba 'Fornecedores & Preços' ou 'Importar Planilhas' para preencher.")
            else:
                valor_imposto = preco_venda * (imposto / 100.0)
                preco_venda_final = preco_venda + valor_imposto
                
                st.subheader(f"Resultado para: {cesta_escolhida}")
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Custo Insumos", f"R$ {custo_insumos:.2f}")
                m2.metric("Custo Total", f"R$ {custo_total:.2f}")
                m3.metric("Lucro Líquido", f"R$ {valor_lucro:.2f}")
                m4.metric("Impostos", f"R$ {valor_imposto:.2f}")
                m5.metric("🏷️ Preço Final Sugerido", f"R$ {preco_venda_final:.2f}")
                
                st.markdown("---")
                st.markdown("### Detalhes dos Menores Preços Encontrados por Grupo")
                tabela_exibicao = df_itens[['produto', 'grupo_equivalencia', 'quantidade', 'unidade', 'menor_preco', 'fornecedor', 'subtotal']].copy()
                tabela_exibicao.columns = ['Produto', 'Grupo / Categoria', 'Qtd', 'Un', 'Menor Preço Un.', 'Atacadista Vencedor', 'Subtotal']
                st.dataframe(tabela_exibicao.style.format({
                    'Menor Preço Un.': 'R$ {:.2f}',
                    'Subtotal': 'R$ {:.2f}',
                    'Qtd': '{:.1f}'
                }), use_container_width=True)

    with tab_p2:
        st.subheader("📈 Inteligência de Mercado: Histórico de Variação de Preço nos Atacadistas")
        conn = get_connection()
        df_hist = pd.read_sql_query('''
            SELECT c.data_cotacao, p.nome AS produto, f.nome AS atacadista, c.preco
            FROM cotacoes c
            JOIN produtos p ON c.produto_id = p.id
            JOIN fornecedores f ON c.fornecedor_id = f.id
            ORDER BY c.data_cotacao ASC
        ''', conn)
        conn.close()
        
        if df_hist.empty:
            st.info("Nenhuma cotação cadastrada para exibir o histórico.")
        else:
            prod_filtro = st.selectbox("Selecione o produto para analisar a oscilação:", df_hist['produto'].unique())
            df_prod_hist = df_hist[df_hist['produto'] == prod_filtro]
            
            fig_hist = px.line(df_prod_hist, x='data_cotacao', y='preco', color='atacadista', markers=True,
                               title=f"Evolução do Preço do Item: {prod_filtro} (R$)",
                               labels={'data_cotacao':'Data da Cotação', 'preco':'Preço Unitário (R$)', 'atacadista':'Atacadista'})
            st.plotly_chart(fig_hist, use_container_width=True)

# ==========================================
# ABA 3: REGISTRO DE PEDIDOS / VENDAS (SUGESTÕES 2 E 4)
# ==========================================
elif menu == "🛒 Registro de Pedidos / Vendas":
    st.header("🛒 Registro de Pedidos & Geração de Orçamento em PDF")
    st.markdown("Registre novos pedidos especificando a **Zona de Boa Vista**, o **Vendedor** e o **Canal de Venda** (descontando automaticamente do estoque).")
    
    conn = get_connection()
    tipos_cesta = pd.read_sql_query("SELECT id, nome FROM tipos_cesta", conn)
    conn.close()
    
    if tipos_cesta.empty:
        st.warning("Cadastre tipos de cesta primeiro.")
    else:
        with st.form("form_venda"):
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                cesta_venda = st.selectbox("Cesta / Kit Vendido", tipos_cesta['nome'])
                cesta_id_venda = int(tipos_cesta[tipos_cesta['nome'] == cesta_venda]['id'].values[0])
                qtd_vendida = st.number_input("Quantidade Vendida", min_value=1, value=1, step=1)
                preco_praticado = st.number_input("Preço Unitário Praticado (R$)", min_value=0.01, value=85.00, step=1.00)
                
            with col_v2:
                vendedor = st.selectbox("Vendedor Responsável", ["Otávio (Online)", "JC (PAP)", "Thiago (PAP)", "Venda Direta / Balcão"])
                zona = st.selectbox("Zona de Entrega (Boa Vista)", [
                    "Zona 1 - Centro / Caçari / Paraviana",
                    "Zona 2 - Caranã / Cauamé / Aeroporto",
                    "Zona 3 - Pintolândia / Santa Luzia / Laura Moreira",
                    "Zona 4 - Raiar do Sol / Nova Cidade / Bela Vista",
                    "Zona 5 - Cidade Satélite / Murilo Silva",
                    "Zona 6 - Operário / Jardim Equatorial",
                    "Zona 7 - Cambará / Liberdade / Mecejana",
                    "Zona 8 - Outras Regiões / Interior"
                ])
                canal = st.selectbox("Canal de Venda", list(TAXAS_CANAL.keys()))
                
            taxa_canal = TAXAS_CANAL[canal]
            comissao_perc = st.number_input("Comissão do Vendedor (%)", min_value=0.0, max_value=20.0, value=2.5, step=0.5)
            btn_registrar_venda = st.form_submit_button("Salvar Pedido / Dar Baixa no Estoque")
            
            if btn_registrar_venda:
                data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
                conn = get_connection()
                cursor = conn.cursor()
                
                # Salvar Venda
                cursor.execute('''
                    INSERT INTO vendas (tipo_cesta_id, quantidade_vendida, preco_unitario_praticado, canal_venda, vendedor, zona_entrega, taxa_canal_percentual, comissao_percentual, data_venda)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (cesta_id_venda, qtd_vendida, preco_praticado, canal, vendedor, zona, taxa_canal, comissao_perc, data_atual))
                
                # Baixa Automatica de Estoque dos Insumos
                cursor.execute('''
                    SELECT cc.produto_id, cc.quantidade
                    FROM composicao_cesta cc
                    WHERE cc.tipo_cesta_id = ?
                ''', (cesta_id_venda,))
                itens_cesta = cursor.fetchall()
                
                for prod_id_item, qtd_insumo in itens_cesta:
                    qtd_total_descontar = qtd_insumo * qtd_vendida
                    cursor.execute("UPDATE produtos SET estoque_atual = estoque_atual - ? WHERE id = ?", (qtd_total_descontar, prod_id_item))
                    
                conn.commit()
                conn.close()
                st.success(f"Pedido de {qtd_vendida}x '{cesta_venda}' registrado! Estoque atualizado automaticamente.")
                st.rerun()
                
        st.markdown("---")
        st.subheader("📊 Histórico de Pedidos e Vendas Realizadas")
        conn = get_connection()
        df_vendas = pd.read_sql_query('''
            SELECT 
                v.id, 
                v.data_venda,
                t.nome AS cesta, 
                v.quantidade_vendida, 
                v.preco_unitario_praticado, 
                (v.quantidade_vendida * v.preco_unitario_praticado) AS faturamento_total,
                v.vendedor,
                v.canal_venda, 
                v.zona_entrega
            FROM vendas v
            JOIN tipos_cesta t ON v.tipo_cesta_id = t.id
            ORDER BY v.data_venda DESC
        ''', conn)
        conn.close()
        
        if df_vendas.empty:
            st.info("Nenhum pedido ou venda registrado até o momento.")
        else:
            st.dataframe(df_vendas.style.format({
                'preco_unitario_praticado': 'R$ {:.2f}',
                'faturamento_total': 'R$ {:.2f}'
            }), use_container_width=True)

# ==========================================
# ABA 4: IMPORTAR PLANILHAS (EXCEL / CSV)
# ==========================================
elif menu == "📁 Importar Planilhas (Excel / CSV)":
    st.header("📁 Importação de Cotações via Excel / Google Sheets")
    st.markdown("Faça o upload do arquivo .xlsx preenchido para atualizar os preços dos atacadistas no sistema.")
    
    file_upload = st.file_uploader("Selecione o arquivo Excel de Cotação", type=["xlsx", "xls", "csv"])
    
    if file_upload is not None:
        try:
            if file_upload.name.endswith('.csv'):
                df_upload = pd.read_csv(file_upload)
            else:
                df_upload = pd.read_excel(file_upload, skiprows=3)
                
            st.subheader("Pré-visualização dos Dados Carregados:")
            st.dataframe(df_upload.head(10), use_container_width=True)
            
            if st.button("🚀 Processar e Atualizar Cotações no Banco de Dados"):
                conn = get_connection()
                cursor = conn.cursor()
                
                count_cot = 0
                data_hoje = datetime.now().strftime("%Y-%m-%d")
                cols_fornec = [c for c in df_upload.columns if c not in ["ID Produto", "Produto / Item", "Unidade", "Grupo / Categoria"]]
                
                for index, row in df_upload.iterrows():
                    prod_nome = row.get("Produto / Item")
                    grupo = row.get("Grupo / Categoria")
                    unidade = row.get("Unidade", "UN")
                    
                    if pd.isna(prod_nome) or pd.isna(grupo):
                        continue
                        
                    cursor.execute("SELECT id FROM produtos WHERE nome = ?", (prod_nome,))
                    res_prod = cursor.fetchone()
                    if res_prod:
                        prod_id = res_prod[0]
                    else:
                        cursor.execute("INSERT INTO produtos (nome, unidade, grupo_equivalencia) VALUES (?, ?, ?)", (prod_nome, unidade, grupo))
                        prod_id = cursor.lastrowid
                        
                    for f_nome in cols_fornec:
                        preco_val = row.get(f_nome)
                        if pd.notna(preco_val) and str(preco_val).strip() != "":
                            try:
                                preco_float = float(preco_val)
                                cursor.execute("SELECT id FROM fornecedores WHERE nome = ?", (f_nome,))
                                res_f = cursor.fetchone()
                                if res_f:
                                    f_id = res_f[0]
                                else:
                                    cursor.execute("INSERT INTO fornecedores (nome, telefone) VALUES (?, ?)", (f_nome, "Atacado"))
                                    f_id = cursor.lastrowid
                                    
                                cursor.execute("INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, ?)",
                                               (prod_id, f_id, preco_float, data_hoje))
                                count_cot += 1
                            except ValueError:
                                pass
                                
                conn.commit()
                conn.close()
                st.success(f"Sucesso! {count_cot} cotações atualizadas no banco de dados!")
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")

# ==========================================
# ABA 5: CADASTRAR PRODUTOS E SUBSTITUTOS
# ==========================================
elif menu == "📦 Cadastrar Produtos & Substitutos":
    st.header("📦 Cadastro de Produtos e Grupos de Substituição")
    
    with st.form("form_produto"):
        nome_prod = st.text_input("Nome do Produto (Ex: Arroz Camil 5kg, Sabonete Lux 85g)")
        unidade = st.selectbox("Unidade de Medida", ["UN", "PCT", "KG", "L", "CX"])
        grupo_eq = st.text_input("Grupo de Equivalência (Ex: Arroz 5kg, Feijão 1kg, Sabonete)")
        est_inicial = st.number_input("Estoque Inicial", min_value=0.0, value=50.0, step=5.0)
        est_minimo = st.number_input("Estoque Mínimo de Reposição", min_value=0.0, value=10.0, step=5.0)
        
        submitted = st.form_submit_button("Cadastrar Produto")
        if submitted:
            if nome_prod and grupo_eq:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO produtos (nome, unidade, grupo_equivalencia, estoque_atual, estoque_minimo) VALUES (?, ?, ?, ?, ?)", 
                               (nome_prod, unidade, grupo_eq, est_inicial, est_minimo))
                conn.commit()
                conn.close()
                st.success(f"Produto '{nome_prod}' cadastrado com sucesso!")
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios.")
                
    st.markdown("---")
    st.subheader("Produtos Cadastrados")
    conn = get_connection()
    df_prods = pd.read_sql_query("SELECT id, nome, unidade, grupo_equivalencia, estoque_atual, estoque_minimo FROM produtos", conn)
    conn.close()
    st.dataframe(df_prods, use_container_width=True)

# ==========================================
# ABA 6: FORNECEDORES & PREÇOS
# ==========================================
elif menu == "🏭 Fornecedores & Preços":
    st.header("🏭 Atacadistas, Distribuidoras e Cotações")
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Atacadista", "✏️ Atualizar / Gerenciar Atacadistas", "💰 Registrar Cotação de Preço"])
    
    with tab1:
        with st.form("form_fornecedor"):
            f_nome = st.text_input("Nome do Atacadista / Distribuidora (Ex: Atacadão, Assaí, Nova Era)")
            f_tel = st.text_input("Contato / Telefone / Tipo (Ex: Atacado, Varejo)")
            btn_f = st.form_submit_button("Salvar Atacadista")
            if btn_f and f_nome:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO fornecedores (nome, telefone) VALUES (?, ?)", (f_nome, f_tel))
                    conn.commit()
                    conn.close()
                    st.success(f"Atacadista '{f_nome}' cadastrado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

    with tab2:
        st.subheader("Atualizar ou Excluir Atacadistas Cadastrados")
        conn = get_connection()
        df_fornecs = pd.read_sql_query("SELECT id, nome, telefone FROM fornecedores", conn)
        conn.close()
        
        if df_fornecs.empty:
            st.info("Nenhum fornecedor cadastrado.")
        else:
            for index, row in df_fornecs.iterrows():
                with st.expander(f"🏢 {row['nome']} (Tel/Tipo: {row['telefone']})"):
                    with st.form(f"form_edit_fornec_{row['id']}"):
                        novo_nome = st.text_input("Nome do Atacadista", value=row['nome'], key=f"nome_{row['id']}")
                        novo_tel = st.text_input("Contato / Telefone / Tipo", value=row['telefone'] if row['telefone'] else "", key=f"tel_{row['id']}")
                        
                        col_bt1, col_bt2 = st.columns(2)
                        atualizar = col_bt1.form_submit_button("💾 Atualizar Dados")
                        excluir = col_bt2.form_submit_button("🗑️ Excluir Fornecedor")
                        
                        if atualizar:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE fornecedores SET nome = ?, telefone = ? WHERE id = ?", (novo_nome, novo_tel, row['id']))
                            conn.commit()
                            conn.close()
                            st.success("Fornecedor atualizado com sucesso!")
                            st.rerun()
                            
                        if excluir:
                            deletar_fornecedor(row['id'])
                            st.warning("Fornecedor excluído com sucesso!")
                            st.rerun()

    with tab3:
        conn = get_connection()
        prods = pd.read_sql_query("SELECT id, nome, grupo_equivalencia FROM produtos", conn)
        fornecs = pd.read_sql_query("SELECT id, nome FROM fornecedores", conn)
        conn.close()
        
        if prods.empty or fornecs.empty:
            st.warning("Cadastre produtos e fornecedores antes de inserir cotações.")
        else:
            with st.form("form_cotacao"):
                p_id = st.selectbox("Produto", prods['id'], format_func=lambda x: prods[prods['id'] == x]['nome'].values[0])
                f_id = st.selectbox("Atacadista / Fornecedor", fornecs['id'], format_func=lambda x: fornecs[fornecs['id'] == x]['nome'].values[0])
                preco = st.number_input("Preço Unitário Ofertado (R$)", min_value=0.01, step=0.10)
                btn_c = st.form_submit_button("Salvar Cotação")
                
                if btn_c:
                    data_hoje = datetime.now().strftime("%Y-%m-%d")
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, ?)",
                                   (p_id, f_id, preco, data_hoje))
                    conn.commit()
                    conn.close()
                    st.success("Cotação salva com sucesso!")
                    st.rerun()
                    
            st.markdown("---")
            st.subheader("Cotações Recentes")
            conn = get_connection()
            df_cot = pd.read_sql_query('''
                SELECT c.id, p.nome AS produto, f.nome AS atacadista, c.preco, c.data_cotacao
                FROM cotacoes c
                JOIN produtos p ON c.produto_id = p.id
                JOIN fornecedores f ON c.fornecedor_id = f.id
                ORDER BY c.data_cotacao DESC LIMIT 20
            ''', conn)
            conn.close()
            st.dataframe(df_cot, use_container_width=True)

# ==========================================
# ABA 7: COMPOSIÇÃO DE CESTAS & KITS
# ==========================================
elif menu == "📋 Composição de Cestas & Kits":
    st.header("📋 Gerenciamento de Cestas, Kits e Combos")
    
    tab_c1, tab_c2 = st.tabs(["➕ Criar Nova Cesta / Kit Sazonal", "🧩 Montar Itens do Kit"])
    
    with tab_c1:
        with st.form("form_novo_tipo"):
            nome_cesta = st.text_input("Nome do Kit (Ex: Cesta Natalina Feliz, Kit Higiene Família)")
            desc_cesta = st.text_area("Descrição / Quantidade de Itens")
            btn_criar = st.form_submit_button("Criar Modelo de Cesta/Kit")
            
            if btn_criar and nome_cesta:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO tipos_cesta (nome, descricao) VALUES (?, ?)", (nome_cesta, desc_cesta))
                    conn.commit()
                    conn.close()
                    st.success(f"Modelo '{nome_cesta}' criado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")
                    
        st.markdown("---")
        st.subheader("Modelos de Cestas e Kits Cadastrados")
        conn = get_connection()
        df_tipos = pd.read_sql_query("SELECT id, nome, descricao FROM tipos_cesta", conn)
        conn.close()
        st.dataframe(df_tipos, use_container_width=True)
        
    with tab_c2:
        conn = get_connection()
        tipos = pd.read_sql_query("SELECT id, nome FROM tipos_cesta", conn)
        produtos_list = pd.read_sql_query("SELECT id, nome, unidade FROM produtos", conn)
        conn.close()
        
        if tipos.empty or produtos_list.empty:
            st.warning("Cadastre os modelos de cesta e os produtos primeiro.")
        else:
            with st.form("form_comp"):
                t_id = st.selectbox("Cesta / Kit Alvo", tipos['id'], format_func=lambda x: tipos[tipos['id'] == x]['nome'].values[0])
                prod_id = st.selectbox("Produto a Incluir", produtos_list['id'], format_func=lambda x: produtos_list[produtos_list['id'] == x]['nome'].values[0])
                qtd = st.number_input("Quantidade na Cesta", min_value=0.1, value=1.0, step=0.1)
                
                if st.form_submit_button("Vincular Produto"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO composicao_cesta (tipo_cesta_id, produto_id, quantidade) VALUES (?, ?, ?)", (t_id, prod_id, qtd))
                    conn.commit()
                    conn.close()
                    st.success("Item vinculado!")
                    st.rerun()
                    
            st.markdown("---")
            st.subheader("Itens Atuais do Kit")
            cesta_vis = st.selectbox("Visualizar composição:", tipos['nome'])
            c_id_vis = int(tipos[tipos['nome'] == cesta_vis]['id'].values[0])
            
            conn = get_connection()
            df_comp = pd.read_sql_query('''
                SELECT cc.id, p.nome AS produto, p.unidade, cc.quantidade, p.grupo_equivalencia
                FROM composicao_cesta cc
                JOIN produtos p ON cc.produto_id = p.id
                WHERE cc.tipo_cesta_id = ?
            ''', conn, params=(c_id_vis,))
            conn.close()
            st.dataframe(df_comp, use_container_width=True)
