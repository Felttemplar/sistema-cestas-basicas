import re
from contextlib import closing
from datetime import date
from numbers import Real

import pandas as pd

from core.database import get_connection, normalizar_fornecedor


def _normalizar(texto):
    import unicodedata
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", texto.lower())


_UNIT_ALIASES = {
    "un": "UN", "und": "UN", "unid": "UN", "unidade": "UN",
    "pc": "PC", "pct": "PC", "pacote": "PC",
    "fr": "FR", "frasco": "FR",
    "lt": "LT", "l": "LT", "litro": "LT",
    "g": "G", "gr": "G", "grama": "G", "gramas": "G",
    "kg": "KG", "quilograma": "KG", "quilogramas": "KG",
}


def normalizar_nome_produto(valor):
    return _normalizar(valor)


def normalizar_unidade(valor):
    texto = _normalizar(valor)
    return _UNIT_ALIASES.get(texto, str(valor).strip().upper())


def _achar_coluna(colunas, *nomes):
    mapa = {_normalizar(coluna): coluna for coluna in colunas}
    for nome in nomes:
        if _normalizar(nome) in mapa:
            return mapa[_normalizar(nome)]
    return None


def ler_planilha_cotacoes(arquivo):
    """Lê o modelo tabular do app ou a aba legada CONCORRENTES COTAÇÃO.

    Na planilha legada, nomes dos mercados estão na linha 6 e os dados começam
    na linha 7. Colunas de preço da cesta recomendada não são tratadas como
    cotações de item.
    """
    xls = pd.ExcelFile(arquivo, engine="openpyxl")
    aba = next((
        nome for nome in xls.sheet_names
        if "concorrentes" in _normalizar(nome) and "cotacao" in _normalizar(nome)
    ), xls.sheet_names[0])
    bruto = pd.read_excel(xls, sheet_name=aba, header=None, dtype=object)

    linha_cabecalho = None
    col_produto = col_unidade = None
    for idx in range(min(30, len(bruto))):
        mapa = {_normalizar(valor): col for col, valor in bruto.iloc[idx].items() if not pd.isna(valor)}
        col_produto = mapa.get("produtos", mapa.get("produto"))
        col_unidade = mapa.get("und", mapa.get("unidade"))
        if col_produto is not None:
            linha_cabecalho = idx
            break

    if linha_cabecalho is None:
        return pd.read_excel(xls, sheet_name=aba, engine="openpyxl")

    cabecalho = bruto.iloc[linha_cabecalho]
    col_marca_base = next((c for c, v in cabecalho.items() if _normalizar(v) == "marca"), None)
    excluidas = {"alimentos", "produto", "produtos", "und", "unidade", "marca", "cotacao"}
    colunas_fornecedor = []
    for col, valor in cabecalho.items():
        nome = str(valor).strip() if not pd.isna(valor) else ""
        if col <= col_produto or not nome or _normalizar(nome) in excluidas:
            continue
        # Colunas identificadas como loja na linha de cabeçalho; a coluna
        # imediatamente anterior só é marca quando seu cabeçalho diz MARCA.
        marca_col = col - 1 if col > 0 and _normalizar(cabecalho.iloc[col - 1]) == "marca" else None
        colunas_fornecedor.append((col, nome, marca_col))

    if not colunas_fornecedor:
        raise ValueError(f"A aba '{aba}' tem a coluna de produto, mas não encontrei colunas de fornecedores.")

    registros = []
    for idx in range(linha_cabecalho + 1, len(bruto)):
        nome_produto = bruto.iat[idx, col_produto]
        if pd.isna(nome_produto) or not str(nome_produto).strip():
            continue
        registro = {
            "Nome do Produto": str(nome_produto).strip(),
            "Unidade": bruto.iat[idx, col_unidade] if col_unidade is not None else None,
            "Marca": bruto.iat[idx, col_marca_base] if col_marca_base is not None else None,
            "Origem": f"{aba.strip()} — linha {idx + 1}",
        }
        for preco_col, fornecedor, marca_col in colunas_fornecedor:
            registro[f"Preço {fornecedor}"] = bruto.iat[idx, preco_col]
            if marca_col is not None:
                registro[f"Marca {fornecedor}"] = bruto.iat[idx, marca_col]
        registros.append(registro)

    df = pd.DataFrame(registros)
    df.attrs["aba_origem"] = aba
    df.attrs["cabecalho_linha"] = linha_cabecalho + 1
    return df


def _preco(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    if isinstance(valor, Real):
        preco = float(valor)
    else:
        texto = re.sub(r"[^0-9,.-]", "", str(valor).strip())
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        try:
            preco = float(texto)
        except ValueError as exc:
            raise ValueError(f"Preço inválido: {valor}") from exc
    if preco <= 0:
        raise ValueError(f"O preço deve ser maior que zero: {valor}")
    return round(preco, 2)


def _data_iso(valor, data_padrao):
    if valor is None or pd.isna(valor) or str(valor).strip() == "":
        return data_padrao
    try:
        return pd.to_datetime(valor, dayfirst=True).date().isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Data de cotação inválida: {valor}") from exc


def importar_cotacoes(df, data_cotacao=None):
    """Importa cotações em formato comparativo ou longo para qualquer fornecedor.

    O formato longo usa uma linha por produto/fornecedor. O comparativo usa
    colunas "Preço <Fornecedor>" e, opcionalmente, "Marca <Fornecedor>".
    """
    if df is None or df.empty:
        raise ValueError("A planilha está vazia.")

    col_produto = _achar_coluna(df.columns, "Nome do Produto", "Produto", "Nome")
    col_unidade = _achar_coluna(df.columns, "Unidade", "UND")
    col_marca_geral = _achar_coluna(df.columns, "Marca", "Marca Principal")
    col_fornecedor_longo = _achar_coluna(df.columns, "Fornecedor", "Mercado", "Distribuidora")
    col_preco_longo = _achar_coluna(df.columns, "Preço", "Preco", "Valor")
    col_marca_longa = _achar_coluna(df.columns, "Marca Ofertada", "Marca do Produto") or col_marca_geral
    col_data = _achar_coluna(df.columns, "Data Cotação", "Data da Cotação", "Data")
    col_origem = _achar_coluna(df.columns, "Origem", "Fonte", "Observação", "Observacao")

    colunas_faltando = []
    if not col_produto:
        colunas_faltando.append("Nome do Produto")
    if not col_unidade:
        colunas_faltando.append("Unidade")

    colunas_preco_largo = []
    for coluna in df.columns:
        normalizada = _normalizar(coluna)
        if normalizada.startswith("preco") and normalizada not in {_normalizar(x) for x in (col_preco_longo,)}:
            etiqueta = re.sub(r"^(?:preco|valor)(?:do)?", "", normalizada)
            if etiqueta:
                nome_fornecedor = str(coluna)
                nome_fornecedor = re.sub(r"^(?:preço|preco|valor)\s*(?:do\s*)?", "", nome_fornecedor, flags=re.IGNORECASE).strip(" :-_")
                colunas_preco_largo.append((coluna, nome_fornecedor))

    formato_longo = bool(col_fornecedor_longo and col_preco_longo)
    if not formato_longo and not colunas_preco_largo:
        colunas_faltando.append("Preço e Fornecedor, ou colunas Preço <Fornecedor>")
    if colunas_faltando:
        raise ValueError("Colunas não encontradas: " + ", ".join(colunas_faltando))

    hoje = data_cotacao or date.today().isoformat()
    linhas = []
    erros = []
    cotacoes_excluidas = 0
    chaves_oferta = set()
    for numero, (_, row) in enumerate(df.iterrows(), start=2):
        nome = "" if pd.isna(row[col_produto]) else str(row[col_produto]).strip()
        if not nome or nome.lower() in {"nan", "none"}:
            continue
        unidade_bruta = "UN" if pd.isna(row[col_unidade]) or not str(row[col_unidade]).strip() else row[col_unidade]
        unidade = normalizar_unidade(unidade_bruta)
        marca_geral = "" if not col_marca_geral or pd.isna(row[col_marca_geral]) else str(row[col_marca_geral]).strip()
        origem = "" if not col_origem or pd.isna(row[col_origem]) else str(row[col_origem]).strip()
        try:
            data_linha = _data_iso(row[col_data] if col_data else None, hoje)
        except ValueError as exc:
            erros.append(f"Linha {numero}: {exc}")
            continue

        ofertas = []
        if formato_longo:
            fornecedor = "" if pd.isna(row[col_fornecedor_longo]) else str(row[col_fornecedor_longo]).strip()
            if fornecedor:
                try:
                    preco = _preco(row[col_preco_longo])
                except ValueError as exc:
                    erros.append(f"Linha {numero}: {exc}")
                    continue
                if preco is not None:
                    marca = "" if not col_marca_longa or pd.isna(row[col_marca_longa]) else str(row[col_marca_longa]).strip()
                    ofertas.append((fornecedor, marca or marca_geral or None, preco, origem, data_linha))
        else:
            for coluna_preco, fornecedor in colunas_preco_largo:
                try:
                    preco = _preco(row[coluna_preco])
                except ValueError as exc:
                    erros.append(f"Linha {numero}: {exc}")
                    continue
                if preco is None:
                    continue
                col_marca = _achar_coluna(df.columns, f"Marca {fornecedor}", f"Marca do {fornecedor}")
                marca = "" if not col_marca or pd.isna(row[col_marca]) else str(row[col_marca]).strip()
                ofertas.append((fornecedor, marca or marca_geral or None, preco, origem, data_linha))

        if normalizar_nome_produto(nome).startswith("cesta"):
            cotacoes_excluidas += len(ofertas)
            ofertas = []
        for fornecedor, marca, preco, _, data_item in ofertas:
            chave = (normalizar_nome_produto(nome), unidade, normalizar_fornecedor(fornecedor), data_item)
            if chave in chaves_oferta:
                erros.append(f"Linha {numero}: cotação repetida para {nome} em {fornecedor} na data {data_item}.")
            chaves_oferta.add(chave)
        linhas.append((nome.upper(), unidade, marca_geral.upper() or "VARIÁVEL", ofertas))

    if erros:
        raise ValueError("Corrija os dados antes de importar:\n" + "\n".join(erros[:20]))
    if not linhas:
        raise ValueError("Nenhum produto válido foi encontrado na planilha.")

    produtos_conferidos = 0
    produtos_novos = 0
    cotacoes_salvas = 0
    cotacoes_novas = 0
    cotacoes_atualizadas = 0
    with closing(get_connection()) as conn, conn:
        cursor = conn.cursor()
        produtos_existentes = cursor.execute("SELECT id, nome, unidade FROM produtos").fetchall()
        fornecedores_existentes = cursor.execute("SELECT id, nome, nome_normalizado FROM fornecedores").fetchall()
        for nome, unidade, marca_padrao, ofertas in linhas:
            chave_nome = normalizar_nome_produto(nome)
            produto = next((
                item for item in produtos_existentes
                if normalizar_nome_produto(item["nome"]) == chave_nome
                and normalizar_unidade(item["unidade"]) == unidade
            ), None)
            if produto:
                produto_id = produto["id"]
                cursor.execute(
                    "UPDATE produtos SET marca = ? WHERE id = ? AND (marca IS NULL OR trim(marca) = '' OR upper(marca) = 'GERAL')",
                    (marca_padrao, produto_id),
                )
            else:
                cursor.execute(
                    "INSERT INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)",
                    (nome, marca_padrao, unidade, nome),
                )
                produto_id = cursor.lastrowid
                produtos_existentes.append({"id": produto_id, "nome": nome, "unidade": unidade})
                produtos_novos += 1
            produtos_conferidos += 1

            for fornecedor, marca, preco, origem, data_item in ofertas:
                chave_fornecedor = normalizar_fornecedor(fornecedor)
                registro_fornecedor = next((
                    item for item in fornecedores_existentes
                    if (item["nome_normalizado"] or normalizar_fornecedor(item["nome"])) == chave_fornecedor
                ), None)
                if registro_fornecedor:
                    fornecedor_id = registro_fornecedor["id"]
                else:
                    nome_normalizado = chave_fornecedor
                    cursor.execute(
                        "INSERT INTO fornecedores (nome, tipo, cidade, nome_normalizado) VALUES (?, ?, ?, ?)",
                        (fornecedor, "Distribuidora" if "DISTRIBUIDORA" in fornecedor.upper() else "Mercado", "Boa Vista", nome_normalizado),
                    )
                    fornecedor_id = cursor.lastrowid
                    fornecedores_existentes.append({"id": fornecedor_id, "nome": fornecedor, "nome_normalizado": nome_normalizado})
                existente = cursor.execute(
                    "SELECT id FROM cotacoes WHERE produto_id = ? AND fornecedor_id = ? AND data_cotacao = ? ORDER BY id DESC LIMIT 1",
                    (produto_id, fornecedor_id, data_item),
                ).fetchone()
                if existente:
                    cursor.execute(
                        "UPDATE cotacoes SET preco = ?, marca = ?, origem = ? WHERE id = ?",
                        (preco, marca, origem or None, existente["id"]),
                    )
                    cotacoes_atualizadas += 1
                else:
                    cursor.execute(
                        "INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao, marca, origem) VALUES (?, ?, ?, ?, ?, ?)",
                        (produto_id, fornecedor_id, preco, data_item, marca, origem or None),
                    )
                    cotacoes_novas += 1
                cotacoes_salvas += 1

    datas = sorted({oferta[4] for _, _, _, ofertas in linhas for oferta in ofertas})
    if data_cotacao is not None:
        data_resultado = data_cotacao.isoformat() if hasattr(data_cotacao, "isoformat") else str(data_cotacao)
    elif len(datas) == 1:
        data_resultado = datas[0]
    elif datas:
        data_resultado = f"{datas[0]} a {datas[-1]}"
    else:
        data_resultado = "nenhuma cotação com preço"
    return {
        "produtos": produtos_conferidos,
        "produtos_novos": produtos_novos,
        "cotacoes": cotacoes_salvas,
        "cotacoes_novas": cotacoes_novas,
        "cotacoes_atualizadas": cotacoes_atualizadas,
        "cotacoes_excluidas": cotacoes_excluidas,
        "data": data_resultado,
    }
