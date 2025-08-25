import pandas as pd
from pathlib import Path

# --- CONFIGURAÇÃO ---
# Garanta que estes caminhos e nomes de arquivos estão EXATAMENTE iguais aos seus
ROOT_DIR = Path(__file__).parent.resolve()
DATA_DIR = ROOT_DIR / "data"
ARQUIVO_HORARIOS = DATA_DIR / "Planilha de alunos Digital novo (2).xlsx"
ARQUIVO_CHAMADA_HISTORICO = DATA_DIR / "chamada_diaria.xlsx"

def diagnosticar_planilhas():
    """
    Executa uma série de testes nos arquivos Excel para encontrar o ponto de falha.
    """
    print("--- INICIANDO DIAGNÓSTICO DAS PLANILHAS ---")

    # --- Teste 1: Planilha de Horários (Alunos) ---
    print(f"\n[TESTE 1] Lendo a planilha de alunos: '{ARQUIVO_HORARIOS.name}'")
    if not ARQUIVO_HORARIOS.exists():
        print(f"  [ERRO GRAVE] O arquivo NÃO FOI ENCONTRADO no caminho: {ARQUIVO_HORARIOS}")
        return
    else:
        print(f"  [OK] Arquivo encontrado.")

    try:
        xls_horarios = pd.ExcelFile(ARQUIVO_HORARIOS)
        print(f"  [OK] Arquivo Excel aberto com sucesso.")
        print(f"  [INFO] Abas encontradas: {xls_horarios.sheet_names}")

        todos_os_nomes = set()
        for sheet_name in xls_horarios.sheet_names:
            print(f"\n  Lendo aba: '{sheet_name}'...")
            df = pd.read_excel(xls_horarios, sheet_name=sheet_name, header=None)
            
            nomes_na_aba = set()
            for _, row in df.iterrows():
                for item in row:
                    if pd.notna(item):
                        nome = str(item).strip()
                        if len(nome) > 5 and nome.isupper() and "ÀS" not in nome and "MANUTENÇÃO" not in nome:
                            nomes_na_aba.add(nome)
            
            if nomes_na_aba:
                print(f"    [OK] {len(nomes_na_aba)} nomes de alunos encontrados nesta aba.")
                todos_os_nomes.update(nomes_na_aba)
            else:
                print(f"    [AVISO] Nenhum nome de aluno encontrado nesta aba.")

        print(f"\n  [RESULTADO TESTE 1] Total de {len(todos_os_nomes)} alunos únicos encontrados na planilha de horários.")
        if len(todos_os_nomes) < 10:
             print("  [AVISO] Poucos alunos encontrados. A lógica de extração pode estar falhando.")
        print("-" * 20)

    except Exception as e:
        print(f"  [ERRO GRAVE] Falha ao processar a planilha de horários. Erro: {e}")
        print("-" * 20)


    # --- Teste 2: Planilha de Histórico de Chamadas ---
    print(f"\n[TESTE 2] Lendo a planilha de histórico: '{ARQUIVO_CHAMADA_HISTORICO.name}'")
    if not ARQUIVO_CHAMADA_HISTORICO.exists():
        print(f"  [ERRO GRAVE] O arquivo NÃO FOI ENCONTRADO no caminho: {ARQUIVO_CHAMADA_HISTORICO}")
        return
    else:
        print(f"  [OK] Arquivo encontrado.")

    try:
        # header=5 para pular as primeiras 5 linhas
        df_chamada = pd.read_excel(ARQUIVO_CHAMADA_HISTORICO, header=5)
        print("  [OK] Arquivo de histórico lido com sucesso.")
        print(f"  [INFO] Colunas encontradas: {list(df_chamada.columns)}")
        print(f"  [INFO] Total de {len(df_chamada)} registros de falta encontrados antes da limpeza.")
        print("-" * 20)

    except Exception as e:
        print(f"  [ERRO GRAVE] Falha ao processar a planilha de histórico. Erro: {e}")
        print("-" * 20)

    print("\n--- DIAGNÓSTICO CONCLUÍDO ---")


if __name__ == "__main__":
    diagnosticar_planilhas()
