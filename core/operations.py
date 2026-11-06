from contextlib import closing
from datetime import date
import re
import sqlite3
from uuid import uuid4

from core.database import get_connection


def criar_fornecedor(nome, tipo="Mercado", cidade="Boa Vista", bairro=None, telefone=None):
    nome = nome.strip()
    if not nome:
        raise ValueError("Informe o nome do fornecedor.")
    with closing(get_connection()) as conn, conn:
        # A verificação normalizada é feita em Python para suportar acentos e prefixos.
        from core.database import normalizar_fornecedor
        chave = normalizar_fornecedor(nome)
        linhas = conn.execute("SELECT id, nome, nome_normalizado FROM fornecedores").fetchall()
        duplicado = next((r for r in linhas if (r["nome_normalizado"] or normalizar_fornecedor(r["nome"])) == chave), None)
        if duplicado:
            raise ValueError(f"Já existe o fornecedor '{duplicado['nome']}'.")
        cur = conn.execute(
            "INSERT INTO fornecedores (nome, nome_normalizado, tipo, cidade, bairro, telefone) VALUES (?, ?, ?, ?, ?, ?)",
            (nome, chave, tipo, cidade.strip() or None if cidade else None, bairro.strip() or None if bairro else None, telefone.strip() or None if telefone else None),
        )
        return cur.lastrowid


def registrar_cotacao(produto_id, fornecedor_id, preco, data_cotacao, marca=None, origem=None):
    preco = round(float(preco), 2)
    if preco <= 0:
        raise ValueError("O preço deve ser maior que zero.")
    data = data_cotacao.isoformat() if hasattr(data_cotacao, "isoformat") else str(data_cotacao)
    with closing(get_connection()) as conn, conn:
        existente = conn.execute(
            "SELECT id FROM cotacoes WHERE produto_id = ? AND fornecedor_id = ? AND data_cotacao = ? ORDER BY id DESC LIMIT 1",
            (produto_id, fornecedor_id, data),
        ).fetchone()
        if existente:
            conn.execute(
                "UPDATE cotacoes SET preco = ?, marca = ?, origem = ? WHERE id = ?",
                (preco, marca.strip() or None if marca else None, origem.strip() or None if origem else None, existente["id"]),
            )
            return existente["id"], "atualizada"
        cur = conn.execute(
            "INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao, marca, origem) VALUES (?, ?, ?, ?, ?, ?)",
            (produto_id, fornecedor_id, preco, data, marca.strip() or None if marca else None, origem.strip() or None if origem else None),
        )
        return cur.lastrowid, "registrada"


def salvar_lote_compra(nome, itens, observacao=None, chave_requisicao=None):
    itens_validos = [i for i in itens if float(i["quantidade"]) > 0]
    if not itens_validos:
        raise ValueError("Selecione ao menos um produto e informe a quantidade comprada.")
    for item in itens_validos:
        if float(item["preco_unitario"]) <= 0:
            raise ValueError("O preço unitário de cada item do lote deve ser maior que zero.")
    custo_total = sum(float(i["quantidade"]) * float(i["preco_unitario"]) for i in itens_validos)
    nome = nome.strip() or f"Lote {date.today():%d/%m/%Y}"
    chave_requisicao = chave_requisicao or uuid4().hex
    with closing(get_connection()) as conn, conn:
        existente = conn.execute(
            "SELECT id, nome_lote, custo_total FROM lotes WHERE chave_requisicao = ?",
            (chave_requisicao,),
        ).fetchone()
        if existente:
            quantidade_itens = conn.execute(
                "SELECT COUNT(*) FROM itens_lote WHERE lote_id = ?", (existente["id"],)
            ).fetchone()[0]
            return {
                "id": existente["id"], "nome": existente["nome_lote"],
                "custo_total": existente["custo_total"], "itens": quantidade_itens,
                "ja_existia": True,
            }
        numero = f"LOTE-{date.today():%Y%m%d}-{uuid4().hex[:8].upper()}"
        try:
            cur = conn.execute(
                "INSERT INTO lotes (numero_lote, nome_lote, data_compra, observacao, custo_total, custo_total_insumos, chave_requisicao) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (numero, nome, date.today().isoformat(), observacao.strip() or None if observacao else None, custo_total, custo_total, chave_requisicao),
            )
        except sqlite3.IntegrityError:
            existente = conn.execute(
                "SELECT id, nome_lote, custo_total FROM lotes WHERE chave_requisicao = ?",
                (chave_requisicao,),
            ).fetchone()
            if not existente:
                raise
            quantidade_itens = conn.execute(
                "SELECT COUNT(*) FROM itens_lote WHERE lote_id = ?", (existente["id"],)
            ).fetchone()[0]
            return {
                "id": existente["id"], "nome": existente["nome_lote"],
                "custo_total": existente["custo_total"], "itens": quantidade_itens,
                "ja_existia": True,
            }
        lote_id = cur.lastrowid
        for item in itens_validos:
            produto_id = int(item["produto_id"])
            fornecedor_id = int(item["fornecedor_id"])
            cotacao_id = int(item["cotacao_id"])
            quantidade = float(item["quantidade"])
            preco = round(float(item["preco_unitario"]), 2)
            oferta = conn.execute(
                "SELECT produto_id, fornecedor_id FROM cotacoes WHERE id = ?", (cotacao_id,)
            ).fetchone()
            if not oferta or oferta["produto_id"] != produto_id or oferta["fornecedor_id"] != fornecedor_id:
                raise ValueError("Uma oferta selecionada não corresponde ao produto/fornecedor do lote.")
            conn.execute(
                "INSERT INTO itens_lote (lote_id, produto_id, fornecedor_id, cotacao_id, quantidade, preco_unitario, subtotal) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (lote_id, produto_id, fornecedor_id, cotacao_id, quantidade, preco, quantidade * preco),
            )
            conn.execute(
                "INSERT INTO movimentacoes_estoque (produto_id, lote_id, tipo, quantidade, custo_unitario, observacao) VALUES (?, ?, 'ENTRADA', ?, ?, ?)",
                (produto_id, lote_id, quantidade, preco, f"Compra: {nome}"),
            )
    return {"id": lote_id, "nome": nome, "custo_total": custo_total, "itens": len(itens_validos), "ja_existia": False}


def obter_detalhes_lote(lote_id):
    with closing(get_connection()) as conn:
        lote = conn.execute("""
            SELECT id, numero_lote, nome_lote, data_compra, observacao, custo_total
            FROM lotes WHERE id = ?
        """, (lote_id,)).fetchone()
        if not lote:
            return None, []
        itens = conn.execute("""
            SELECT p.nome AS produto, p.unidade, p.conteudo_embalagem, p.unidade_conteudo,
                   i.quantidade, i.preco_unitario, i.subtotal, f.nome AS fornecedor,
                   c.data_cotacao
            FROM itens_lote i
            JOIN produtos p ON p.id = i.produto_id
            LEFT JOIN fornecedores f ON f.id = i.fornecedor_id
            LEFT JOIN cotacoes c ON c.id = i.cotacao_id
            WHERE i.lote_id = ? ORDER BY p.nome
        """, (lote_id,)).fetchall()
    return dict(lote), [dict(item) for item in itens]


def obter_historico_lotes(limite=50):
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT l.id, l.numero_lote, l.nome_lote, l.data_compra, l.custo_total,
                   COUNT(i.id) AS quantidade_itens
            FROM lotes l LEFT JOIN itens_lote i ON i.lote_id = l.id
            GROUP BY l.id ORDER BY l.id DESC LIMIT ?
        """, (int(limite),)).fetchall()


def obter_status_receita(tipo_cesta_id):
    with closing(get_connection()) as conn:
        tipo = conn.execute("SELECT nome, descricao FROM tipos_cesta WHERE id = ?", (tipo_cesta_id,)).fetchone()
        cadastrados = conn.execute(
            "SELECT COUNT(*) FROM composicao_cesta WHERE tipo_cesta_id = ?", (tipo_cesta_id,)
        ).fetchone()[0]
    if not tipo:
        return {"itens_cadastrados": 0, "itens_minimos": None, "itens_faltando": None, "completa": False}
    rotulo = f"{tipo['nome']} {tipo['descricao'] or ''}"
    faixa = re.search(r"(\d{1,3})\s*[-–]\s*(\d{1,3})\s*(?:ITENS?)?", rotulo, re.IGNORECASE)
    minimo = int(faixa.group(1)) if faixa else None
    faltando = max(0, minimo - cadastrados) if minimo is not None else 0
    return {
        "itens_cadastrados": cadastrados,
        "itens_minimos": minimo,
        "itens_faltando": faltando,
        "completa": cadastrados > 0 and (minimo is None or cadastrados >= minimo),
    }


def salvar_receita(tipo_cesta_id, itens):
    limpos = {}
    for item in itens:
        produto_id = int(item["produto_id"])
        quantidade = float(item["quantidade"])
        if quantidade <= 0:
            raise ValueError("A quantidade de cada item na receita deve ser maior que zero.")
        limpos[produto_id] = quantidade
    if not limpos:
        raise ValueError("A receita precisa conter ao menos um item.")
    with closing(get_connection()) as conn, conn:
        conn.execute("DELETE FROM composicao_cesta WHERE tipo_cesta_id = ?", (tipo_cesta_id,))
        conn.executemany(
            "INSERT INTO composicao_cesta (tipo_cesta_id, produto_id, quantidade) VALUES (?, ?, ?)",
            [(tipo_cesta_id, p, q) for p, q in limpos.items()],
        )
    return len(limpos)


def montar_cestas(tipo_cesta_id, quantidade_cestas, frete_total=0, embalagem_por_cesta=0, margem_bruta=25, observacao=None):
    quantidade_cestas = int(quantidade_cestas)
    if quantidade_cestas <= 0:
        raise ValueError("Informe uma quantidade de cestas maior que zero.")
    if margem_bruta < 0 or margem_bruta >= 100:
        raise ValueError("A margem bruta deve estar entre 0% e menos de 100%.")
    status_receita = obter_status_receita(tipo_cesta_id)
    if not status_receita["completa"]:
        if status_receita["itens_minimos"] is not None:
            raise ValueError(
                f"Receita incompleta: {status_receita['itens_cadastrados']} de "
                f"{status_receita['itens_minimos']} itens mínimos. Complete a composição antes de montar."
            )
        raise ValueError("Cadastre e confirme ao menos um item na receita antes de montar.")

    with closing(get_connection()) as conn, conn:
        receita = conn.execute("""
            SELECT cc.produto_id, cc.quantidade AS por_cesta, p.nome, p.unidade,
                   p.conteudo_embalagem, p.unidade_conteudo,
                   COALESCE(SUM(CASE WHEN m.tipo IN ('ENTRADA','AJUSTE_ENTRADA') THEN m.quantidade
                                     WHEN m.tipo IN ('SAIDA','AJUSTE_SAIDA') THEN -m.quantidade ELSE 0 END),0) AS saldo,
                   SUM(CASE WHEN m.tipo IN ('ENTRADA','AJUSTE_ENTRADA') AND m.custo_unitario IS NOT NULL
                            THEN m.quantidade * m.custo_unitario ELSE 0 END)
                   / NULLIF(SUM(CASE WHEN m.tipo IN ('ENTRADA','AJUSTE_ENTRADA') AND m.custo_unitario IS NOT NULL
                                     THEN m.quantidade ELSE 0 END),0) AS custo_medio
            FROM composicao_cesta cc
            JOIN produtos p ON p.id = cc.produto_id
            LEFT JOIN movimentacoes_estoque m ON m.produto_id = p.id
            WHERE cc.tipo_cesta_id = ?
            GROUP BY cc.produto_id, cc.quantidade, p.nome, p.unidade, p.conteudo_embalagem, p.unidade_conteudo
            ORDER BY p.nome
        """, (tipo_cesta_id,)).fetchall()
        if not receita:
            raise ValueError("Este modelo de cesta ainda não tem uma receita cadastrada.")
        faltas = []
        custo_produtos = 0.0
        for item in receita:
            necessario = item["por_cesta"] * quantidade_cestas
            if item["saldo"] < necessario:
                faltas.append(f"{item['nome']}: precisa {necessario:g} {item['unidade']}, há {item['saldo']:g}")
            if item["custo_medio"] is None:
                raise ValueError(f"Falta custo de entrada para {item['nome']}; registre a entrada com custo unitário.")
            custo_produtos += item["por_cesta"] * item["custo_medio"]
        if faltas:
            raise ValueError("Estoque insuficiente:\n" + "\n".join(faltas))

        frete_unitario = float(frete_total) / quantidade_cestas
        custo_total_unitario = custo_produtos + float(embalagem_por_cesta) + frete_unitario
        preco_sugerido = custo_total_unitario / (1 - margem_bruta / 100)
        cur = conn.execute("""
            INSERT INTO montagens_cesta
                (tipo_cesta_id, quantidade, custo_produtos_unitario, custo_embalagem_unitario,
                 frete_unitario, margem_bruta, preco_venda_sugerido, observacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (tipo_cesta_id, quantidade_cestas, custo_produtos, float(embalagem_por_cesta), frete_unitario, float(margem_bruta), preco_sugerido, observacao.strip() or None if observacao else None))
        montagem_id = cur.lastrowid
        for item in receita:
            quantidade_total = item["por_cesta"] * quantidade_cestas
            custo = float(item["custo_medio"])
            conn.execute("""
                INSERT INTO itens_montagem
                    (montagem_id, produto_id, quantidade_por_cesta, quantidade_total, custo_unitario, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (montagem_id, item["produto_id"], item["por_cesta"], quantidade_total, custo, quantidade_total * custo))
            conn.execute("""
                INSERT INTO movimentacoes_estoque
                    (produto_id, tipo, quantidade, custo_unitario, observacao)
                VALUES (?, 'SAIDA', ?, ?, ?)
            """, (item["produto_id"], quantidade_total, custo, f"Montagem cesta #{montagem_id}"))
    return {
        "id": montagem_id,
        "quantidade": quantidade_cestas,
        "custo_produtos_unitario": custo_produtos,
        "frete_unitario": frete_unitario,
        "custo_total_unitario": custo_total_unitario,
        "preco_sugerido": preco_sugerido,
    }



def obter_planejamento_montagem(tipo_cesta_id):
    with closing(get_connection()) as conn:
        itens = conn.execute("""
            SELECT cc.produto_id, cc.quantidade AS por_cesta, p.nome, p.unidade,
                   p.conteudo_embalagem, p.unidade_conteudo,
                   COALESCE(SUM(CASE WHEN m.tipo IN ('ENTRADA','AJUSTE_ENTRADA') THEN m.quantidade
                                     WHEN m.tipo IN ('SAIDA','AJUSTE_SAIDA') THEN -m.quantidade ELSE 0 END),0) AS saldo,
                   SUM(CASE WHEN m.tipo IN ('ENTRADA','AJUSTE_ENTRADA') AND m.custo_unitario IS NOT NULL
                            THEN m.quantidade * m.custo_unitario ELSE 0 END)
                   / NULLIF(SUM(CASE WHEN m.tipo IN ('ENTRADA','AJUSTE_ENTRADA') AND m.custo_unitario IS NOT NULL
                                     THEN m.quantidade ELSE 0 END),0) AS custo_medio
            FROM composicao_cesta cc
            JOIN produtos p ON p.id = cc.produto_id
            LEFT JOIN movimentacoes_estoque m ON m.produto_id = p.id
            WHERE cc.tipo_cesta_id = ?
            GROUP BY cc.produto_id, cc.quantidade, p.nome, p.unidade, p.conteudo_embalagem, p.unidade_conteudo
            ORDER BY p.nome
        """, (tipo_cesta_id,)).fetchall()
    max_cestas = min((int(i["saldo"] // i["por_cesta"]) for i in itens), default=0)
    return [dict(i) for i in itens], max_cestas


def obter_resumo_cestas():
    with closing(get_connection()) as conn:
        return conn.execute("""
            SELECT t.id, t.nome,
                   COALESCE((SELECT SUM(m.quantidade) FROM montagens_cesta m WHERE m.tipo_cesta_id=t.id),0) AS montadas,
                   COALESCE((SELECT SUM(v.quantidade_vendida) FROM vendas v WHERE v.tipo_cesta_id=t.id),0) AS vendidas,
                   COALESCE((SELECT m.preco_venda_sugerido FROM montagens_cesta m WHERE m.tipo_cesta_id=t.id ORDER BY m.data_montagem DESC, m.id DESC LIMIT 1),0) AS ultimo_preco_sugerido
            FROM tipos_cesta t ORDER BY t.nome
        """).fetchall()
def registrar_venda(tipo_cesta_id, quantidade, preco_unitario, canal, vendedor=None, zona=None, imposto=0):
    quantidade = int(quantidade)
    preco_unitario = round(float(preco_unitario), 2)
    if quantidade <= 0 or preco_unitario <= 0:
        raise ValueError("Quantidade e preço da venda devem ser maiores que zero.")
    with closing(get_connection()) as conn, conn:
        montadas = conn.execute("SELECT COALESCE(SUM(quantidade),0) FROM montagens_cesta WHERE tipo_cesta_id=?", (tipo_cesta_id,)).fetchone()[0]
        vendidas = conn.execute("SELECT COALESCE(SUM(quantidade_vendida),0) FROM vendas WHERE tipo_cesta_id=?", (tipo_cesta_id,)).fetchone()[0]
        if quantidade > montadas - vendidas:
            raise ValueError(f"Só há {montadas-vendidas} cestas prontas deste modelo.")
        cur = conn.execute("""
            INSERT INTO vendas (tipo_cesta_id, quantidade_vendida, preco_unitario_praticado, canal_venda,
                                vendedor, zona_entrega, imposto_percentual, data_venda)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (tipo_cesta_id, quantidade, preco_unitario, canal, vendedor or "Venda Direta", zona or "Boa Vista", float(imposto)))
        return cur.lastrowid
