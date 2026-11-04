import streamlit as st
import pandas as pd
from datetime import datetime
from core.database import init_db, get_connection, deletar_fornecedor
from core.engine import calcular_custo_cesta, obter_parametros, salvar_parametro

init_db()

st.set_page_config(page_title="Gestão Cesta da Família - Monte Roraima", page_icon="🛒", layout="wide")

st.title("🛒 Sistema de Cotação, Precificação e Vendas - Boa Vista/RR")
st.markdown("Gestão de fornecedores, frete por zonas, comissões, cotações e vendas por canal e vendedor.")

st.sidebar.header("Navegação")
menu = st.sidebar.radio("Ir para:", [
    "📈 Dashboard & Projeções",
    "📊 Cotações & Precificação", 
    "🛒 Registro de Vendas",
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
            v.data_venda
        FROM vendas v
        JOIN tipos_cesta t ON v.tipo_cesta_id = t.id
    ''', conn)
    conn.close()
    
    if df_vendas.empty:
        st.info("⚠️ Nenhuma venda registrada até o momento. Registre vendas na aba 'Registro de Vendas'.")
    else:
        total_faturamento = df_vendas['faturamento_total'].sum()
        total_unidades = df_vendas['quantidade_vendida'].sum()
        ticket_medio = total_faturamento / df_vendas['id'].count() if df_vendas['id'].count() > 0 else 0.0
        
        k1, k2, k3 = st.columns(3)
        k1.metric("💰 Faturamento Acumulado", f"R$ {total_faturamento:.2f}")
        k2.metric("📦 Cestas/Kits Vendidos", f"{total_unidades} un")
        k3.metric("🎯 Ticket Médio por Venda", f"R$ {ticket_medio:.2f}")
        
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
            st.subheader("📱 Vendas por Canal")
            df_canais = df_vendas.groupby('canal_venda')['faturamento_total'].sum().reset_index()
            st.bar_chart(df_canais.set_index('canal_venda'))
            
        with c_graf4:
            st.subheader("🏆 Kits Mais Vendidos")
            df_kits = df_vendas.groupby('cesta')['quantidade_vendida'].sum().reset_index()
            st.bar_chart(df_kits.set_index('cesta'))

# ==========================================
# ABA 1: COTAÇÕES & PRECIFICAÇÃO
# ==========================================
elif menu == "📊 Cotações & Precificação":
    st.header("📊 Análise de Custo, Impostos e Sugestão de Preço")
    
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
            st.info("⚠️ Nenhuma cotação cadastrada para os itens desta cesta ainda. Vá na aba 'Fornecedores & Preços' para preencher.")
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

# ==========================================
# ABA 2: REGISTRO DE VENDAS
# ==========================================
elif menu == "🛒 Registro de Vendas":
    st.header("🛒 Registro e Controle de Vendas")
    st.markdown("Registre as vendas especificando a **Zona de Boa Vista**, o **Vendedor** e o **Canal de Venda**.")
    
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
                canal = st.selectbox("Canal de Venda", [
                    "Online - Instagram",
                    "Online - Pigz",
                    "Online - iFood",
                    "Online - Zé Delivery",
                    "Online - Facebook Marketplace",
                    "Presencial - Venda Física (In Loco / PAP)"
                ])
                
            comissao_perc = st.number_input("Comissão do Vendedor (%)", min_value=0.0, max_value=20.0, value=2.5, step=0.5)
            btn_registrar_venda = st.form_submit_button("Registar Venda")
            
            if btn_registrar_venda:
                data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO vendas (tipo_cesta_id, quantidade_vendida, preco_unitario_praticado, canal_venda, vendedor, zona_entrega, comissao_percentual, data_venda)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (cesta_id_venda, qtd_vendida, preco_praticado, canal, vendedor, zona, comissao_perc, data_atual))
                conn.commit()
                conn.close()
                st.success(f"Venda de {qtd_vendida}x '{cesta_venda}' salva com sucesso!")
                st.rerun()
                
        st.markdown("---")
        st.subheader("📊 Histórico de Vendas Realizadas")
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
            st.info("Nenhuma venda registrada até o momento.")
        else:
            st.dataframe(df_vendas.style.format({
                'preco_unitario_praticado': 'R$ {:.2f}',
                'faturamento_total': 'R$ {:.2f}'
            }), use_container_width=True)

# ==========================================
# ABA 3: CADASTRAR PRODUTOS E SUBSTITUTOS
# ==========================================
elif menu == "📦 Cadastrar Produtos & Substitutos":
    st.header("📦 Cadastro de Produtos e Grupos de Substituição")
    
    with st.form("form_produto"):
        nome_prod = st.text_input("Nome do Produto (Ex: Arroz Camil 5kg, Sabonete Lux 85g)")
        unidade = st.selectbox("Unidade de Medida", ["UN", "PCT", "KG", "L", "CX"])
        grupo_eq = st.text_input("Grupo de Equivalência (Ex: Arroz 5kg, Feijão 1kg, Sabonete)")
        
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
    st.header("🏭 Atacadistas, Distribuidoras e Cotações")
    
    tab1, tab2 = st.tabs(["Cadastrar e Gerenciar Atacadistas", "Registrar Cotação de Preço"])
    
    with tab1:
        with st.form("form_fornecedor"):
            f_nome = st.text_input("Nome do Atacadista / Distribuidora (Ex: Atacadão, Assaí, Nova Era)")
            f_tel = st.text_input("Contato / Telefone")
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
                    
        st.markdown("---")
        st.subheader("Atacadistas Cadastrados")
        conn = get_connection()
        df_fornecs = pd.read_sql_query("SELECT id, nome, telefone FROM fornecedores", conn)
        conn.close()
        
        if not df_fornecs.empty:
            for index, row in df_fornecs.iterrows():
                c1, c2, c3 = st.columns([3, 3, 2])
                c1.write(f"**{row['nome']}**")
                c2.write(f"Tel/Tipo: {row['telefone'] if row['telefone'] else 'Atacado'}")
                if c3.button("🗑️ Excluir", key=f"del_fornec_{row['id']}"):
                    deletar_fornecedor(row['id'])
                    st.warning(f"Excluído com sucesso!")
                    st.rerun()

    with tab2:
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
# ABA 5: COMPOSIÇÃO DE CESTAS & KITS
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
