import argparse
from pathlib import Path

import pandas as pd

from core.importacao import importar_cotacoes


def importar_dados_excel(file_path):
    caminho = Path(file_path)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
    df = pd.read_excel(caminho, sheet_name=0, engine="openpyxl")
    resultado = importar_cotacoes(df)
    print(
        f"Importação concluída na base oficial: {resultado['produtos']} produtos e "
        f"{resultado['cotacoes']} cotações em {resultado['data']}."
    )
    return resultado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importa cotações para a base usada pelo app.")
    parser.add_argument(
        "arquivo",
        help="Planilha .xlsx com colunas nomeadas de produto, unidade e preços por loja.",
    )
    args = parser.parse_args()
    importar_dados_excel(args.arquivo)
