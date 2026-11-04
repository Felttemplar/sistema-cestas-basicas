import pandas as pd
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cesta_basica.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def importar_dados_excel(file_path):
    if not os.path.exists(file_path):
        print(f"❌ Arquivo '{file_path}' não encontrado na pasta atual!")
        return

    conn = get_connection()
    cursor = conn.cursor()
    
    print(f"📂 Lendo a planilha: {file_path}")
    try:
        df = pd.read_excel(file_path, sheet_name="CONCORRENTESCOTAÇÃO PRECIFICAÇÃ", header=4)
    except Exception as e:
        print(f"❌ Erro ao abrir aba da planilha: {e}")
        conn.close()
        return
    
    atacadistas_map = {
        4: "Assaí Atacadista",
        6: "Atacadão",
        8: "Supermercado Gavião",
        10: "Novo Tempo",
        12: "Nova Era",
        14: "Goiano",
        16: "Aguiar",
        18: "Distribuidora 1"
    }
    
    itens_importados = 0
    for idx, row in df.iterrows():
        if len(row) < 4:
            continue
            
        nome_prod = row.iloc[1]
        unidade = row.iloc[2]
        
        if pd.isna(nome_prod) or str(nome_prod).strip() == "" or str(nome_prod).upper() in ["ALIMENTO", "HIGIENE", "LIMPEZA"]:
            continue
            
        unidade_str = str(unidade).strip() if not pd.isna(unidade) else "UN"
        marca_principal = str(row.iloc[3]).strip() if not pd.isna(row.iloc[3]) else "Geral"
        nome_clean = str(nome_prod).strip()
        
        cursor.execute(
            "INSERT OR IGNORE INTO produtos (nome, marca, unidade, grupo_equivalencia) VALUES (?, ?, ?, ?)",
            (nome_clean, marca_principal, unidade_str, nome_clean)
        )
        conn.commit()
        
        cursor.execute("SELECT id FROM produtos WHERE nome = ? AND marca = ?", (nome_clean, marca_principal))
        p_res = cursor.fetchone()
        if not p_res:
            continue
        produto_db_id = p_res[0]
        
        for col_idx, atac_nome in atacadistas_map.items():
            if col_idx < len(row):
                preco_val = row.iloc[col_idx]
                if not pd.isna(preco_val) and isinstance(preco_val, (int, float)) and preco_val > 0:
                    cursor.execute("SELECT id FROM fornecedores WHERE nome = ?", (atac_nome,))
                    f_res = cursor.fetchone()
                    if f_res:
                        forn_id = f_res[0]
                        cursor.execute(
                            "INSERT INTO cotacoes (produto_id, fornecedor_id, preco, data_cotacao) VALUES (?, ?, ?, date('now'))",
                            (produto_db_id, forn_id, float(preco_val))
                        )
        conn.commit()
        itens_importados += 1
        
    conn.close()
    print(f"🎉 Importação concluída! Total de {itens_importados} produtos e cotações cadastrados no sistema.")

if __name__ == "__main__":
    importar_dados_excel("CESTA DA FAMILIA bom dia (1).xlsx")
