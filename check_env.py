import os
import sys

def check_project():
    print("🔍 Executando verificação de integridade do projeto...")
    required_files = [
        "app.py",
        "core/database.py",
        "Cestas_Bom_Dia_Template_Upload.xlsx"
    ]
    
    missing = []
    for f in required_files:
        if not os.path.exists(f):
            missing.append(f)
        else:
            print(f"  [OK] Encontrado: {f}")
            
    if missing:
        print(f"\n❌ ERRO: Faltam os seguintes arquivos obrigatórios: {missing}")
        sys.exit(1)
    else:
        print("\n✨ Todos os arquivos essenciais estão presentes e prontos para o deploy!")

if __name__ == "__main__":
    check_project()
