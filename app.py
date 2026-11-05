import streamlit as st
import pandas as pd
from datetime import datetime
from contextlib import closing
from core.database import init_db, get_connection
from core.importacao import importar_cotacoes, normalizar_unidade, normalizar_nome_produto
from core.operations import (criar_fornecedor, registrar_cotacao, salvar_lote_compra, salvar_receita, obter_planejamento_montagem, montar_cestas, obter_resumo_cestas, registrar_venda)
import io

init_db()
st.set_page_config(page_title="Cestas Bom Dia | Gestão", page_icon="🛒", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    :root { color-scheme: light; }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: #f5f7f8 !important; }
    [data-testid="stMain"] { color: #1f2937 !important; }
    [data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3,
    [data-testid="stMain"] p, [data-testid="stMain"] label,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"],
    [data-testid="stMain"] [data-testid="stWidgetLabel"],
    [data-testid="stMain"] [data-testid="stCaptionContainer"] { color: #1f2937 !important; }
    [data-testid="stSidebar"] { background: #102c27 !important; }
    [data-testid="stSidebar"] * { color: #eef7f2; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label { padding: .45rem .55rem; border-radius: .45rem; }
    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background: #1b433a; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1450px; }
    [data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3 { color: #173c33 !important; letter-spacing: -.02em; }
    [data-testid="stMain"] [data-testid="stMetric"] { background: #fff; border: 1px solid #e5ebe8; padding: 1rem 1.1rem; border-radius: .8rem; box-shadow: 0 2px 10px rgba(20,50,40,.04); }
    [data-testid="stMain"] [data-testid="stMetricLabel"] { color: #52645d !important; }
    [data-testid="stMain"] [data-testid="stMetricValue"] { color: #173c33 !important; }
    [data-testid="stMain"] input, [data-testid="stMain"] textarea,
    [data-testid="stMain"] [data-baseweb="select"] > div,
    [data-testid="stMain"] [data-baseweb="input"] > div { background-color: #fff !important; color: #17211e !important; border-color: #aebdb6 !important; }
    [data-testid="stMain"] input::placeholder, [data-testid="stMain"] textarea::placeholder { color: #66756f !important; opacity: 1; }
    [data-testid="stMain"] [role="listbox"], [data-testid="stMain"] [role="option"],
    [data-testid="stMain"] [data-baseweb="popover"] { background: #fff !important; color: #17211e !important; }
    [data-testid="stMain"] [data-testid="stForm"], [data-testid="stMain"] [data-testid="stExpander"] { background: #fff; border-color: #d5e0da; border-radius: .75rem; }
    [data-testid="stMain"] button { color: #173c33 !important; border-color: #aebdb6 !important; background: #fff !important; }
    [data-testid="stMain"] button[kind="primary"] { color: #fff !important; background: #12664f !important; border-color: #12664f !important; }
    [data-testid="stMain"] button:focus-visible, [data-testid="stMain"] input:focus,
    [data-testid="stMain"] textarea:focus { outline: 3px solid #55a98b !important; outline-offset: 1px; }
    [data-testid="stMain"] [data-testid="stDataFrame"] { background: #fff; border: 1px solid #d5e0da; border-radius: .65rem; overflow: hidden; }
    [data-testid="stMain"] [data-testid="stAlert"] { color: #17211e; }
</style>
""", unsafe_allow_html=True)

# Base inicial de cotação, com marca separada por loja para evitar comparar marcas diferentes como se fossem iguais.
_colunas_cotacao = ["Nº", "Nome do Produto", "Unidade", "Marca Assaí", "Preço Assaí", "Marca Atacadão", "Preço Atacadão"]
_linhas_cotacao = """
1|ARROZ 1KG|KG|PRATO CHIC|3.39|PANELAÇO|4.49
2|FEIJÃO 1KG|KG|KICALDO|5.62|BULNEZ|5.69
3|AÇUCAR 1KG|KG|CRISTAL SONORA|2.79|CRISTAL SONORA|3.35
4|FARINHA||||MANDIOCA DONA|4.29
5|TRIGO 1KG|KG|TRIGOLAR|4.70|FINNA|4.69
6|OLEO 900ML|FR|SERRA VERDE|7.49|SERRA VERDE|6.95
7|SAL 1KG|KG|FELICIA|2.25|RN|1.79
8|MACARRÃO ESPAG. 400G|PC|BOM SABOR|1.89|BOM SABOR|2.09
9|MOLHO TOMATE SC300G|SC/G|BONARE|1.59|BOM SABOR|1.59
10|VINAGRE 500ML|FR|VIRROSAS|3.19|VIRROSA|2.59
11|CAFE 250GR|PC|PILÃO|8.09|MANAUS|9.99
12|SARDINHA 125G|LT|PALMEIRA|4.89|SUPLESCA|5.59
13|BOLACHA DOCE RECHEADA 80G|PC|TRIGOLINO|1.69|TRIGOLIN|1.39
14|BISCOITO SALGADO CREMCKER 300G|PC|RACHEIRO|2.99|ESTRELA|3.99
15|LEITE EM PÓ|||||
16|COMPOSTO LACTEO 400G|PC|PURIBON|8.39|PIRACANJUBA|11.89
18|GOIABADA|||||
19|MIOJO 74G DVS SABOR|UND|NOSSO SABOR LAMEN|1.23|NOSSA SABOR LAMEN|1.49
20|CESTA BÁSICA 1|||89.00||
21|CESTA BÁSICA 2|||159.00||
22|FLOCÃO 500GR|G|LIVRE FLOCOS|3.89||
23|SELETA LEGUMES 170G|LT|PREDILECTA|2.79|BONARE SC|3.29
24|ACHOCOLATADO 200GR|PC|APITI POWER|4.30|MARATÁ|4.65
25|BISCOITO ROSQUINHA DOCE 300G|PC|TRIGOLINO|4.29|ESTRELA COCO|3.69
26|MARGARINA 250G|UND|PRIMOR|2.95|PRIMOR|3.29
27|MARGARINA 500G|UND|PRIMOR|4.99|PRIMOR|6.00
28|PÃO FORMA 450G|UND|PÃES DELÍCIA|6.99|PAES DELICIA|8.00
29|REFRESCO PÓ 8G|UND|||SUKKI|0.39
30|BANDEJA DE OVOS 30UND|UND|||GSL|11.59
31|PASTA DE DENTES 70GR|UND|EVEN TRI PROT|2.09|CLOSEUP|2.49
32|SABONETE 80GR|UND|FRANCIS INTENSO|1.59|EVEN|1.99
33|PAPEL HIGIÊNICO INDIV.|||||
34|PAPEL HIGIÊNICO 4UND.|UND|FLORAL|3.99|GIRASOL 30MT|2.90
35|SHAMPOO|||||
36|CONDICIONADOR|||||
37|KIT SHAMPOO/CONDIC.|UND|DABELLE|17.49|ABOVE|15.91
38|ESCOVA DE DENTES|UND|SORRISO|3.99|CONDOR|2.79
39|PENTE|||||
40|FIO DENTAL|UND|JADE PRO|8.95|DENTRAT MENTA|4.99
41|DESODORANTE NEUTRO|UND|ABOVE CREME|3.39||
42|PAPEL HIGIENICO COM 8UND|UND|GIRASSOL 30M NEUTRO|6.29|GIRASOL 30MT|6.29
43|ÁGUA SANITÁRIA 1 LT|UND|BRINORT|2.65|BRINORT|2.29
44|DESINFETANTE 2LT|UND|BRINORT EUCALIPTO|5.45|BRINORT|5.29
45|SABÃO EM BARRA 450G / 180G|UND|GUAMÁ|4.49|MULTIUSO|2.35
46|SABÃO EM PÓ 400GR|UND|LAV ROUPA PÓ SONHO|3.39|DET. PO ABSOLUTO|1.80
47|AMACIANTE 2LT|UND|AMAC HIPER PLUS|5.79|BRINORT|5.39
48|MULTIÚSO 500ML|UND|BRILUX MULTIUSO|3.99|BRILUX MULTIUSO|4.15
49|ESPONJA|UND|ESFRELUX C/4|0.75|JEITOSA UND|0.55
50|PALHA DE AÇO||||LUSTRO|1.55
51|DETERGENTE 500ML|UND|BRILUX|1.85|FC|2.05
52|DESINFETANTE 500ML|UND|BRILUX EUCALIPTO|1.99|ECONOMICO|2.79
"""
dados_completos = []
for _linha in _linhas_cotacao.strip().splitlines():
    _valores = _linha.split("|")
    _registro = dict(zip(_colunas_cotacao, _valores))
    for _campo in ("Preço Assaí", "Preço Atacadão"):
        _registro[_campo] = float(_registro[_campo]) if _registro[_campo] else None
    dados_completos.append(_registro)


def _ir_para(pagina):
    st.session_state["main_navigation"] = pagina


with st.sidebar:
    st.markdown("## 🛒 Cestas Bom Dia")
    st.caption("OPERAÇÃO • BOA VISTA, RR")
    st.markdown("---")
    st.caption("SEU FLUXO DE TRABALHO")
    menu = st.radio("Navegação", [
        "Visão geral",
        "Cotações e fornecedores",
        "Importar planilha",
        "Compras e lotes",
        "Estoque",
        "Cestas e vendas",
        "Produtos",
        "Histórico de preços",
    ], label_visibility="collapsed", key="main_navigation")
    st.markdown("---")
    st.caption("Cote → compare → compre → monte → venda")

if menu == "Visão geral":
    st.title("Painel da operação")
    st.caption("Acompanhe o caminho da cotação até as cestas disponíveis para venda.")
    conn = get_connection()
    resumo = pd.read_sql_query("""
        SELECT
          (SELECT COUNT(*) FROM produtos) AS produtos,
          (SELECT COUNT(*) FROM fornecedores) AS fornecedores,
          (SELECT COUNT(*) FROM cotacoes) AS cotacoes,
          (SELECT COUNT(*) FROM lotes) AS lotes,
          (SELECT COALESCE(SUM(CASE WHEN tipo IN ('ENTRADA','AJUSTE_ENTRADA') THEN quantidade ELSE -quantidade END),0) FROM movimentacoes_estoque) AS unidades_estoque,
          (SELECT COALESCE(SUM(m.quantidade),0) FROM montagens_cesta m) AS cestas_montadas,
          (SELECT COALESCE(SUM(v.quantidade_vendida),0) FROM vendas v) AS cestas_vendidas
    """, conn).iloc[0]
    df_alertas = pd.read_sql_query("""
        SELECT p.nome AS produto, p.unidade,
               COALESCE(SUM(CASE WHEN m.tipo IN ('ENTRADA','AJUSTE_ENTRADA') THEN m.quantidade ELSE -m.quantidade END),0) AS saldo
        FROM produtos p LEFT JOIN movimentacoes_estoque m ON m.produto_id=p.id
        GROUP BY p.id ORDER BY saldo, p.nome LIMIT 8
    """, conn)
    df_ultimas = pd.read_sql_query("""
        SELECT f.nome AS fornecedor, COUNT(*) AS cotacoes, MAX(c.data_cotacao) AS atualizada
        FROM cotacoes c JOIN fornecedores f ON f.id=c.fornecedor_id
        GROUP BY f.id ORDER BY atualizada DESC, f.nome LIMIT 5
    """, conn)
    conn.close()
    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Produtos cadastrados", f"{int(resumo['produtos']):,}".replace(',', '.'))
    k2.metric("Fornecedores", int(resumo['fornecedores']))
    k3.metric("Cotações registradas", f"{int(resumo['cotacoes']):,}".replace(',', '.'))
    k4.metric("Lotes de compra", int(resumo['lotes']))
    a1,a2,a3,a4 = st.columns(4)
    with a1:
        st.button("＋ Registrar cotação", on_click=_ir_para, args=("Cotações e fornecedores",), width="stretch")
    with a2:
        st.button("▦ Planejar compra", on_click=_ir_para, args=("Compras e lotes",), width="stretch")
    with a3:
        st.button("▤ Conferir estoque", on_click=_ir_para, args=("Estoque",), width="stretch")
    with a4:
        st.button("▣ Montar e vender", on_click=_ir_para, args=("Cestas e vendas",), type="primary", width="stretch")
    st.markdown("### Produção e disponibilidade")
    k5,k6,k7 = st.columns(3)
    k5.metric("Unidades em estoque", f"{float(resumo['unidades_estoque']):,.0f}".replace(',', '.'))
    k6.metric("Cestas montadas", int(resumo['cestas_montadas']))
    k7.metric("Cestas vendidas", int(resumo['cestas_vendidas']))
    esquerda,direita = st.columns([1.1,.9])
    with esquerda:
        st.markdown("### Comece por aqui")
        st.markdown("""
        - **1 · Cotar:** registre preços e marcas por loja ou importe a planilha.
        - **2 · Planejar a compra:** compare as últimas ofertas e informe quanto comprar.
        - **3 · Registrar o lote:** a compra entra no estoque com fornecedor, preço e quantidade.
        - **4 · Montar cestas:** defina a composição e veja quantas unidades o estoque permite.
        - **5 · Acompanhar vendas:** registre vendas e consulte o saldo pronto para revenda.
        """)
    with direita:
        st.markdown("### Estoque mais baixo")
        st.dataframe(df_alertas.rename(columns={"produto":"Produto","unidade":"Unidade","saldo":"Saldo"}), hide_index=True, width="stretch")
        st.markdown("### Atividade de cotação")
        st.dataframe(df_ultimas.rename(columns={"fornecedor":"Fornecedor","cotacoes":"Cotações","atualizada":"Última atualização"}), hide_index=True, width="stretch")

elif menu == "Importar planilha":
    st.title("Importar cotações")
    st.caption("Traga os preços coletados para a mesma base de produtos e fornecedores.")

    # Gerador dinâmico de planilha em memória
    output = io.BytesIO()
    df_m = pd.DataFrame(dados_completos, columns=_colunas_cotacao)
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
            st.success(f"Planilha carregada: {len(df_up)} linhas para conferência.")
            st.dataframe(df_up.head(30), width="stretch")
            st.caption("A importação preserva cotações antigas. Se houver uma cotação do mesmo produto e loja na mesma data, ela será atualizada.")
            if st.button("🚀 Validar e salvar cotações", type="primary"):
                resultado = importar_cotacoes(df_up)
                st.success(
                    f"Importação concluída: {resultado['produtos']} produtos conferidos e "
                    f"{resultado['cotacoes']} cotações salvas em {resultado['data']}."
                )
        except Exception as e:
            st.error(f"A planilha não foi importada: {e}")
elif menu == "Produtos":
    st.title("Cadastro de produtos")
    st.caption("Cadastre uma única vez cada item, com unidade e categoria padronizadas.")
    with st.form("form_prod"):
        n = st.text_input("Nome do Produto (Ex: Arroz 1kg, Feijão 1kg)")
        m = st.text_input("Marca principal (opcional; as marcas cotadas são registradas por loja)")
        u = st.selectbox("Unidade", ["KG", "PCT", "UN", "FR", "LT", "CX", "SC"])
        g = st.text_input("Grupo / Categoria (Ex: Alimento, Higiene, Limpeza)")
        if st.form_submit_button("Salvar Produto"):
            nome = n.strip().upper()
            marca_principal = m.strip().upper() or "VARIÁVEL"
            unidade_produto = normalizar_unidade(u)
            grupo = g.strip().upper() or nome
            if not nome:
                st.error("Informe o nome do produto.")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                existente = next((
                    item for item in cursor.execute("SELECT id, nome, unidade FROM produtos").fetchall()
                    if normalizar_nome_produto(item["nome"]) == normalizar_nome_produto(nome)
                    and normalizar_unidade(item["unidade"]) == unidade_produto
                ), None)
                if existente:
                    st.warning("Já existe um produto com este nome e unidade. Atualize esse cadastro em vez de criar outro.")
                    conn.close()
                else:
                    cursor.execute(
                        "INSERT INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)",
                        (nome, marca_principal, unidade_produto, grupo),
                    )
                    conn.commit()
                    conn.close()
                    st.success("Produto cadastrado com sucesso.")
                    st.rerun()
elif menu == "Cotações e fornecedores":
    st.title("Cotações e fornecedores")
    st.caption("Cadastre fornecedores de Boa Vista e compare a última cotação registrada por produto e loja.")

    with st.expander("Cadastrar mercado ou distribuidora", expanded=False):
        with st.form("form_fornecedor"):
            nome_fornecedor = st.text_input("Nome do fornecedor")
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                tipo_fornecedor = st.selectbox("Tipo", ["Mercado", "Atacarejo", "Distribuidora", "Outro"])
            with col_f2:
                cidade_fornecedor = st.text_input("Cidade", value="Boa Vista")
            with col_f3:
                bairro_fornecedor = st.text_input("Bairro")
            telefone_fornecedor = st.text_input("Telefone (opcional)")
            salvar_fornecedor = st.form_submit_button("Cadastrar fornecedor")
        if salvar_fornecedor:
            try:
                criar_fornecedor(nome_fornecedor, tipo_fornecedor, cidade_fornecedor, bairro_fornecedor, telefone_fornecedor)
                st.success("Fornecedor cadastrado.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    conn = get_connection()
    df_fornecedores = pd.read_sql_query("SELECT id, nome, tipo, cidade, bairro, telefone FROM fornecedores ORDER BY nome", conn)
    df_produtos_cot = pd.read_sql_query("SELECT id, nome, marca, unidade FROM produtos ORDER BY nome, unidade", conn)
    conn.close()
    with st.expander(f"Fornecedores cadastrados ({len(df_fornecedores)})", expanded=False):
        st.dataframe(df_fornecedores.drop(columns=["id"]), width="stretch")

    if not df_produtos_cot.empty and not df_fornecedores.empty:
        with st.expander("Registrar uma cotação", expanded=True):
            with st.form("form_nova_cotacao"):
                col_q1, col_q2 = st.columns(2)
                with col_q1:
                    produto_cotado_id = st.selectbox(
                        "Produto", df_produtos_cot["id"].tolist(),
                        format_func=lambda pid: df_produtos_cot.loc[df_produtos_cot["id"] == pid].apply(
                            lambda r: f"{r['nome']} ({r['unidade']})", axis=1
                        ).iloc[0],
                    )
                    fornecedor_cotacao_id = st.selectbox(
                        "Mercado / distribuidora", df_fornecedores["id"].tolist(),
                        format_func=lambda fid: df_fornecedores.loc[df_fornecedores["id"] == fid, "nome"].iloc[0],
                    )
                with col_q2:
                    preco_cotado = st.number_input("Preço (R$)", min_value=0.01, value=1.0, step=0.01, format="%.2f")
                    data_cotada = st.date_input("Data da cotação", value=datetime.now().date())
                    marca_cotada = st.text_input("Marca ofertada")
                    origem_cotada = st.text_input("Origem / observação (opcional)", placeholder="Ex.: visita à loja, telefone, encarte")
                salvar_cotacao = st.form_submit_button("Salvar cotação")
            if salvar_cotacao:
                try:
                    _, status_cotacao = registrar_cotacao(
                        produto_cotado_id, fornecedor_cotacao_id, preco_cotado,
                        data_cotada, marca_cotada, origem_cotada,
                    )
                    st.success("Cotação " + ("atualizada" if status_cotacao == "atualizada" else "registrada") + ".")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    conn = get_connection()
    df_comparativo = pd.read_sql_query("""
        WITH recentes AS (
            SELECT c.*, ROW_NUMBER() OVER (
                PARTITION BY produto_id, fornecedor_id ORDER BY data_cotacao DESC, id DESC
            ) AS ordem_fornecedor
            FROM cotacoes c
        )
        SELECT p.nome AS produto, p.unidade, f.nome AS fornecedor,
               r.marca AS marca_ofertada, r.preco, r.data_cotacao, r.origem
        FROM recentes r
        JOIN produtos p ON r.produto_id = p.id
        JOIN fornecedores f ON r.fornecedor_id = f.id
        WHERE r.ordem_fornecedor = 1
        ORDER BY p.nome, r.preco, f.nome
    """, conn)
    conn.close()
    if not df_comparativo.empty:
        df_menor = (
            df_comparativo.sort_values(["preco", "data_cotacao"], ascending=[True, False])
            .groupby(["produto", "unidade"], as_index=False).first()
            [["produto", "unidade", "fornecedor", "marca_ofertada", "preco", "data_cotacao"]]
        )
        st.subheader("Melhor oferta mais recente por produto")
        st.dataframe(df_menor, width="stretch")
        st.subheader("Comparativo: última oferta de cada fornecedor")
        st.dataframe(df_comparativo, width="stretch")
    else:
        st.info("Registre ou importe cotações para ver a comparação entre fornecedores.")
elif menu == "Estoque":
    st.title("Estoque")
    st.caption("O saldo abaixo é calculado pelas movimentações registradas desde a ativação deste controle. Confira a contagem física e lance o saldo inicial como entrada.")
    conn = get_connection()
    df_saldo = pd.read_sql_query("""
        SELECT p.id AS produto_id, p.nome AS produto, p.marca, p.unidade,
               COALESCE(SUM(CASE
                   WHEN m.tipo IN ('ENTRADA', 'AJUSTE_ENTRADA') THEN m.quantidade
                   WHEN m.tipo IN ('SAIDA', 'AJUSTE_SAIDA') THEN -m.quantidade
                   ELSE 0 END), 0) AS saldo_calculado
        FROM produtos p
        LEFT JOIN movimentacoes_estoque m ON m.produto_id = p.id
        GROUP BY p.id, p.nome, p.marca, p.unidade
        ORDER BY p.nome, p.marca
    """, conn)
    df_produtos = pd.read_sql_query("SELECT id, nome, marca, unidade FROM produtos ORDER BY nome, marca", conn)
    conn.close()
    st.dataframe(df_saldo.drop(columns=["produto_id"]), width="stretch")

    if not df_produtos.empty:
        with st.form("form_movimento_estoque"):
            produto_id = st.selectbox(
                "Produto",
                df_produtos["id"].tolist(),
                format_func=lambda pid: df_produtos.loc[df_produtos["id"] == pid].apply(
                    lambda r: f"{r['nome']} — {r['marca']} ({r['unidade']})", axis=1
                ).iloc[0],
            )
            tipo_label = st.selectbox("Movimentação", ["Entrada / saldo inicial", "Saída", "Ajuste para mais", "Ajuste para menos"])
            quantidade = st.number_input("Quantidade", min_value=0.01, value=1.0, step=1.0)
            custo_unitario = st.number_input("Custo unitário (R$; necessário para calcular o preço da cesta)", min_value=0.0, value=0.0, step=0.10)
            observacao = st.text_input("Observação (opcional)")
            salvar_movimento = st.form_submit_button("Registrar movimentação")

        if salvar_movimento:
            tipo_movimento = {
                "Entrada / saldo inicial": "ENTRADA",
                "Saída": "SAIDA",
                "Ajuste para mais": "AJUSTE_ENTRADA",
                "Ajuste para menos": "AJUSTE_SAIDA",
            }[tipo_label]
            with closing(get_connection()) as conn, conn:
                cursor = conn.cursor()
                saldo_atual = cursor.execute("""
                    SELECT COALESCE(SUM(CASE
                        WHEN tipo IN ('ENTRADA', 'AJUSTE_ENTRADA') THEN quantidade
                        ELSE -quantidade END), 0)
                    FROM movimentacoes_estoque WHERE produto_id = ?
                """, (produto_id,)).fetchone()[0]
                if tipo_movimento in ("SAIDA", "AJUSTE_SAIDA") and quantidade > saldo_atual:
                    st.error(f"Saldo insuficiente. Saldo calculado: {saldo_atual:g}.")
                else:
                    cursor.execute("""
                        INSERT INTO movimentacoes_estoque
                            (produto_id, tipo, quantidade, custo_unitario, observacao)
                        VALUES (?, ?, ?, ?, ?)
                    """, (produto_id, tipo_movimento, quantidade, custo_unitario if tipo_movimento in ("ENTRADA", "AJUSTE_ENTRADA") and custo_unitario > 0 else None, observacao.strip() or None))
                    conn.commit()
                    st.success("Movimentação registrada.")
                    st.rerun()
    else:
        st.info("Cadastre ou importe produtos para começar a controlar o estoque.")
elif menu == "Histórico de preços":
    st.title("Histórico de preços")
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT c.data_cotacao, (p.nome || ' - ' || p.marca) AS prod, f.nome AS atac, c.marca AS marca_ofertada, c.preco
        FROM cotacoes c
        JOIN produtos p ON c.produto_id=p.id
        JOIN fornecedores f ON c.fornecedor_id=f.id
        ORDER BY c.data_cotacao DESC
    """, conn)
    conn.close()
    if not df.empty:
        st.dataframe(df, width="stretch")
    else:
        st.info("Nenhuma cotação registada.")

elif menu == "Compras e lotes":
    st.title("Planejar compras e registrar lote")
    st.markdown("Defina quanto comprar de cada produto. O sistema sugere a oferta mais barata entre as últimas cotações registradas e permite escolher outro fornecedor.")
    nome_lote_input = st.text_input("Identificação do lote", value=f"Lote - {datetime.now():%d/%m/%Y}")
    observacao_lote = st.text_input("Observação da compra (opcional)")

    conn = get_connection()
    df_ofertas = pd.read_sql_query("""
        WITH recentes AS (
            SELECT c.*, ROW_NUMBER() OVER (
                PARTITION BY produto_id, fornecedor_id ORDER BY data_cotacao DESC, id DESC
            ) AS ordem_fornecedor
            FROM cotacoes c
        )
        SELECT r.id AS cotacao_id, r.produto_id, r.fornecedor_id,
               p.nome AS produto, p.unidade, f.nome AS fornecedor,
               r.marca AS marca_ofertada, r.preco, r.data_cotacao
        FROM recentes r
        JOIN produtos p ON r.produto_id = p.id
        JOIN fornecedores f ON r.fornecedor_id = f.id
        WHERE r.ordem_fornecedor = 1
        ORDER BY p.nome, r.preco, f.nome
    """, conn)
    conn.close()

    if not df_ofertas.empty:
        lote_itens_salvar = []
        st.caption("Quantidade zero = produto fora deste lote. Escolha o fornecedor e informe a quantidade realmente comprada.")
        for produto_id, ofertas in df_ofertas.groupby("produto_id", sort=False):
            ofertas = ofertas.sort_values(["preco", "data_cotacao"], ascending=[True, False]).reset_index(drop=True)
            primeira = ofertas.iloc[0]
            col_prod, col_fornec, col_qtd, col_sub = st.columns([3, 3, 1.5, 1.5])
            with col_prod:
                st.markdown(f"**{primeira['produto']}** ({primeira['unidade']})")
            with col_fornec:
                quote_options = ofertas["cotacao_id"].tolist()
                quote_label = {
                    int(r["cotacao_id"]): f"{r['fornecedor']} — {r['marca_ofertada'] or 'marca não informada'} — R$ {r['preco']:.2f} ({r['data_cotacao']})"
                    for _, r in ofertas.iterrows()
                }
                quote_id = st.selectbox(
                    "Oferta", quote_options,
                    format_func=lambda qid: quote_label[int(qid)],
                    key=f"lote_quote_{produto_id}",
                )
                oferta_escolhida = ofertas.loc[ofertas["cotacao_id"] == quote_id].iloc[0]
            with col_qtd:
                qtd_compra = st.number_input("Quantidade", min_value=0.0, value=0.0, step=1.0, key=f"lote_qtd_{produto_id}")
            with col_sub:
                st.markdown(f"**Subtotal**  \nR$ {qtd_compra * float(oferta_escolhida['preco']):.2f}")
            if qtd_compra > 0:
                lote_itens_salvar.append({
                    "produto_id": int(produto_id),
                    "fornecedor_id": int(oferta_escolhida["fornecedor_id"]),
                    "cotacao_id": int(oferta_escolhida["cotacao_id"]),
                    "quantidade": float(qtd_compra),
                    "preco_unitario": float(oferta_escolhida["preco"]),
                })

        total_lote = sum(i["quantidade"] * i["preco_unitario"] for i in lote_itens_salvar)
        st.metric("Custo estimado do lote", f"R$ {total_lote:.2f}")
        if st.button("Salvar lote e dar entrada no estoque", type="primary"):
            try:
                resultado = salvar_lote_compra(nome_lote_input, lote_itens_salvar, observacao_lote)
                st.success(f"Lote {resultado['nome']} salvo: {resultado['itens']} produtos, R$ {resultado['custo_total']:.2f}. Estoque atualizado.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    else:
        st.warning("Não há cotações para sugerir compras. Cadastre fornecedores e cotações primeiro.")
elif menu == "Cestas e vendas":
    st.title("Cestas e vendas")
    st.caption("Configure o conteúdo de cada modelo, monte a quantidade possível e acompanhe as vendas.")
    tab_receitas, tab_montagem, tab_vendas = st.tabs(["Modelos e composição", "Montagem e preço", "Disponíveis e vendas"])

    conn = get_connection()
    df_tipos = pd.read_sql_query("SELECT id, nome, descricao FROM tipos_cesta ORDER BY nome", conn)
    df_produtos = pd.read_sql_query("SELECT id, nome, unidade FROM produtos ORDER BY nome", conn)
    conn.close()

    with tab_receitas:
        st.subheader("Criar modelo de cesta")
        with st.form("form_tipo_cesta"):
            nome_tipo = st.text_input("Nome do modelo", placeholder="Ex.: Cesta Família Econômica")
            desc_tipo = st.text_input("Descrição")
            criar_tipo = st.form_submit_button("Criar modelo")
        if criar_tipo:
            try:
                with closing(get_connection()) as conn, conn:
                    conn.execute("INSERT INTO tipos_cesta (nome, descricao) VALUES (?, ?)", (nome_tipo.strip(), desc_tipo.strip() or None))
                st.success("Modelo criado.")
                st.rerun()
            except Exception as e:
                st.error(f"Não foi possível criar o modelo: {e}")

        if not df_tipos.empty and not df_produtos.empty:
            tipo_receita = st.selectbox(
                "Modelo para editar", df_tipos["id"].tolist(),
                format_func=lambda tid: df_tipos.loc[df_tipos["id"] == tid, "nome"].iloc[0],
                key="tipo_receita",
            )
            conn = get_connection()
            df_receita = pd.read_sql_query("""
                SELECT cc.produto_id, p.nome AS produto, p.unidade, cc.quantidade
                FROM composicao_cesta cc JOIN produtos p ON p.id = cc.produto_id
                WHERE cc.tipo_cesta_id = ? ORDER BY p.nome
            """, conn, params=(tipo_receita,))
            conn.close()
            st.markdown("**Composição por cesta**")
            if df_receita.empty:
                st.info("Este modelo ainda não tem itens.")
            else:
                st.dataframe(df_receita.drop(columns=["produto_id"]), width="stretch")

            with st.form("form_item_receita"):
                col_r1, col_r2 = st.columns([3, 1])
                with col_r1:
                    produto_receita = st.selectbox(
                        "Produto para incluir/atualizar", df_produtos["id"].tolist(),
                        format_func=lambda pid: df_produtos.loc[df_produtos["id"] == pid].apply(
                            lambda r: f"{r['nome']} ({r['unidade']})", axis=1
                        ).iloc[0],
                    )
                with col_r2:
                    quantidade_receita = st.number_input("Quantidade por cesta", min_value=0.01, value=1.0, step=0.25)
                salvar_item_receita = st.form_submit_button("Incluir ou atualizar item")
            if salvar_item_receita:
                itens = [{"produto_id": int(r["produto_id"]), "quantidade": float(r["quantidade"])} for _, r in df_receita.iterrows()]
                atualizados = False
                for item in itens:
                    if item["produto_id"] == int(produto_receita):
                        item["quantidade"] = float(quantidade_receita)
                        atualizados = True
                        break
                if not atualizados:
                    itens.append({"produto_id": int(produto_receita), "quantidade": float(quantidade_receita)})
                salvar_receita(tipo_receita, itens)
                st.success("Receita salva.")
                st.rerun()

            if not df_receita.empty:
                with st.form("form_remover_item_receita"):
                    produto_remover = st.selectbox(
                        "Remover item da receita", df_receita["produto_id"].tolist(),
                        format_func=lambda pid: df_receita.loc[df_receita["produto_id"] == pid, "produto"].iloc[0],
                    )
                    remover_item = st.form_submit_button("Remover item")
                if remover_item:
                    itens = [
                        {"produto_id": int(r["produto_id"]), "quantidade": float(r["quantidade"])}
                        for _, r in df_receita.iterrows() if int(r["produto_id"]) != int(produto_remover)
                    ]
                    if itens:
                        salvar_receita(tipo_receita, itens)
                        st.success("Item removido e receita atualizada.")
                    else:
                        with closing(get_connection()) as conn, conn:
                            conn.execute("DELETE FROM composicao_cesta WHERE tipo_cesta_id = ?", (tipo_receita,))
                        st.success("A receita agora está vazia.")
                    st.rerun()

    with tab_montagem:
        if not df_tipos.empty:
            tipo_montagem = st.selectbox(
                "Modelo a montar", df_tipos["id"].tolist(),
                format_func=lambda tid: df_tipos.loc[df_tipos["id"] == tid, "nome"].iloc[0],
                key="tipo_montagem",
            )
            itens_plano, max_cestas = obter_planejamento_montagem(tipo_montagem)
            if not itens_plano:
                st.info("Cadastre a receita do modelo na aba 'Modelos e receitas'.")
            else:
                df_plano = pd.DataFrame(itens_plano).rename(columns={
                    "nome": "Produto", "unidade": "Unidade", "por_cesta": "Qtd. por cesta",
                    "saldo": "Saldo atual", "custo_medio": "Custo médio unitário",
                })
                st.dataframe(df_plano[["Produto", "Unidade", "Qtd. por cesta", "Saldo atual", "Custo médio unitário"]], width="stretch")
                custos_pendentes = [i["nome"] for i in itens_plano if i["custo_medio"] is None]
                if max_cestas <= 0:
                    st.warning("O estoque atual não permite montar uma cesta completa. Registre saldo inicial ou compre um lote.")
                elif custos_pendentes:
                    st.warning("Registre custo unitário nas entradas de estoque para calcular o preço: " + ", ".join(custos_pendentes))
                else:
                    qtd_montar = st.number_input("Quantidade de cestas a montar", min_value=1, max_value=max_cestas, value=max_cestas, step=1)
                    col_c1, col_c2, col_c3 = st.columns(3)
                    with col_c1:
                        frete_montagem = st.number_input("Frete total desta montagem (R$)", min_value=0.0, value=0.0, step=1.0)
                    with col_c2:
                        embalagem = st.number_input("Embalagem por cesta (R$)", min_value=0.0, value=3.50, step=0.25)
                    with col_c3:
                        margem = st.slider("Margem bruta desejada (%)", min_value=0.0, max_value=80.0, value=25.0, step=1.0)
                    custo_produtos_unitario = sum(i["por_cesta"] * i["custo_medio"] for i in itens_plano)
                    frete_unitario = frete_montagem / qtd_montar
                    custo_unitario = custo_produtos_unitario + embalagem + frete_unitario
                    preco_sugerido = custo_unitario / (1 - margem / 100)
                    col_m1, col_m2, col_m3 = st.columns(3)
                    col_m1.metric("Custo de produtos por cesta", f"R$ {custo_produtos_unitario:.2f}")
                    col_m2.metric("Custo total por cesta", f"R$ {custo_unitario:.2f}")
                    col_m3.metric("Preço sugerido", f"R$ {preco_sugerido:.2f}")
                    observacao_montagem = st.text_input("Observação desta montagem")
                    if st.button("Montar e baixar os itens do estoque", type="primary"):
                        try:
                            resultado = montar_cestas(tipo_montagem, qtd_montar, frete_montagem, embalagem, margem, observacao_montagem)
                            st.success(f"Montadas {resultado['quantidade']} cestas. Preço sugerido: R$ {resultado['preco_sugerido']:.2f} cada.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
        else:
            st.info("Crie um modelo de cesta primeiro.")

    with tab_vendas:
        resumo = [dict(r) for r in obter_resumo_cestas()]
        if resumo:
            df_resumo = pd.DataFrame(resumo)
            df_resumo["Disponíveis"] = df_resumo["montadas"] - df_resumo["vendidas"]
            st.dataframe(df_resumo[["nome", "montadas", "vendidas", "Disponíveis"]].rename(columns={
                "nome": "Modelo", "montadas": "Montadas", "vendidas": "Vendidas",
            }), width="stretch")
            disponiveis = df_resumo[df_resumo["Disponíveis"] > 0]
            if not disponiveis.empty:
                with st.form("form_venda_cesta"):
                    tipo_venda = st.selectbox(
                        "Modelo vendido", disponiveis["id"].tolist(),
                        format_func=lambda tid: disponiveis.loc[disponiveis["id"] == tid, "nome"].iloc[0],
                    )
                    saldo_cestas = int(disponiveis.loc[disponiveis["id"] == tipo_venda, "Disponíveis"].iloc[0])
                    quantidade_venda = st.number_input("Quantidade vendida", min_value=1, max_value=max(1, saldo_cestas), value=1, step=1)
                    ultima_referencia = float(disponiveis.loc[disponiveis["id"] == tipo_venda, "ultimo_preco_sugerido"].iloc[0]) if "ultimo_preco_sugerido" in disponiveis.columns else 0.0
                    preco_venda = st.number_input("Preço por cesta (R$)", min_value=0.01, value=max(0.01, ultima_referencia), step=0.50)
                    canal = st.selectbox("Canal de venda", ["Venda direta", "WhatsApp", "Entrega", "Revendedor", "Outro"])
                    vendedor = st.text_input("Vendedor")
                    zona = st.text_input("Bairro / local de entrega", value="Boa Vista")
                    imposto = st.number_input("Imposto estimado (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5)
                    salvar_venda = st.form_submit_button("Registrar venda")
                if salvar_venda:
                    try:
                        registrar_venda(tipo_venda, quantidade_venda, preco_venda, canal, vendedor, zona, imposto)
                        st.success("Venda registrada; saldo de cestas prontas atualizado.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            else:
                st.info("Ainda não há cestas montadas para venda.")
