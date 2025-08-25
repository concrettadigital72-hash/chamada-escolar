# Início do código para database_setup.py

import sqlite3
import logging
import pandas as pd
from pathlib import Path

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- CAMINHOS DOS ARQUIVOS ---
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "escola.db"
ARQUIVO_HORARIOS = DATA_DIR / "Planilha de alunos Digital novo (2).xlsx"
ARQUIVO_CHAMADA_HISTORICO = DATA_DIR / "chamada_diaria.xlsx"

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

def criar_tabelas(cursor):
    """Cria todas as tabelas necessárias no banco de dados."""
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            turma TEXT NOT NULL DEFAULT 'N/A',
            nome_responsavel TEXT,
            telefone_responsavel TEXT
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS observacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            aluno_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            detalhes TEXT,
            acao_tomada TEXT,
            professor TEXT,
            FOREIGN KEY (aluno_id) REFERENCES alunos (id)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chamadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            horario TEXT,
            status TEXT NOT NULL,
            justificativa TEXT,
            professor_responsavel TEXT,
            ligacao_feita BOOLEAN DEFAULT FALSE,
            categoria_justificativa TEXT,
            FOREIGN KEY (aluno_id) REFERENCES alunos (id)
        );
        """)
        logging.info("Tabelas verificadas/criadas com sucesso.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Erro ao criar tabelas: {e}")
        return False

def inserir_alunos_da_planilha(cursor):
    """
    Lê a planilha de horários, extrai todos os nomes de alunos únicos
    e os insere no banco de dados se a tabela estiver vazia.
    """
    try:
        cursor.execute("SELECT COUNT(*) FROM alunos")
        if cursor.fetchone()[0] > 0:
            logging.info("Alunos já existem no banco de dados. Pulando inserção inicial.")
            return True

        if not ARQUIVO_HORARIOS.exists():
            logging.error(f"Arquivo de horários '{ARQUIVO_HORARIOS.name}' não encontrado!")
            return False

        logging.info(f"Lendo alunos da planilha: {ARQUIVO_HORARIOS.name}...")
        xls = pd.ExcelFile(ARQUIVO_HORARIOS)
        todos_os_nomes = set()

        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            for _, row in df.iterrows():
                for item in row:
                    if pd.notna(item):
                        nome = str(item).strip()
                        if len(nome) > 5 and nome.isupper() and "ÀS" not in nome and "MANUTENÇÃO" not in nome:
                            todos_os_nomes.add(nome)

        if not todos_os_nomes:
            logging.warning("Nenhum nome de aluno válido encontrado na planilha.")
            return False

        alunos_para_inserir = [(nome, f"Turma {chr(65 + i % 5)}") for i, nome in enumerate(sorted(list(todos_os_nomes)))]
        cursor.executemany("INSERT OR IGNORE INTO alunos (nome, turma) VALUES (?, ?)", alunos_para_inserir)
        logging.info(f"✅ {len(alunos_para_inserir)} alunos únicos inseridos da planilha!")
        return True
    except Exception as e:
        logging.error(f"Erro crítico ao ler planilha ou inserir alunos: {e}")
        return False

def migrar_historico_chamadas(cursor):
    """
    Lê o arquivo de histórico de chamadas, insere os registros de falta
    e atualiza o telefone dos responsáveis no cadastro dos alunos.
    """
    try:
        cursor.execute("SELECT COUNT(*) FROM chamadas")
        if cursor.fetchone()[0] > 0:
            logging.info("Histórico de chamadas já existe. Pulando migração.")
            return True

        if not ARQUIVO_CHAMADA_HISTORICO.exists():
            logging.warning(f"Arquivo de histórico '{ARQUIVO_CHAMADA_HISTORICO.name}' não encontrado. Pulando migração.")
            return True

        logging.info(f"Migrando histórico de chamadas de '{ARQUIVO_CHAMADA_HISTORICO.name}'...")
        df_chamada = pd.read_excel(ARQUIVO_CHAMADA_HISTORICO, header=5)
        
        # Mapeamento robusto dos nomes das colunas
        colunas_mapeadas = {
            'NOME': 'nome_aluno',
            'DATA': 'data',
            'RELATO': 'justificativa',
            'PROFESSOR': 'professor_responsavel',
            'NÚMERO': 'telefone_responsavel',
            'TELEFONE': 'telefone_responsavel' # Aceita ambos os nomes
        }
        
        # Limpa e renomeia as colunas existentes
        df_chamada.columns = [str(c).strip() for c in df_chamada.columns]
        df_chamada.rename(columns=colunas_mapeadas, inplace=True)
        
        df_chamada.dropna(subset=['nome_aluno', 'data'], inplace=True)
        df_chamada['nome_aluno'] = df_chamada['nome_aluno'].astype(str).str.strip().upper()
        df_chamada['data'] = pd.to_datetime(df_chamada['data'], errors='coerce').dt.strftime('%Y-%m-%d')

        migrados = 0
        atualizados = 0
        for _, row in df_chamada.iterrows():
            cursor.execute("SELECT id FROM alunos WHERE nome = ?", (row['nome_aluno'],))
            aluno_id_result = cursor.fetchone()
            if aluno_id_result:
                aluno_id = aluno_id_result[0]
                
                if 'telefone_responsavel' in row and pd.notna(row['telefone_responsavel']):
                    telefone = str(row['telefone_responsavel']).strip()
                    cursor.execute("UPDATE alunos SET telefone_responsavel = ? WHERE id = ?", (telefone, aluno_id))
                    atualizados += 1

                cursor.execute(
                    """INSERT INTO chamadas (aluno_id, data, status, justificativa, professor_responsavel) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (aluno_id, row['data'], 'Faltou', row.get('justificativa'), row.get('professor_responsavel'))
                )
                migrados += 1
        
        logging.info(f"✅ {migrados} registros de chamadas históricas migrados.")
        logging.info(f"✅ {atualizados} cadastros de alunos atualizados com telefones.")
        return True
    except Exception as e:
        logging.error(f"Erro ao migrar histórico de chamadas: {e}")
        return False

def setup_database():
    """Função principal para configurar o banco de dados: cria tabelas e popula dados."""
    logging.info("Iniciando configuração do banco de dados...")
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        if criar_tabelas(cursor):
            if inserir_alunos_da_planilha(cursor):
                migrar_historico_chamadas(cursor)
        
        conn.commit()
        logging.info("Banco de dados configurado com sucesso!")
        return True
    except sqlite3.Error as e:
        logging.error(f"Erro no setup do banco de dados: {e}")
        conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    setup_database()

# Fim do código para database_setup.py