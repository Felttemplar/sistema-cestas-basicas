import streamlit as st
import pandas as pd
from datetime import datetime
from core.database import init_db, get_connection, deletar_fornecedor
from core.engine import calcular_custo_cesta, obter_parametros, salvar_parametro

init_db()

st.set_page_config(page_title="Gestão de Cestas Básicas & Kits", page_icon="🛒", layout="wide")

st.title("🛒 Sistema de Cotação e Precificação de Cestas Básicas")
st.markdown("Gerencie fornecedores, cotações, substitutos, calcule preços e controle as vendas por canal.")

st.sidebar.header("Navegação")
menu = st.sidebar.radio("Ir para:", [
    "📈 Dashboard & Projeções",
    "📊 Cotações & Preço de Venda", 
    "🛒 Registro de Vendas",
    "📦 Cadastrar Produtos e Substitutos", 
    "🏭 Fornecedores & Preços", 
    "📋 Composição de Cestas e Kits"
])

params = obter_parametros()

# ==========================================
# ABA 0: DASHBOARD & PROJEÇÕES
# ==========================================
if menu == "📈 Dashboard & Projeções":
    st.header("📈 Dashboard Analítico & Projeções Financeiras")
    st.markdown("Visão geral do desempenho comercial, participação por canal e simulador de metas.")
    
    conn = get_connection()
    df_vendas = pd.read_sql_query('''
        SELECT 
            v.id, 
            t.nome AS cesta, 
            v.quantidade_vendida, 
            v.preco_unitario_praticado, 
            (v.quantidade_vendida * v.preco_unitario_praticado) AS faturamento_total,
            v.canal_venda, 
            v.data_venda
        FROM vendas v
        JOIN tipos_cesta t ON v.tipo_cesta_id = t.id
    ''', conn)
    conn.close()
    
    if df_vendas.empty:
        st.info("⚠️ Ainda não há vendas registradas para gerar dados analíticos. Registre vendas na aba 'Registro de Vendas'.")
    else:
        # KPIs Superiores
        total_faturamento = df_vendas['faturamento_total'].sum()
        total_unidades = df_vendas['quantidade_vendida'].sum()
        ticket_medio = total_faturamento / df_vendas['id'].count() if df_vendas['id'].count() > 0 else 0.0
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💰 Faturamento Acumulado", f"R$ {total_faturamento:.2f}")
        kpi2.metric("📦 Cestas / Kits Vendidos", f"{total_unidades} un")
        kpi3.metric("🎯 Ticket Médio por Venda", f"R$ {ticket_medio:.2f}")
        
        st.markdown("---")
        
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("📊 Faturamento por Canal de Venda")
            df_canais = df_vendas.groupby('canal_venda')['faturamento_total'].sum().reset_index()
            st.bar_chart(df_canais.set_index('canal_venda'))
            
        with col_graf2:
            st.subheader("🏆 Cestas Mais Vendidas (Volume)")
            df_cestas = df_vendas.groupby('cesta')['quantidade_vendida'].sum().reset_index()
            st.bar_chart(df_cestas.set_index('cesta'))
            
        st.markdown("---")
        st.subheader("🔮 Simulador de Projeção de Crescimento")
        st.markdown("Simule o impacto de metas de vendas no seu faturamento mensal estimado.")
        
        c_sim1, c_sim2 = st.columns(2)
        with c_sim1:
            meta_diaria = st.slider("Meta diária de vendas (Cestas/dia)", 1, 100, 10)
            preco_medio_estimado = st.number_input("Preço médio por cesta (R$)", value=float(ticket_medio if ticket_medio > 0 else 85.00), step=5.00)
        
        with c_sim2:
            faturamento_diario_proj = meta_diaria * preco_medio_estimado
            faturamento_mensal_proj = faturamento_diario_proj * 26  # Considerando 26 dias úteis
            
            st.markdown(f"**Faturamento Diário Projetado:** R$ {faturamento_diario_proj:.2f}")
            st.markdown(f"**Faturamento Mensal Estimado (26 dias):** R$ {faturamento_mensal_proj:.2f}")
            
            margem_estimada = float(params.get("margem_lucro_padrao", 25.0))
            lucro_mensal_proj = faturamento_mensal_proj * (margem_estimada / 100.0)
            st.metric("💡 Lucro Mensal Estimado", f"R$ {lucro_mensal_proj:.2f}", delta=f"{margem_estimada}% margem")

# ==========================================
# ABA 1: COTAÇÕES & PREÇO DE VENDA
# ==========================================
elif menu == "📊 Cotações & Preço de Venda":
    st.header("📊 Análise de Custo e Sugestão de Preço para Revenda")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        margem = st.slider("Margem de Lucro Desejada (%)", 5.0, 60.0, float(params.get("margem_lucro_padrao", 25.0)), 1.0)
    with col2:
        embalagem = st.number_input("Custo de Embalagem (R$)", value=float(params.get("custo_embalagem", 3.50)), step=0.50)
    with col3:
        frete = st.number_input("Custo de Frete Rateado (R$)", value=float(params.get("frete_medio", 5.00)), step=0.50)
        
    conn = get_connection()
    tipos_cesta = pd.read_sql_query("SELECT id, nome FROM tipos_cesta", conn)
    conn.close()
    
    if tipos_cesta.empty:
        st.warning("Cadastre tipos de cesta primeiro na aba 'Composição de Cestas e Kits'.")
    else:
        cesta_escolhida = st.selectbox("Selecione a Cesta ou Kit para Orçar", tipos_cesta['nome'])
        cesta_id = int(tipos_cesta[tipos_cesta['nome'] == cesta_escolhida]['id'].values[0])
        
        df_itens, custo_insumos, custo_total, valor_lucro, preco_venda = calcular_custo_cesta(cesta_id, margem, embalagem, frete)
        
        if df_itens.empty:
            st.info("⚠️ Nenhuma cotação cadastrada para os itens desta cesta ainda. Vá na aba 'Fornecedores & Preços' para preencher.")
        else:
            st.subheader(f"Resultado para: {cesta_escolhida}")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Custo dos Insumos", f"R$ {custo_insumos:.2f}")
            m2.metric("Custo Total (c/ Embalagem & Frete)", f"R$ {custo_total:.2f}")
            m3.metric("Lucro Previsto", f"R$ {valor_lucro:.2f}")
            m4.metric("🏷️ Preço Sugerido de Venda", f"R$ {preco_venda:.2f}")
            
            st.markdown("---")
            st.markdown("### Detalhes dos Menores Preços Encontrados (Menor Custo por Grupo)")
            
            tabela_exibicao = df_itens[['produto', 'grupo_equivalencia', 'quantidade', 'unidade', 'menor_preco', 'fornecedor', 'subtotal']].copy()
            tabela_exibicao.columns = ['Produto Escolhido', 'Grupo / Categoria', 'Qtd', 'Un', 'Menor Preço Un.', 'Fornecedor Vencedor', 'Subtotal']
            st.dataframe(tabela_exibicao.style.format({
                'Menor Preço Un.': 'R$ {:.2f}',
                'Subtotal': 'R$ {:.2f}',
                'Qtd': '{:.1f}'
            }), use_container_width=True)

# ==========================================
# ABA 2: REGISTRO DE VENDAS
# ==========================================
elif menu == "🛒 Registro de Vendas":
    st.header("🛒 Controlo e Registo de Vendas")
    st.markdown("Registe as suas vendas efetuadas por canais online ou presenciais para controlo de quantidades e faturamento.")
    
    conn = get_connection()
    tipos_cesta = pd.read_sql_query("SELECT id, nome FROM tipos_cesta", conn)
    conn.close()
    
    if tipos_cesta.empty:
        st.warning("Cadastre tipos de cesta primeiro.")
    else:
        with st.form("form_venda"):
            cesta_venda = st.selectbox("Cesta / Kit Vendido", tipos_cesta['nome'])
            cesta_id_venda = int(tipos_cesta[tipos_cesta['nome'] == cesta_venda]['id'].values[0])
            
            qtd_vendida = st.number_input("Quantidade Vendida", min_value=1, value=1, step=1)
            preco_praticado = st.number_input("Preço Unitário Praticado na Venda (R$)", min_value=0.01, value=50.00, step=1.00)
            
            canal = st.selectbox("Canal de Venda", [
                "Online - Instagram", 
                "Online - Pigz", 
                "Online - iFood", 
                "Online - Facebook Marketplace", 
                "Offline - Negociação Física (In Loco)"
            ])
            
            btn_registrar_venda = st.form_submit_button("Registar Venda")
            
            if btn_registrar_venda:
                data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO vendas (tipo_cesta_id, quantidade_vendida, preco_unitario_praticado, canal_venda, data_venda)
                    VALUES (?, ?, ?, ?, ?)
                ''', (cesta_id_venda, qtd_vendida, preco_praticado, canal, data_atual))
                conn.commit()
                conn.close()
                st.success(f"Venda de {qtd_vendida}x '{cesta_venda}' registada com sucesso via {canal}!")
                st.rerun()
                
        st.markdown("---")
        st.subheader("📊 Histórico e Resumo de Vendas")
        
        conn = get_connection()
        df_vendas = pd.read_sql_query('''
            SELECT 
                v.id, 
                t.nome AS cesta, 
                v.quantidade_vendida, 
                v.preco_unitario_praticado, 
                (v.quantidade_vendida * v.preco_unitario_praticado) AS faturamento_total,
                v.canal_venda, 
                v.data_venda
            FROM vendas v
            JOIN tipos_cesta t ON v.tipo_cesta_id = t.id
            ORDER BY v.data_venda DESC
        ''', conn)
        conn.close()
        
        if df_vendas.empty:
            st.info("Nenhuma venda registada até o momento.")
        else:
            total_faturamento = df_vendas['faturamento_total'].sum()
            total_qtd = df_vendas['quantidade_vendida'].sum()
            
            kpi1, kpi2 = st.columns(2)
            kpi1.metric("📦 Total de Cestas/Kits Vendidos", f"{total_qtd} unidades")
            kpi2.metric("💰 Faturamento Total Acumulado", f"R$ {total_faturamento:.2f}")
            
            st.markdown("### Detalhamento das Transações")
            st.dataframe(df_vendas.style.format({
                'preco_unitario_praticado': 'R$ {:.2f}',
                'faturamento_total': 'R$ {:.2f}'
            }), use_container_width=True)

# ==========================================
# ABA 3: CADASTRAR PRODUTOS E SUBSTITUTOS
# ==========================================
elif menu == "📦 Cadastrar Produtos e Substitutos":
    st.header("📦 Cadastro de Produtos e Grupos de Substituição")
    st.markdown("Cadastre os produtos informando a qual **Grupo de Equivalência** pertencem.")
    
    with st.form("form_produto"):
        nome_prod = st.text_input("Nome do Produto (Ex: Arroz Camil 5kg)")
        unidade = st.selectbox("Unidade de Medida", ["UN", "PCT", "KG", "L", "CX"])
        grupo_eq = st.text_input("Grupo de Equivalência (Ex: Arroz 5kg, Óleo 900ml, Sabonete)")
        
        submitted = st.form_submit_button("Cadastrar Produto")
        if submitted:
            if nome_prod and grupo_eq:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO produtos (nome, unidade, grupo_equivalencia) VALUES (?, ?, ?)", 
                               (nome_prod, unidade, grupo_eq))
                conn.commit()
                conn.close()
                st.success(f"Produto '{nome_prod}' cadastrado com sucesso!")
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios.")
                
    st.markdown("---")
    st.subheader("Produtos Cadastrados")
    conn = get_connection()
    df_prods = pd.read_sql_query("SELECT * FROM produtos", conn)
    conn.close()
    st.dataframe(df_prods, use_container_width=True)

# ==========================================
# ABA 4: FORNECEDORES & PREÇOS
# ==========================================
elif menu == "🏭 Fornecedores & Preços":
    st.header("🏭 Gestão de Fornecedores e Cotações Semanais")
    
    tab1, tab2 = st.tabs(["Cadastrar e Gerenciar Fornecedores", "Registrar Cotação de Preço"])
    
    with tab1:
        with st.form("form_fornecedor"):
            f_nome = st.text_input("Nome do Fornecedor / Atacadista")
            f_tel = st.text_input("Telefone / Contato")
            btn_f = st.form_submit_button("Salvar Fornecedor")
            if btn_f and f_nome:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO fornecedores (nome, telefone) VALUES (?, ?)", (f_nome, f_tel))
                    conn.commit()
                    conn.close()
                    st.success(f"Fornecedor '{f_nome}' cadastrado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")
                    
        st.markdown("---")
        st.subheader("Fornecedores Cadastrados")
        
        conn = get_connection()
        df_fornecs = pd.read_sql_query("SELECT id, nome, telefone FROM fornecedores", conn)
        conn.close()
        
        if df_fornecs.empty:
            st.info("Nenhum fornecedor cadastrado até o momento.")
        else:
            for index, row in df_fornecs.iterrows():
                col_info1, col_info2, col_btn = st.columns([3, 3, 2])
                col_info1.write(f"**{row['nome']}**")
                col_info2.write(f"Tel: {row['telefone'] if row['telefone'] else 'Não informado'}")
                if col_btn.button("🗑️ Excluir", key=f"del_fornec_{row['id']}"):
                    deletar_fornecedor(row['id'])
                    st.warning(f"Fornecedor '{row['nome']}' excluído com sucesso!")
                    st.rerun()
                    
    with tab2:
        conn = get_connection()
        prods = pd.read_sql_query("SELECT id, nome, grupo_equivalencia FROM produtos", conn)
        fornecs = pd.read_sql_query("SELECT id, nome FROM fornecedores", conn)
        conn.close()
        
        if prods.empty or fornecs.empty:
            st.warning("Cadastre ao menos um produto e um fornecedor antes de registrar cotações.")
        else:
            with st.form("form_cotacao"):
                p_id = st.selectbox("Produto", prods['id'], format_func=lambda x: prods[prods['id'] == x]['nome'].values[0])
                f_id = st.selectbox("Fornecedor", fornecs['id'], format_func=lambda x: fornecs[fornecs['id'] == x]['nome'].values[0])
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
                    st.success("Cotação registrada com sucesso!")
                    st.rerun()
                    
            st.markdown("---")
            st.subheader("Histórico de Cotações Recentes")
            conn = get_connection()
            df_cot = pd.read_sql_query('''
                SELECT c.id, p.nome AS produto, f.nome AS fornecedor, c.preco, c.data_cotacao
                FROM cotacoes c
                JOIN produtos p ON c.produto_id = p.id
                JOIN fornecedores f ON c.fornecedor_id = f.id
                ORDER BY c.data_cotacao DESC LIMIT 20
            ''', conn)
            conn.close()
            st.dataframe(df_cot, use_container_width=True)

# ==========================================
# ABA 5: COMPOSIÇÃO DE CESTAS E KITS
# ==========================================
elif menu == "📋 Composição de Cestas e Kits":
    st.header("📋 Montagem e Gerenciamento de Cestas e Kits")
    
    tab_cesta1, tab_cesta2 = st.tabs(["➕ Criar Novo Tipo de Cesta/Kit Sazonal", "🧩 Montar Itens da Cesta"])
    
    with tab_cesta1:
        st.subheader("Criar Nova Cesta ou Kit (Ex: Cesta de Natal, Kit Dia das Mães)")
        with st.form("form_novo_tipo_cesta"):
            nome_cesta = st.text_input("Nome da Nova Cesta/Kit (Ex: Cesta de Natal Premium, Kit Páscoa)")
            desc_cesta = st.text_area("Descrição / Finalidade (Opcional)")
            btn_criar_cesta = st.form_submit_button("Criar Tipo de Cesta")
            
            if btn_criar_cesta:
                if nome_cesta:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO tipos_cesta (nome, descricao) VALUES (?, ?)", (nome_cesta, desc_cesta))
                        conn.commit()
                        conn.close()
                        st.success(f"Tipo de Cesta '{nome_cesta}' criado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao cadastrar: {e}")
                else:
                    st.error("Informe o nome da cesta.")
                    
        st.markdown("---")
        st.subheader("Cestas e Kits Cadastrados")
        conn = get_connection()
        df_tipos_existentes = pd.read_sql_query("SELECT id, nome, descricao FROM tipos_cesta", conn)
        conn.close()
        st.dataframe(df_tipos_existentes, use_container_width=True)
        
    with tab_cesta2:
        st.subheader("Vincular Produtos a uma Cesta / Kit")
        conn = get_connection()
        tipos = pd.read_sql_query("SELECT id, nome FROM tipos_cesta", conn)
        produtos_list = pd.read_sql_query("SELECT id, nome, unidade FROM produtos", conn)
        conn.close()
        
        if tipos.empty or produtos_list.empty:
            st.warning("Cadastre tipos de cesta e produtos primeiro.")
        else:
            with st.form("form_composicao"):
                t_id = st.selectbox("Escolha a Cesta / Kit", tipos['id'], format_func=lambda x: tipos[tipos['id'] == x]['nome'].values[0])
                prod_id = st.selectbox("Produto a Adicionar", produtos_list['id'], format_func=lambda x: produtos_list[produtos_list['id'] == x]['nome'].values[0])
                qtd = st.number_input("Quantidade na Cesta", min_value=0.1, value=1.0, step=0.1)
                
                btn_comp = st.form_submit_button("Vincular Produto à Cesta")
                if btn_comp:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO composicao_cesta (tipo_cesta_id, produto_id, quantidade)
                        VALUES (?, ?, ?)
                    ''', (t_id, prod_id, qtd))
                    conn.commit()
                    conn.close()
                    st.success("Item adicionado à composição com sucesso!")
                    st.rerun()
                    
            st.markdown("---")
            st.subheader("Itens Atuais na Composição")
            cesta_selecionada_visual = st.selectbox("Visualizar cesta:", tipos['nome'], key="vis_cesta")
            c_id_vis = int(tipos[tipos['nome'] == cesta_selecionada_visual]['id'].values[0])
            
            conn = get_connection()
            df_comp = pd.read_sql_query('''
                SELECT cc.id, p.nome AS produto, p.unidade, cc.quantidade, p.grupo_equivalencia
                FROM composicao_cesta cc
                JOIN produtos p ON cc.produto_id = p.id
                WHERE cc.tipo_cesta_id = ?
            ''', conn, params=(c_id_vis,))
            conn.close()
            
            st.dataframe(df_comp, use_container_width=True)
