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
ARQUIVO_BASE_ALUNOS = DATA_DIR / "base_de_alunos.xlsx - Sheet1.csv"
ARQUIVO_CHAMADA_DIARIA_UNICO = DATA_DIR / "chamada_diaria.xlsx"

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
                console.print(f"[warning]Aviso: Coluna 'Nome Aluno' não encontrada em uma linha do arquivo {filename}. Pulando linha.[/warning]")
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
            console.print(f"[error]Erro KeyError ao processar linha: {ke}. Verifique os nomes das colunas em '{filename}'.[/error]")
            conn.rollback()
            break
        except Exception as e:
            console.print(f"[error]Erro ao inserir/atualizar aluno '{row.get('Nome Aluno', 'N/A')}': {e}[/error]")
            conn.rollback()
            break
    
    if conn:
        conn.close()

    console.print(f"[success]✔ {migrados} novos alunos migrados da '{filename}'.[/success]")
    return migrados

def migrar_base_alunos():
    """Lê o arquivo base de alunos (Excel ou CSV) e insere no banco de dados."""
    console.print(f"[info]Migrando dados da '{ARQUIVO_BASE_ALUNOS.name}'...[/info]")
    
    if not ARQUIVO_BASE_ALUNOS.exists():
        console.print(f"[error]Erro Crítico: O arquivo '{ARQUIVO_BASE_ALUNOS.name}' NÃO foi encontrado.[/error]")
        return 0
    
    df = None
    try:
        # Tenta ler como Excel primeiro
        df = pd.read_excel(ARQUIVO_BASE_ALUNOS)
        console.print(f"[info]Arquivo lido com sucesso como Excel.[/info]")
    except Exception:
        console.print(f"[warning]Falha ao ler como Excel. Tentando como CSV...[/warning]")
        # Tenta ler como CSV com diferentes codificações e separadores
        encodings_to_try = ['latin-1', 'utf-8', 'windows-1252']
        delimiters_to_try = [',', ';', '\t']
        for enc in encodings_to_try:
            for sep in delimiters_to_try:
                try:
                    df = pd.read_csv(ARQUIVO_BASE_ALUNOS, encoding=enc, sep=sep, on_bad_lines='skip')
                    if 'Nome Aluno' in df.columns:
                        console.print(f"[info]Arquivo lido com sucesso como CSV (encoding: '{enc}', sep: '{sep}').[/info]")
                        break
                    else:
                        df = None
                except Exception:
                    df = None
            if df is not None:
                break

    if df is None or 'Nome Aluno' not in df.columns:
        console.print(f"[error]Erro Crítico: Não foi possível ler o arquivo '{ARQUIVO_BASE_ALUNOS.name}' ou a coluna 'Nome Aluno' não foi encontrada.[/error]")
        return 0

    return _processar_e_inserir_alunos(df, ARQUIVO_BASE_ALUNOS.name)

def migrar_historico_chamadas():
    """Lê o arquivo Excel de histórico de chamadas e insere no banco de dados."""
    console.print(f"[info]Migrando histórico de chamadas do arquivo: '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}'...[/info]")
    
    if not ARQUIVO_CHAMADA_DIARIA_UNICO.exists():
        console.print(f"[warning]Aviso: Arquivo '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}' NÃO ENCONTRADO. Pulando migração.[/warning]")
        return

    conn = get_db_connection()
    if not conn:
        console.print("[error]Não foi possível obter conexão com o banco de dados.[/error]")
        return

    try:
        cursor = conn.cursor()
        df_chamada = pd.read_excel(ARQUIVO_CHAMADA_DIARIA_UNICO, header=5)
        df_chamada.columns = [str(c).strip() for c in df_chamada.columns]

        df_chamada.rename(columns={
            'NOME': 'nome_aluno', 'TELEFONE': 'telefone_responsavel',
            'PROFESSOR': 'professor_responsavel', 'DATA': 'data', 'RELATO': 'justificativa'
        }, inplace=True)

        required_cols = ['nome_aluno', 'data']
        if not all(col in df_chamada.columns for col in required_cols):
            missing = [col for col in required_cols if col not in df_chamada.columns]
            console.print(f"[error]Colunas essenciais ausentes em '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}': {missing}.[/error]")
            return

        df_chamada['nome_aluno'] = df_chamada['nome_aluno'].astype(str).str.strip().str.upper()
        df_chamada['data'] = pd.to_datetime(df_chamada['data'], errors='coerce').dt.strftime('%Y-%m-%d')
        df_chamada.dropna(subset=['data', 'nome_aluno'], inplace=True)

        migrados_arquivo = 0
        for _, row in df_chamada.iterrows():
            try:
                cursor.execute("SELECT id FROM alunos WHERE nome = ?", (row['nome_aluno'],))
                aluno_id_result = cursor.fetchone()
                if aluno_id_result:
                    aluno_id = aluno_id_result[0]
                    cursor.execute("SELECT id FROM chamadas WHERE aluno_id = ? AND data = ?", (aluno_id, row['data']))
                    chamada_existente = cursor.fetchone()
                    
                    status = 'F'
                    justificativa = str(row.get('justificativa', '')).strip() if pd.notna(row.get('justificativa')) else None
                    professor = str(row.get('professor_responsavel', '')).strip() if pd.notna(row.get('professor_responsavel')) else None

                    if not chamada_existente:
                        cursor.execute("""
                            INSERT INTO chamadas (aluno_id, data, status, justificativa, professor_responsavel) 
                            VALUES (?, ?, ?, ?, ?)
                        """, (aluno_id, row['data'], status, justificativa, professor))
                        migrados_arquivo += 1
                else:
                    console.print(f"[warning]Aluno '{row['nome_aluno']}' não encontrado no DB. Pulando registro.[/warning]")
            except Exception as e_row:
                console.print(f"[error]Erro ao processar linha de chamada: {e_row}[/error]")
        
        conn.commit()
        console.print(f"[success]✔ {migrados_arquivo} registros de chamada migrados de '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}'.[/success]")

    except Exception as e:
        console.print(f"[error]Erro ao ler ou processar '{ARQUIVO_CHAMADA_DIARIA_UNICO.name}': {e}[/error]")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    console.print("[info]Iniciando migração de dados para o banco...[/info]")
    
    if not DB_PATH.parent.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if not criar_banco_dados():
        console.print("[error]Falha crítica: Não foi possível criar a estrutura do banco de dados.[/error]")
        exit(1)
        
    migrar_base_alunos()
    migrar_historico_chamadas()

    console.print("[success]🎉 Migração de dados concluída![/success]")
import sqlite3