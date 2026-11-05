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
    cotacoes_salvas = 0
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
                else:
                    cursor.execute(
                        "INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao, marca, origem) VALUES (?, ?, ?, ?, ?, ?)",
                        (produto_id, fornecedor_id, preco, data_item, marca, origem or None),
                    )
                cotacoes_salvas += 1

    return {"produtos": produtos_conferidos, "cotacoes": cotacoes_salvas, "data": data_cotacao or "datas da planilha"}
