# migrate_to_db.py
import pandas as pd
import sqlite3
from pathlib import Path
import logging
from rich.console import Console
from rich.theme import Theme
from typing import Dict, List, Optional
from database_setup import get_db_connection, criar_banco_dados # Importado para garantir a criação do DB

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuração para Rich Console
custom_theme = Theme({"info": "dim cyan", "warning": "magenta", "error": "bold red", "success": "bold green"})
console = Console(theme=custom_theme)

# Definição dos caminhos
ROOT_DIR = Path(__file__).parent.resolve()
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "escola.db"

# --- CAMINHOS DOS ARQUIVOS ---
# Usando os nomes EXATOS dos arquivos que você forneceu.
ARQUIVO_BASE_ALUNOS = DATA_DIR / "base_de_alunos.xlsx - Sheet1.csv"
ARQUIVO_CHAMADA_DIARIA_UNICO = DATA_DIR / "chamada_diaria.xlsx"


# Função para migrar dados da base de alunos
def migrar_base_alunos():
    console.print(f"[info]Migrando dados da '{ARQUIVO_BASE_ALUNOS.name}'...")
    
    if not ARQUIVO_BASE_ALUNOS.exists():
        console.print(f"[error]Erro Crítico: O arquivo '{ARQUIVO_BASE_ALUNOS.name}' NÃO foi encontrado em '{DATA_DIR}'. Por favor, verifique o nome e localização do arquivo.[/error]")
        return 0
    
    conn = None
    df = None
    try:
        # PRIMEIRA TENTATIVA: Tentar ler como Excel, considerando o nome "xlsx" no nome do arquivo
        try:
            df = pd.read_excel(ARQUIVO_BASE_ALUNOS)
            console.print(f"[info]Arquivo '{ARQUIVO_BASE_ALUNOS.name}' lido com sucesso como um arquivo Excel.[/info]")
            # Se a leitura Excel foi bem-sucedida e contém a coluna essencial, podemos parar por aqui.
            if 'Nome Aluno' in df.columns:
                return _processar_e_inserir_alunos(df, ARQUIVO_BASE_ALUNOS.name) # Chamar função auxiliar para inserir
            else:
                console.print(f"[warning]Arquivo '{ARQUIVO_BASE_ALUNOS.name}' lido como Excel, mas a coluna 'Nome Aluno' não foi encontrada. Tentando como CSV...[/warning]")
                df = None # Reset df para tentar como CSV
        except Exception as e_excel:
            console.print(f"[warning]Falha ao ler '{ARQUIVO_BASE_ALUNOS.name}' como Excel ({e_excel}). Tentando como CSV...[/warning]")
            df = None # Reset df para tentar como CSV

        # SEGUNDA TENTATIVA: Se falhou como Excel ou não encontrou a coluna, tentar como CSV
        if df is None: # Só tenta como CSV se df ainda for None (falha na leitura Excel ou coluna não encontrada)
            encodings_to_try = ['latin-1', 'utf-8', 'windows-1252']
            delimiters_to_try = [',', ';', '\t']
            
            for enc in encodings_to_try:
                for sep in delimiters_to_try:
                    try:
                        df = pd.read_csv(ARQUIVO_BASE_ALUNOS, encoding=enc, sep=sep, on_bad_lines='skip')
                        if 'Nome Aluno' in df.columns:
                            console.print(f"[info]Arquivo '{ARQUIVO_BASE_ALUNOS.name}' lido com sucesso como CSV usando codificação '{enc}' e separador '{sep}'.[/info]")
                            return _processar_e_inserir_alunos(df, ARQUIVO_BASE_ALUNOS.name) # Chamar função auxiliar
                        else:
                            df = None
                    except Exception as e_csv:
                        df = None
                if df is not None and 'Nome Aluno' in df.columns:
                    break # Sai dos loops de tentativa se for bem-sucedido

            if df is None:
                console.print(f"[error]Erro Crítico: Não foi possível ler o arquivo '{ARQUIVO_BASE_ALUNOS.name}' de nenhuma forma esperada ou a coluna 'Nome Aluno' não foi encontrada. Verifique o arquivo manualmente.[/error]")
                return 0

    except Exception as e:
        console.print(f"[error]Erro geral ao ler ou processar '{ARQUIVO_BASE_ALUNOS.name}': {e}[/error]")
        return 0
    finally:
        if conn:
            conn.close()

def _processar_e_inserir_alunos(df: pd.DataFrame, filename: str) -> int:
    """Função auxiliar para processar o DataFrame e inserir alunos no DB."""
    df.columns = [str(c).strip() for c in df.columns] # Limpa espaços em branco dos nomes das colunas
    
    conn = get_db_connection()
    if not conn:
        console.print("[error]Não foi possível obter conexão com o banco de dados para migrar alunos.[/error]")
        return 0
    
    cursor = conn.cursor()
    migrados = 0
    
    for _, row in df.iterrows():
        try:
            if 'Nome Aluno' not in row:
                console.print(f"[warning]Aviso: Coluna 'Nome Aluno' não encontrada em uma linha do arquivo {filename}. Pulando linha. Verifique o cabeçalho e o conteúdo do arquivo.[/warning]")
                continue

            nome_aluno_original = str(row['Nome Aluno']).strip()
            nome_aluno_upper = nome_aluno_original.upper()
            nome_responsavel = str(row.get('Nome Responsavel', '')).strip() if pd.notna(row.get('Nome Responsavel')) else None
            telefone_responsavel = str(row.get('Telefone Responsavel', '')).strip() if pd.notna(row.get('Telefone Responsavel')) else None
            
            cursor.execute("SELECT id FROM alunos WHERE nome = ?", (nome_aluno_upper,))
            aluno_existente = cursor.fetchone()

            if aluno_existente:
                cursor.execute("""
                    UPDATE alunos 
                    SET nome_responsavel = ?, telefone_responsavel = ?
                    WHERE id = ?
                """, (nome_responsavel, telefone_responsavel, aluno_existente[0]))
            else:
                cursor.execute("""
                    INSERT INTO alunos (nome, nome_responsavel, telefone_responsavel) 
                    VALUES (?, ?, ?)
                """, (nome_aluno_upper, nome_responsavel, telefone_responsavel))
                migrados += 1
            
            conn.commit()
        except KeyError as ke:
            console.print(f"[error]Erro KeyError ao processar linha do arquivo de alunos: {ke}. Verifique os nomes das colunas no seu arquivo '{filename}'.[/error]")
            conn.rollback()
            break
        except Exception as e:
            console.print(f"[error]Erro ao inserir/atualizar aluno '{row.get('Nome Aluno', 'N/A')}': {e}[/error]")
            conn.rollback()
            break

    console.print(f"[success]✔ {migrados} novos alunos migrados da '{filename}'.[/success]")
    return migrados


# Função para migrar histórico de chamadas (agora lendo o único arquivo Excel)
def migrar_historico_chamadas():
    console.print(f"[info]Migrando histórico de chamadas do arquivo: '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}'...[/info]")
    total_migrated_calls = 0

    if not ARQUIVO_CHAMADA_DIARIA_UNICO.exists():
        console.print(f"[warning]Aviso: Arquivo de chamada '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}' NÃO ENCONTRADO. Por favor, verifique o nome e localização do arquivo. Pulando migração de chamadas.[/warning]")
        return
    
    conn = get_db_connection()
    if not conn:
        console.print("[error]Não foi possível obter conexão com o banco de dados para migrar chamadas.[/error]")
        return

    cursor = conn.cursor()

    try:
        # Lendo o arquivo Excel. A metadata de arquivos anteriores (estimatedRowsAboveHeader:5)
        # sugere que o cabeçalho real pode estar na linha 5 (índice 5).
        # Vamos usar `header=5` para que o pandas leia essa linha como cabeçalho.
        df_chamada = pd.read_excel(ARQUIVO_CHAMADA_DIARIA_UNICO, header=5)
        console.print(f"[info]Arquivo '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}' lido com sucesso como um arquivo Excel.[/info]")

        # Limpar espaços em branco dos nomes das colunas lidas do Excel
        df_chamada.columns = [str(c).strip() for c in df_chamada.columns]

        # Renomear colunas para corresponder ao esquema do banco de dados e padronizar
        # AGORA USANDO O NOME EXATO 'PROFESSOR' QUE VOCÊ FORNECEU
        df_chamada.rename(columns={
            'NOME': 'nome_aluno',
            'TELEFONE': 'telefone_responsavel', # Mapeia TELEFONE para telefone_responsavel
            'PROFESSOR': 'professor_responsavel', # <--- CORRIGIDO PARA 'PROFESSOR'
            'DATA': 'data',
            'RELATO': 'justificativa'
        }, inplace=True)

        if 'nome_aluno' in df_chamada.columns:
            df_chamada['nome_aluno'] = df_chamada['nome_aluno'].astype(str).str.strip().str.upper()
        
        if 'data' in df_chamada.columns:
            df_chamada['data'] = pd.to_datetime(df_chamada['data'], errors='coerce').dt.strftime('%Y-%m-%d')
            df_chamada.dropna(subset=['data'], inplace=True)
        
        required_cols = ['nome_aluno', 'data', 'justificativa']
        # Verifica se todas as colunas REQUERIDAS estão presentes
        if not all(col in df_chamada.columns for col in required_cols):
            missing_cols = [col for col in required_cols if col not in df_chamada.columns]
            console.print(f"[error]Colunas essenciais ausentes em '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}': {missing_cols}. Requer: {required_cols}[/error]")
            if 'nome_aluno' not in df_chamada.columns: # Erro crítico se nome_aluno não está presente
                console.print("[error]Migração de chamadas interrompida: Coluna 'NOME' (nome_aluno) não encontrada no arquivo. Verifique o cabeçalho.[/error]")
                return
            # Se 'professor_responsavel' ou 'justificativa' estiverem faltando, mas 'nome_aluno' e 'data' estão OK, continuar mas avisar.
            if 'professor_responsavel' not in df_chamada.columns:
                console.print("[warning]Aviso: Coluna 'professor_responsavel' não encontrada após renomeação. Será tratada como vazia.[/warning]")
                df_chamada['professor_responsavel'] = None # Garante que a coluna existe para o insert
            if 'justificativa' not in df_chamada.columns:
                console.print("[warning]Aviso: Coluna 'justificativa' não encontrada após renomeação. Será tratada como vazia.[/warning]")
                df_chamada['justificativa'] = None # Garante que a coluna existe para o insert
        
        migrados_arquivo = 0
        for _, row in df_chamada.iterrows():
            try:
                aluno_nome = row['nome_aluno']
                data_chamada = row['data']
                status_chamada = 'F' # Assumindo que todos os registros aqui são de faltas
                # Acessa as colunas de forma segura, pois já garantimos que existem ou foram criadas com None
                justificativa = str(row.get('justificativa')).strip() if pd.notna(row.get('justificativa')) else None
                professor_responsavel = str(row.get('professor_responsavel')).strip() if pd.notna(row.get('professor_responsavel')) else None

                if not aluno_nome or not data_chamada:
                    console.print(f"[warning]Linha ignorada: 'nome_aluno' ou 'data' ausente para registro de chamada. Verifique o arquivo '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}'.[/warning]")
                    continue

                cursor.execute("SELECT id FROM alunos WHERE nome = ?", (aluno_nome,))
                aluno_id = cursor.fetchone()

                if aluno_id:
                    aluno_id = aluno_id[0]
                    cursor.execute("SELECT id FROM chamadas WHERE aluno_id = ? AND data = ?", (aluno_id, data_chamada))
                    chamada_existente = cursor.fetchone()

                    if chamada_existente:
                        cursor.execute("""
                            UPDATE chamadas 
                            SET status = ?, justificativa = ?, professor_responsavel = ?
                            WHERE id = ?
                        """, (status_chamada, justificativa, professor_responsavel, chamada_existente[0]))
                    else:
                        cursor.execute("""
                            INSERT INTO chamadas (aluno_id, data, status, justificativa, professor_responsavel) 
                            VALUES (?, ?, ?, ?, ?)
                        """, (aluno_id, data_chamada, status_chamada, justificativa, professor_responsavel))
                        migrados_arquivo += 1
                    
                    conn.commit()
                else:
                    console.print(f"[warning]Aluno '{aluno_nome}' não encontrado no banco de dados. Pulando registro de chamada para {data_chamada}.[/warning]")
                    
            except Exception as e:
                console.print(f"[error]Erro ao processar linha de chamada do arquivo {ARQUIVO_CHAMADA_DIARIA_UNICO.name}: {e}[/error]")
                conn.rollback() # Reverte operações se houver erro
                break # Pára de processar este arquivo em caso de erro grave

        total_migrated_calls += migrados_arquivo
        console.print(f"[success]✔ {migrados_arquivo} registros de chamada migrados de '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}'.[/success]")

    except Exception as e:
        console.print(f"[error]Erro ao ler ou processar '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}': {e}[/error]")
            
    finally:
        if conn:
            conn.close()

    console.print(f"[success]🎉 Migração de histórico de chamadas concluída. Total de {total_migrated_calls} registros migrados.[/success]")


# --- Execução Principal do Script ---
if __name__ == "__main__":
    console.print("[info]Iniciando migração de dados para o banco...[/info]")
    
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    db_exists = DB_PATH.exists() and DB_PATH.stat().st_size > 0
    alunos_in_db = False
    if db_exists:
        try:
            conn_check = get_db_connection()
            if conn_check:
                with conn_check:
                    alunos_in_db = pd.read_sql("SELECT COUNT(*) FROM alunos", conn_check).iloc[0,0] > 0
        except Exception as e:
            console.print(f"[error]Erro ao verificar alunos no banco de dados existente: {e}[/error]")
            alunos_in_db = False

    if not db_exists or not alunos_in_db:
        console.print("[info]Banco de dados inexistente, vazio ou sem alunos, criando estrutura e inserindo dados iniciais...[/info]")
        if not criar_banco_dados():
            console.print("[error]Falha crítica: Não foi possível criar a estrutura do banco de dados.[/error]")
            exit(1)
        
    base_alunos_migrated_count = migrar_base_alunos()

    should_migrate_calls = (base_alunos_migrated_count > 0 or alunos_in_db) and ARQUIVO_CHAMADA_DIARIA_UNICO.exists()

    if should_migrate_calls:
        migrar_historico_chamadas()
    else:
        console.print("[warning]Pulando migração de histórico de chamadas pois a base de alunos não foi encontrada/migrada ou está vazia, OU o arquivo único de chamadas não foi encontrado.[/warning]")

    console.print("[success]🎉 Migração de dados concluída![/success]")