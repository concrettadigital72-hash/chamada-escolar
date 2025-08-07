# database_setup.py
import sqlite3
from pathlib import Path
import logging
from datetime import date
from typing import Optional

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# DB_PATH global aqui para ser acessível pelas funções
DB_PATH = Path(__file__).parent / "data" / "escola.db"


def get_db_connection() -> Optional[sqlite3.Connection]:
    """Estabelece conexão com o banco de dados SQLite."""
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn
    except sqlite3.Error as e:
        logging.error(f"Erro de conexão com o banco: {e}")
        return None


def criar_banco_dados():
    """Cria a estrutura do banco de dados SQLite com todas as tabelas necessárias"""
    # Garante que a pasta 'data' existe
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = get_db_connection()
    if not conn:
        logging.error("Não foi possível obter conexão com o banco de dados para criar tabelas.")
        return False

    cursor = None
    try:
        cursor = conn.cursor()
        
        # Tabela de alunos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE COLLATE NOCASE,
            nome_responsavel TEXT,
            telefone_responsavel TEXT
        );
        """)
        
        # Tabela de chamadas
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chamadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            horario TEXT,
            status TEXT NOT NULL,
            justificativa TEXT,
            ligacao_feita BOOLEAN DEFAULT FALSE,
            professor_responsavel TEXT,
            categoria_justificativa TEXT,
            FOREIGN KEY (aluno_id) REFERENCES alunos (id)
        );
        """)
        
        # Tabela de lembretes
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS lembretes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            data_criacao TEXT NOT NULL,
            lembrete TEXT NOT NULL,
            professor_responsavel TEXT,
            concluido BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (aluno_id) REFERENCES alunos (id)
        );
        """)
        
        # Tabela de comportamentos
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS comportamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            observacao TEXT NOT NULL,
            tipo TEXT NOT NULL,
            professor_responsavel TEXT,
            FOREIGN KEY (aluno_id) REFERENCES alunos (id)
        );
        """)
        
        # Criar índices para melhor performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chamadas_aluno_id ON chamadas(aluno_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chamadas_data ON chamadas(data);")
        
        conn.commit()
        logging.info("✅ Banco de dados criado com sucesso!")
        return True
    except Exception as e:
        logging.error(f"❌ Erro ao criar banco de dados: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        
def inserir_dados_iniciais():
    """Insere dados de teste na tabela alunos e chamadas se estiverem vazias."""
    conn = get_db_connection()
    if not conn:
        logging.error("Não foi possível obter conexão com o banco de dados para inserir dados iniciais.")
        return
        
    try:
        cursor = conn.cursor()
        
        # Inserir alunos de exemplo se a tabela estiver vazia
        cursor.execute("SELECT COUNT(*) FROM alunos")
        if cursor.fetchone()[0] == 0:
            alunos = [
                ('ALESSANDRO SILVA DE CASTRO', 'Responsável 1', '+5511999999999'),
                ('ANA CAROLINA FERREIRA DA PAZ', 'Responsável 2', '+5511888888888'),
                ('DANIELLY PEREIRA DA SILVA', 'Responsável 3', '+5511777777777')
            ]
            cursor.executemany("INSERT OR IGNORE INTO alunos (nome, nome_responsavel, telefone_responsavel) VALUES (?, ?, ?)", alunos)
            conn.commit()
            logging.info("✅ Alunos iniciais inseridos com sucesso!")
        else:
            logging.info("Alunos já existem, pulando inserção de dados iniciais de alunos.")
            
        # Inserir registros de chamada de exemplo se a tabela estiver vazia (para os alunos de exemplo)
        cursor.execute("SELECT COUNT(*) FROM chamadas WHERE aluno_id IN (1, 2, 3)")
        if cursor.fetchone()[0] == 0:
            hoje = date.today().isoformat()
            cursor.execute("INSERT INTO chamadas (aluno_id, data, status, professor_responsavel) VALUES (1, ?, 'P', 'Professor Teste')", (hoje,))
            cursor.execute("INSERT INTO chamadas (aluno_id, data, status, professor_responsavel) VALUES (2, ?, 'F', 'Professor Teste')", (hoje,))
            conn.commit()
            logging.info("✅ Registros de chamada iniciais inseridos com sucesso!")
        else:
            logging.info("Registros de chamada iniciais já existem, pulando inserção.")

    except Exception as e:
        logging.error(f"❌ Erro ao inserir dados iniciais: {e}")
    finally:
        if conn:
            conn.close()

def setup_database():
    """Orquestra a criação do banco de dados e a inserção de dados iniciais."""
    logging.info("Iniciando configuração do banco de dados...")
    if criar_banco_dados():
        logging.info("Banco de dados configurado com sucesso!")
        inserir_dados_iniciais()
    else:
        logging.error("Ocorreu um erro ao configurar o banco de dados.")

if __name__ == "__main__":
    setup_database()