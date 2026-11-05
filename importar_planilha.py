import argparse
from pathlib import Path

from core.importacao import importar_cotacoes, ler_planilha_cotacoes


def importar_dados_excel(file_path, data_cotacao=None):
    caminho = Path(file_path)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    df = ler_planilha_cotacoes(caminho)
    resultado = importar_cotacoes(df, data_cotacao=data_cotacao)
    print(
        f"Importação na base oficial em {resultado['data']}: {resultado['produtos']} produtos conferidos "
        f"({resultado['produtos_novos']} novos), {resultado['cotacoes']} ofertas processadas "
        f"({resultado['cotacoes_novas']} novas e {resultado['cotacoes_atualizadas']} atualizadas), "
        f"{resultado['cotacoes_excluidas']} preços de cestas prontas ignorados na compra de insumos."
    )
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importa cotações para a base usada pelo app.")
    parser.add_argument(
        "arquivo",
        help="Planilha .xlsx com colunas nomeadas de produto, unidade e preços por loja.",
    )
    parser.add_argument(
        "--data-cotacao",
        help="Data real em que os preços foram pesquisados (AAAA-MM-DD). Se omitida, usa a data de hoje.",
    )
    args = parser.parse_args()
    importar_dados_excel(args.arquivo, args.data_cotacao)
