import streamlit as st
import pandas as pd
from datetime import datetime
from contextlib import closing
from pathlib import Path
from uuid import uuid4
from core.database import DB_NAME, init_db, get_connection
from core.importacao import importar_cotacoes, ler_planilha_cotacoes, normalizar_unidade, normalizar_nome_produto
from core.operations import (criar_fornecedor, registrar_cotacao, salvar_lote_compra, obter_detalhes_lote, obter_historico_lotes, salvar_receita, obter_status_receita, obter_planejamento_montagem, montar_cestas, obter_resumo_cestas, registrar_venda)
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


def _iniciar_novo_lote():
    for produto_id in st.session_state.get("lote_produtos_ids", []):
        st.session_state.pop(f"lote_qtd_{produto_id}", None)
    st.session_state["lote_chave_requisicao"] = uuid4().hex
    st.session_state["lote_salvo_id"] = None


def _apresentacao(conteudo, unidade_conteudo):
    if pd.isna(conteudo) or conteudo in (None, 0, "") or not unidade_conteudo:
        return "Conteúdo não informado"
    return f"{float(conteudo):g} {unidade_conteudo} por embalagem"


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
    st.caption(f"Base ativa: {Path(DB_NAME).name}")
    with st.expander("Diagnóstico da base"):
        st.code(str(DB_NAME), language=None)

if menu == "Visão geral":
    st.title("Painel da operação")
    st.caption("Acompanhe o caminho da cotação até as cestas disponíveis para venda.")
    st.caption(f"Dados lidos de: `{DB_NAME}`")
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
    df_modelos = pd.read_sql_query("SELECT id, nome, descricao FROM tipos_cesta ORDER BY nome", conn)
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
    k5.metric("Saldo somado dos produtos", f"{float(resumo['unidades_estoque']):,.0f}".replace(',', '.'))
    k6.metric("Cestas montadas", int(resumo['cestas_montadas']))
    k7.metric("Cestas vendidas", int(resumo['cestas_vendidas']))
    st.caption("O saldo somado é quantidade de produtos nas respectivas unidades; não é quantidade de cestas prontas.")
    linhas_rendimento = []
    for _, modelo in df_modelos.iterrows():
        itens_modelo, limite = obter_planejamento_montagem(int(modelo["id"]))
        status = obter_status_receita(int(modelo["id"]))
        if not status["completa"]:
            quantidade_possivel = "Receita incompleta"
            limitante = "Complete a composição"
            situacao = (
                f"{status['itens_cadastrados']}/{status['itens_minimos']} itens mínimos"
                if status["itens_minimos"] is not None
                else "Sem composição cadastrada"
            )
        else:
            quantidade_possivel = limite
            gargalos = [i for i in itens_modelo if int(i["saldo"] // i["por_cesta"]) == limite]
            limitante = ", ".join(i["nome"] for i in gargalos[:3]) if gargalos else "—"
            situacao = "Sem estoque" if limite == 0 else "Receita pronta"
        linhas_rendimento.append({
            "Modelo": modelo["nome"], "Itens cadastrados": status["itens_cadastrados"],
            "Cestas possíveis": quantidade_possivel, "Item limitante": limitante,
            "Situação": situacao,
        })
    st.markdown("### Rendimento por modelo de cesta")
    st.dataframe(pd.DataFrame(linhas_rendimento), hide_index=True, width="stretch")
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
            df_up = ler_planilha_cotacoes(uploaded_file)
            st.success(f"Planilha reconhecida: {len(df_up)} produtos/linhas para conferência. Aba: {df_up.attrs.get('aba_origem', 'primeira aba')}")
            st.dataframe(df_up.head(30), width="stretch")
            st.caption("A importação usa os preços de cada mercado, mantém a marca ofertada e recalcula a menor oferta. Não importa a coluna de resultado da planilha nem preços de cestas prontas na lista de itens para compra. Cotações antigas são preservadas; produto/loja/data repetidos são atualizados.")
            if "Data Cotação" not in df_up.columns and "Data" not in df_up.columns and "Data da Cotação" not in df_up.columns:
                st.warning("Esta aba não traz a data da pesquisa. Informe a data real da cotação para não registrar preços antigos como atuais.")
            data_referencia = st.date_input("Data de referência da cotação", value=datetime.now().date())
            if st.button("🚀 Validar e salvar cotações", type="primary"):
                resultado = importar_cotacoes(df_up, data_cotacao=data_referencia.isoformat())
                st.success(
                    f"Importação concluída em {resultado['data']}: {resultado['produtos']} produtos conferidos "
                    f"({resultado['produtos_novos']} novos), {resultado['cotacoes']} ofertas processadas "
                    f"({resultado['cotacoes_novas']} novas e {resultado['cotacoes_atualizadas']} atualizadas); "
                    f"{resultado['cotacoes_excluidas']} preços de cestas prontas separados do fluxo de compras."
                )
        except Exception as e:
            st.error(f"A planilha não foi importada: {e}")
elif menu == "Produtos":
    st.title("Cadastro de produtos")
    st.caption("A unidade cadastrada é a unidade usada nas compras, no saldo e na receita da cesta.")
    with st.form("form_prod"):
        n = st.text_input("Nome do Produto (Ex: Arroz 1kg, Feijão 1kg)")
        m = st.text_input("Marca principal (opcional; as marcas cotadas são registradas por loja)")
        u = st.selectbox("Unidade de compra/estoque", ["KG", "PCT", "UN", "FR", "LT", "CX", "SC"])
        col_conteudo, col_unidade_conteudo = st.columns(2)
        with col_conteudo:
            conteudo_embalagem = st.number_input("Conteúdo por embalagem (opcional)", min_value=0.0, value=0.0, step=50.0)
        with col_unidade_conteudo:
            unidade_conteudo = st.selectbox("Unidade do conteúdo", ["Não se aplica", "G", "KG", "ML", "L"])
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
                    st.warning("Já existe um produto com este nome e unidade. Revise o cadastro existente em vez de criar outro.")
                    conn.close()
                else:
                    cursor.execute(
                        "INSERT INTO produtos (nome, marca, unidade, grupo_equivalencia, conteudo_embalagem, unidade_conteudo) VALUES (?, ?, ?, ?, ?, ?)",
                        (nome, marca_principal, unidade_produto, grupo, conteudo_embalagem or None, unidade_conteudo if conteudo_embalagem else None),
                    )
                    conn.commit()
                    conn.close()
                    st.success("Produto cadastrado com sucesso.")
                    st.rerun()
    conn = get_connection()
    df_catalogo = pd.read_sql_query("""
        SELECT id, nome AS Produto, marca AS Marca, unidade AS 'Unidade de estoque',
               conteudo_embalagem, unidade_conteudo
        FROM produtos ORDER BY nome
    """, conn)
    conn.close()
    if not df_catalogo.empty:
        df_catalogo["Apresentação"] = df_catalogo.apply(
            lambda r: _apresentacao(r["conteudo_embalagem"], r["unidade_conteudo"]), axis=1
        )
        st.markdown("### Catálogo e unidades")
        st.dataframe(df_catalogo.drop(columns=["conteudo_embalagem", "unidade_conteudo"]), hide_index=True, width="stretch")
        with st.expander("Revisar unidade de compra e conteúdo da embalagem"):
            st.warning("Alterar a unidade muda como o saldo e as receitas existentes são interpretados. Confira lotes, saldos e receitas antes de salvar; o sistema não converte quantidades automaticamente.")
            produto_apresentacao_id = st.selectbox(
                "Produto", df_catalogo["id"].tolist(), key="produto_apresentacao_id",
                format_func=lambda pid: df_catalogo.loc[df_catalogo["id"] == pid, "Produto"].iloc[0],
            )
            produto_atual = df_catalogo.loc[df_catalogo["id"] == produto_apresentacao_id].iloc[0]
            unidade_atual = str(produto_atual["Unidade de estoque"])
            unidades_disponiveis = list(dict.fromkeys(["KG", "PC", "PCT", "UN", "UND", "FR", "LT", "G", "ML", "SC", "SC/G", "CX", unidade_atual]))
            unidade_atual_normalizada = normalizar_unidade(unidade_atual)
            idx_unidade = next((i for i, uom in enumerate(unidades_disponiveis) if normalizar_unidade(uom) == unidade_atual_normalizada), 0)
            with st.form("form_atualizar_apresentacao"):
                unidade_estoque_nova = st.selectbox("Unidade usada nas compras, estoque e receita", unidades_disponiveis, index=idx_unidade, key=f"produto_unidade_nova_{produto_apresentacao_id}")
                col_conteudo_edit, col_unidade_edit = st.columns(2)
                with col_conteudo_edit:
                    conteudo_novo = st.number_input(
                        "Conteúdo por embalagem", min_value=0.0,
                        value=float(produto_atual["conteudo_embalagem"]) if pd.notna(produto_atual["conteudo_embalagem"]) else 0.0,
                        step=50.0, key=f"produto_conteudo_novo_{produto_apresentacao_id}",
                    )
                with col_unidade_edit:
                    unidade_conteudo_nova = st.selectbox(
                        "Unidade do conteúdo", ["Não se aplica", "G", "KG", "ML", "L"],
                        index=( ["Não se aplica", "G", "KG", "ML", "L"].index(produto_atual["unidade_conteudo"])
                                if produto_atual["unidade_conteudo"] in ["Não se aplica", "G", "KG", "ML", "L"] else 0 ),
                        key=f"produto_unidade_conteudo_novo_{produto_apresentacao_id}",
                    )
                salvar_apresentacao = st.form_submit_button("Atualizar apresentação")
            if salvar_apresentacao:
                try:
                    with closing(get_connection()) as conn, conn:
                        conn.execute("""
                            UPDATE produtos SET unidade=?, conteudo_embalagem=?, unidade_conteudo=? WHERE id=?
                        """, (
                            normalizar_unidade(unidade_estoque_nova), conteudo_novo or None,
                            unidade_conteudo_nova if conteudo_novo else None, produto_apresentacao_id,
                        ))
                    st.success("Unidade e apresentação atualizadas. Os preços cotados continuam vinculados ao produto.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não foi possível atualizar este produto: {e}")
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
          AND upper(trim(p.nome)) NOT LIKE 'CESTA %'
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
               p.conteudo_embalagem, p.unidade_conteudo,
               COALESCE(SUM(CASE
                   WHEN m.tipo IN ('ENTRADA', 'AJUSTE_ENTRADA') THEN m.quantidade
                   WHEN m.tipo IN ('SAIDA', 'AJUSTE_SAIDA') THEN -m.quantidade
                   ELSE 0 END), 0) AS saldo_calculado
        FROM produtos p
        LEFT JOIN movimentacoes_estoque m ON m.produto_id = p.id
        GROUP BY p.id, p.nome, p.marca, p.unidade, p.conteudo_embalagem, p.unidade_conteudo
        ORDER BY p.nome, p.marca
    """, conn)
    df_produtos = pd.read_sql_query("SELECT id, nome, marca, unidade, conteudo_embalagem, unidade_conteudo FROM produtos ORDER BY nome, marca", conn)
    conn.close()
    df_saldo["Apresentação"] = df_saldo.apply(lambda r: _apresentacao(r["conteudo_embalagem"], r["unidade_conteudo"]), axis=1)
    st.dataframe(df_saldo.drop(columns=["produto_id", "conteudo_embalagem", "unidade_conteudo"]), width="stretch")
    st.caption("O saldo é exibido na unidade de compra/estoque do cadastro. Conteúdo da embalagem é informativo e não converte quantidades automaticamente.")

    if not df_produtos.empty:
        with st.form("form_movimento_estoque"):
            produto_id = st.selectbox(
                "Produto",
                df_produtos["id"].tolist(),
                format_func=lambda pid: df_produtos.loc[df_produtos["id"] == pid].apply(
                    lambda r: f"{r['nome']} — {r['marca']} ({r['unidade']}; {_apresentacao(r['conteudo_embalagem'], r['unidade_conteudo'])})", axis=1
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
    st.markdown("Informe a quantidade realmente comprada em cada unidade de compra/estoque. O sistema mostra o saldo antes e a projeção após a entrada.")
    st.session_state.setdefault("lote_chave_requisicao", uuid4().hex)

    conn = get_connection()
    df_ofertas = pd.read_sql_query("""
        WITH recentes AS (
            SELECT c.*, ROW_NUMBER() OVER (
                PARTITION BY produto_id, fornecedor_id ORDER BY data_cotacao DESC, id DESC
            ) AS ordem_fornecedor
            FROM cotacoes c
        )
        SELECT r.id AS cotacao_id, r.produto_id, r.fornecedor_id,
               p.nome AS produto, p.unidade, p.conteudo_embalagem, p.unidade_conteudo,
               COALESCE((SELECT SUM(CASE WHEN m.tipo IN ('ENTRADA','AJUSTE_ENTRADA') THEN m.quantidade ELSE -m.quantidade END)
                         FROM movimentacoes_estoque m WHERE m.produto_id=p.id),0) AS saldo_atual,
               f.nome AS fornecedor,
               r.marca AS marca_ofertada, r.preco, r.data_cotacao
        FROM recentes r
        JOIN produtos p ON r.produto_id = p.id
        JOIN fornecedores f ON r.fornecedor_id = f.id
        WHERE r.ordem_fornecedor = 1
          AND upper(trim(p.nome)) NOT LIKE 'CESTA %'
        ORDER BY p.nome, r.preco, f.nome
    """, conn)
    conn.close()
    st.session_state["lote_produtos_ids"] = [int(pid) for pid in df_ofertas["produto_id"].drop_duplicates()] if not df_ofertas.empty else []

    if st.session_state.get("lote_salvo_id"):
        lote_salvo, itens_salvos = obter_detalhes_lote(st.session_state["lote_salvo_id"])
        if lote_salvo:
            texto_status = "Este lote já havia sido salvo; o estoque não recebeu uma segunda entrada." if st.session_state.get("lote_ja_existia") else "Lote registrado. As quantidades abaixo foram gravadas e entraram no estoque uma única vez."
            st.success(texto_status)
            st.subheader(f"Comprovante — {lote_salvo['nome_lote']}")
            st.caption(f"Número: {lote_salvo['numero_lote']} · Data: {lote_salvo['data_compra']} · Total: R$ {lote_salvo['custo_total']:.2f}")
            df_itens_salvos = pd.DataFrame(itens_salvos)
            if not df_itens_salvos.empty:
                df_itens_salvos["Apresentação"] = df_itens_salvos.apply(lambda r: _apresentacao(r["conteudo_embalagem"], r["unidade_conteudo"]), axis=1)
                st.dataframe(df_itens_salvos.rename(columns={
                    "produto":"Produto", "unidade":"Unidade", "quantidade":"Quantidade salva",
                    "fornecedor":"Fornecedor", "preco_unitario":"Preço unitário", "subtotal":"Subtotal",
                })[["Produto", "Unidade", "Apresentação", "Quantidade salva", "Fornecedor", "Preço unitário", "Subtotal"]], hide_index=True, width="stretch")
        st.button("Iniciar outro lote", on_click=_iniciar_novo_lote)
    elif not df_ofertas.empty:
        lote_itens_salvar = []
        linhas_previa = []
        nome_lote_input = st.text_input("Identificação do lote", value=f"Lote - {datetime.now():%d/%m/%Y}", key="nome_lote_input")
        observacao_lote = st.text_input("Observação da compra (opcional)", key="observacao_lote")
        st.caption("Quantidade zero exclui o produto deste lote. O saldo projetado é apenas uma prévia até salvar.")
        for produto_id, ofertas in df_ofertas.groupby("produto_id", sort=False):
            ofertas = ofertas.sort_values(["preco", "data_cotacao"], ascending=[True, False]).reset_index(drop=True)
            primeira = ofertas.iloc[0]
            col_prod, col_fornec, col_saldo, col_qtd, col_proj, col_sub = st.columns([2.7, 3.2, 1.05, 1.25, 1.15, 1.15])
            with col_prod:
                st.markdown(f"**{primeira['produto']}**")
                st.caption(f"Unidade: {primeira['unidade']} · {_apresentacao(primeira['conteudo_embalagem'], primeira['unidade_conteudo'])}")
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
            with col_saldo:
                st.markdown("Saldo antes")
                st.markdown(f"**{float(primeira['saldo_atual']):g} {primeira['unidade']}**")
            with col_qtd:
                qtd_compra = st.number_input(f"Comprar ({primeira['unidade']})", min_value=0.0, value=0.0, step=1.0, key=f"lote_qtd_{produto_id}")
            with col_proj:
                st.markdown("Saldo após")
                st.markdown(f"**{float(primeira['saldo_atual']) + qtd_compra:g} {primeira['unidade']}**")
            with col_sub:
                st.markdown("Subtotal")
                st.markdown(f"**R$ {qtd_compra * float(oferta_escolhida['preco']):.2f}**")
            if qtd_compra > 0:
                item_lote = {
                    "produto_id": int(produto_id),
                    "fornecedor_id": int(oferta_escolhida["fornecedor_id"]),
                    "cotacao_id": int(oferta_escolhida["cotacao_id"]),
                    "quantidade": float(qtd_compra),
                    "preco_unitario": float(oferta_escolhida["preco"]),
                }
                lote_itens_salvar.append(item_lote)
                linhas_previa.append({
                    "Produto": primeira["produto"], "Unidade": primeira["unidade"],
                    "Saldo antes": float(primeira["saldo_atual"]), "Quantidade comprada": float(qtd_compra),
                    "Saldo após": float(primeira["saldo_atual"]) + float(qtd_compra),
                    "Fornecedor": oferta_escolhida["fornecedor"], "Subtotal": float(qtd_compra) * float(oferta_escolhida["preco"]),
                })

        total_lote = sum(i["quantidade"] * i["preco_unitario"] for i in lote_itens_salvar)
        st.metric("Custo estimado do lote", f"R$ {total_lote:.2f}")
        if linhas_previa:
            with st.expander("Conferir quantidades deste lote", expanded=True):
                st.dataframe(pd.DataFrame(linhas_previa), hide_index=True, width="stretch")
        if st.button("Salvar lote e dar entrada no estoque", type="primary", disabled=not lote_itens_salvar):
            try:
                resultado = salvar_lote_compra(
                    nome_lote_input, lote_itens_salvar, observacao_lote,
                    chave_requisicao=st.session_state["lote_chave_requisicao"],
                )
                st.session_state["lote_salvo_id"] = resultado["id"]
                st.session_state["lote_ja_existia"] = resultado["ja_existia"]
                st.rerun()
            except Exception as e:
                st.error(str(e))
    else:
        st.warning("Não há cotações para sugerir compras. Cadastre fornecedores e cotações primeiro.")
    historico_lotes = [dict(r) for r in obter_historico_lotes()]
    st.markdown("### Histórico de lotes")
    if historico_lotes:
        st.dataframe(pd.DataFrame(historico_lotes).rename(columns={
            "numero_lote":"Número", "nome_lote":"Lote", "data_compra":"Data",
            "custo_total":"Custo total", "quantidade_itens":"Linhas de produtos",
        }).drop(columns=["id"]), hide_index=True, width="stretch")
        lote_detalhe_id = st.selectbox(
            "Consultar itens de um lote", [r["id"] for r in historico_lotes],
            format_func=lambda lid: next(f"{r['nome_lote']} · {r['data_compra']}" for r in historico_lotes if r["id"] == lid),
            key="lote_historico_detalhe",
        )
        if lote_detalhe_id != st.session_state.get("lote_salvo_id"):
            _, itens_historicos = obter_detalhes_lote(lote_detalhe_id)
            if itens_historicos:
                st.dataframe(pd.DataFrame(itens_historicos).rename(columns={
                    "produto":"Produto", "unidade":"Unidade", "quantidade":"Quantidade salva",
                    "fornecedor":"Fornecedor", "preco_unitario":"Preço unitário", "subtotal":"Subtotal",
                })[["Produto", "Unidade", "Quantidade salva", "Fornecedor", "Preço unitário", "Subtotal"]], hide_index=True, width="stretch")
            else:
                st.warning("Este registro não tem linhas de produtos; ele não alterou o estoque.")
    else:
        st.info("Nenhum lote salvo ainda.")
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
                SELECT cc.produto_id, p.nome AS produto, p.unidade, p.conteudo_embalagem,
                       p.unidade_conteudo, cc.quantidade
                FROM composicao_cesta cc JOIN produtos p ON p.id = cc.produto_id
                WHERE cc.tipo_cesta_id = ? ORDER BY p.nome
            """, conn, params=(tipo_receita,))
            conn.close()
            status_receita = obter_status_receita(tipo_receita)
            if status_receita["itens_minimos"] is not None:
                if status_receita["completa"]:
                    st.success(f"Composição atende ao mínimo: {status_receita['itens_cadastrados']} itens cadastrados.")
                else:
                    st.warning(f"Receita incompleta: {status_receita['itens_cadastrados']} de {status_receita['itens_minimos']} itens mínimos; faltam {status_receita['itens_faltando']}.")
            elif not status_receita["completa"]:
                st.warning("Este modelo ainda não tem uma composição cadastrada.")
            else:
                st.info(f"{status_receita['itens_cadastrados']} itens na composição. Confirme se a receita está completa para este modelo.")
            st.markdown("**Composição por cesta**")
            if df_receita.empty:
                st.info("Este modelo ainda não tem itens.")
            else:
                df_receita["Apresentação"] = df_receita.apply(lambda r: _apresentacao(r["conteudo_embalagem"], r["unidade_conteudo"]), axis=1)
                st.dataframe(df_receita.drop(columns=["produto_id", "conteudo_embalagem", "unidade_conteudo"]), width="stretch")

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
            status_receita_montagem = obter_status_receita(tipo_montagem)
            if not itens_plano:
                st.info("Cadastre a receita do modelo na aba 'Modelos e receitas'.")
            else:
                df_plano = pd.DataFrame(itens_plano).rename(columns={
                    "nome": "Produto", "unidade": "Unidade", "por_cesta": "Qtd. por cesta",
                    "saldo": "Saldo atual", "custo_medio": "Custo médio unitário",
                })
                df_plano["Apresentação"] = df_plano.apply(lambda r: _apresentacao(r["conteudo_embalagem"], r["unidade_conteudo"]), axis=1)
                st.dataframe(df_plano[["Produto", "Unidade", "Apresentação", "Qtd. por cesta", "Saldo atual", "Custo médio unitário"]], width="stretch")
                custos_pendentes = [i["nome"] for i in itens_plano if i["custo_medio"] is None]
                if status_receita_montagem["itens_minimos"] is not None and not status_receita_montagem["completa"]:
                    st.warning(
                        f"Rendimento parcial: {max_cestas} usando apenas os {status_receita_montagem['itens_cadastrados']} itens cadastrados. "
                        f"O modelo exige pelo menos {status_receita_montagem['itens_minimos']} itens; complete a receita antes de montar."
                    )
                elif not status_receita_montagem["completa"]:
                    st.warning("Confirme a composição do modelo antes de registrar a montagem.")
                elif max_cestas <= 0:
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
