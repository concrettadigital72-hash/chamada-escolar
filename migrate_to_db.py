# Em migrate_to_db.py

import pandas as pd
from pathlib import Path
import sqlite3
import logging
from datetime import datetime

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Caminhos ---
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "escola.db"
HISTORICO_PATH = DATA_DIR / "chamada_diaria.xlsx"

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Erro de conexão com o banco de dados: {e}")
        return None

def limpar_dados(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa e pré-processa o DataFrame lido do Excel."""
    # Renomeia colunas para um formato padrão, ignorando maiúsculas/minúsculas e acentos
    df = df.rename(columns=lambda c: str(c).strip().upper())
    
    # Mapeamento de possíveis nomes de colunas para os nomes padrão
    col_map = {
        'NOME': ['NOME', 'ALUNO', 'ALUNOS'],
        'DATA': ['DATA', 'DIA'],
        'RELATO': ['RELATO', 'JUSTIFICATIVA', 'MOTIVO', 'OBSERVAÇÃO'],
        'PROFESSOR': ['PROFESSOR', 'PROFESSOR RESPONSAVEL']
    }
    
    # Renomeia as colunas encontradas para o padrão
    for standard_name, possible_names in col_map.items():
        for col_name in df.columns:
            if col_name in possible_names:
                df = df.rename(columns={col_name: standard_name})
                break

    # Verifica se as colunas essenciais existem
    required_cols = {'NOME', 'DATA', 'RELATO'}
    if not required_cols.issubset(df.columns):
        logging.warning(f"Colunas necessárias {required_cols} não encontradas. Colunas disponíveis: {list(df.columns)}")
        return pd.DataFrame() # Retorna DataFrame vazio se não encontrar

    # Limpeza dos dados
    df.dropna(subset=['NOME', 'DATA'], inplace=True)
    df = df[df['NOME'].str.strip() != '']
    
    # Converte a data para o formato correto (YYYY-MM-DD)
    df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce').dt.strftime('%Y-%m-%d')
    df.dropna(subset=['DATA'], inplace=True)

    # Preenche valores vazios em 'RELATO'
    df['RELATO'] = df['RELATO'].fillna('Não especificado')
    df['PROFESSOR'] = df.get('PROFESSOR', pd.Series(index=df.index)).fillna('Não especificado')

    return df

def migrar_historico_chamadas():
    """Lê o arquivo Excel histórico e insere os dados no banco de dados."""
    if not HISTORICO_PATH.exists():
        logging.error(f"Arquivo histórico '{HISTORICO_PATH.name}' não encontrado.")
        return

    conn = get_db_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        
        # Carrega todos os alunos do banco para mapear nomes para IDs
        cursor.execute("SELECT id, nome FROM alunos")
        alunos_db = {row['nome'].strip().upper(): row['id'] for row in cursor.fetchall()}
        
        xls = pd.ExcelFile(HISTORICO_PATH)
        total_registros_inseridos = 0

        for sheet_name in xls.sheet_names:
            logging.info(f"Processando a aba: '{sheet_name}'...")
            try:
                # Tenta encontrar a linha do cabeçalho procurando por 'NOME'
                df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None)
                header_row = -1
                for i, row in df_raw.iterrows():
                    if any('NOME' in str(cell).upper() for cell in row):
                        header_row = i
                        break
                
                if header_row == -1:
                    logging.warning(f"Cabeçalho com a coluna 'NOME' não encontrado na aba '{sheet_name}'. Pulando.")
                    continue

                df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row)
                df_limpo = limpar_dados(df)

                if df_limpo.empty:
                    logging.warning(f"Nenhum dado válido encontrado na aba '{sheet_name}' após a limpeza.")
                    continue

                registros_para_inserir = []
                for _, row in df_limpo.iterrows():
                    nome_aluno = str(row['NOME']).strip().upper()
                    aluno_id = alunos_db.get(nome_aluno)
                    
                    if aluno_id:
                        registros_para_inserir.append((
                            aluno_id,
                            row['DATA'],
                            'Faltou',  # Assume que todos os registros históricos são faltas
                            row['RELATO'],
                            row.get('PROFESSOR', 'N/A')
                        ))
                    else:
                        logging.warning(f"Aluno '{row['NOME']}' da planilha não encontrado na base de dados. Pulando registro.")

                if registros_para_inserir:
                    cursor.executemany("""
                        INSERT OR IGNORE INTO chamadas (aluno_id, data, status, justificativa, professor_responsavel)
                        VALUES (?, ?, ?, ?, ?)
                    """, registros_para_inserir)
                    conn.commit()
                    total_registros_inseridos += len(registros_para_inserir)
                    logging.info(f"{len(registros_para_inserir)} registros da aba '{sheet_name}' inseridos/ignorados.")

            except Exception as e:
                logging.error(f"Erro ao processar a aba '{sheet_name}': {e}")
        
        logging.info(f"Migração concluída! Total de {total_registros_inseridos} registros inseridos.")
        print(f"Migração concluída! Total de {total_registros_inseridos} registros inseridos.")

    except Exception as e:
        logging.error(f"Erro durante a migração dos dados: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrar_historico_chamadas()