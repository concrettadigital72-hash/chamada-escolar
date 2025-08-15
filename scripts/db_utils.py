from typing import List, Tuple, Optional, Dict, Any, Union
import sqlite3
<<<<<<< HEAD
import streamlit as st
=======
>>>>>>> c19bda253a042a39f0d8d16acd0dc96f2b1dabae
import pandas as pd
from pathlib import Path
from datetime import date, datetime
import streamlit as st # Necessário se st.error for usado aqui
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Caminhos globais
ROOT = Path(__file__).resolve().parents[1] # Volta dois níveis para a raiz do projeto (attendance-bot)
DB_PATH = ROOT / "data" / "escola.db"
# Caminho para o arquivo Excel de horários (assumindo o nome que você tem na pasta data)
ARQUIVO_HORARIOS = ROOT / "data" / "Planilha de alunos Digital novo (2).xlsx" # <-- VERIFIQUE ESTE NOME EXATO
EXPORT_DIR = ROOT / "export"
EXPORT_DIR.mkdir(exist_ok=True)


# classificar_justificativa agora precisa de categorias_config vindo do main.py
def classificar_justificativa(texto: str, categorias_config: Dict[str, List[str]]) -> str:
    """Classifica uma justificativa de falta em categorias pré-definidas."""
    if pd.isna(texto) or not isinstance(texto, str):
        return "Não Especificado"
    
    texto_lower = str(texto).lower()
    # Verifica se categorias_config não está vazio e é um dicionário
    if categorias_config and isinstance(categorias_config, dict):
        for categoria, palavras in categorias_config.items():
            if isinstance(palavras, list) and any(palavra.lower() in texto_lower for palavra in palavras):
                return categoria.replace("motivo_", "").replace("_", " ").title()
    return "Outros"

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

# setup_database, criar_banco_dados, verificar_e_inserir_dados_teste
# Essas funções foram movidas para database_setup.py e são importadas de lá em main.py


<<<<<<< HEAD
@st.cache_data
def carregar_alunos_db():
    """Carrega todos os alunos do banco de dados."""
    conn = get_db_connection()
    if not conn:
        st.error("Erro de conexão com o banco de dados.")
        return pd.DataFrame()
=======
@st.cache_data(ttl=600)
def carregar_alunos_db() -> Tuple[pd.DataFrame, str]:
    """Carrega todos os alunos do banco de dados."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame(), "Erro de conexão com o banco de dados."
>>>>>>> c19bda253a042a39f0d8d16acd0dc96f2b1dabae
    try:
        query = """
        SELECT id, nome, nome_responsavel, telefone_responsavel
        FROM alunos
        ORDER BY nome COLLATE NOCASE
        """
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            return df, "Nenhum aluno cadastrado no banco de dados."
            
        df['nome_norm'] = df['nome'].str.strip().str.upper()
        return df, f"Base de dados carregada com {len(df)} alunos."
    except Exception as e:
        logging.error(f"Erro ao carregar alunos: {e}")
        return pd.DataFrame(), f"Erro ao carregar dados dos alunos: {e}"
    finally:
        if conn:
            conn.close()

<<<<<<< HEAD
@st.cache_resource
def carregar_horarios():
=======
@st.cache_resource(ttl=3600)
def carregar_horarios() -> Optional[pd.ExcelFile]:
>>>>>>> c19bda253a042a39f0d8d16acd0dc96f2b1dabae
    """Carrega o arquivo Excel com horários das turmas."""
    if not ARQUIVO_HORARIOS.exists():
        st.error(f"Arquivo '{ARQUIVO_HORARIOS.name}' não encontrado em {ARQUIVO_HORARIOS}.")
        logging.error(f"Arquivo de horários não encontrado: {ARQUIVO_HORARIOS}")
        return None
        
    try:
        xls = pd.ExcelFile(ARQUIVO_HORARIOS)
        dias_semana = ['SEGUNDA', 'TERÇA', 'QUARTA', 'QUINTA', 'SEXTA', 'SÁBADO']
        abas_validas = [aba for aba in xls.sheet_names if aba.upper() in dias_semana]
        if not abas_validas:
            st.error("Nenhuma aba válida (SEGUNDA, TERÇA, etc.) encontrada no arquivo de horários.")
            logging.error("Nenhuma aba válida encontrada no arquivo de horários.")
            return None
        return xls
    except Exception as e:
        st.error(f"Erro ao ler arquivo de horários: {e}")
        logging.error(f"Erro ao ler arquivo de horários: {e}")
        return None

def salvar_justificativa_db(
    aluno_id: int,
    data_falta: date,
    justificativa: str,
    professor: str,
    ligacao_feita: bool,
    categorias_config: Optional[Dict[str, List[str]]] = None
) -> Tuple[bool, Optional[str]]:
    """Salva ou atualiza uma justificativa de falta."""
    conn = get_db_connection()
    if not conn:
        return False, "Erro de conexão com o banco de dados."
        
    try:
        cursor = conn.cursor()
        data_falta_str = data_falta.strftime('%Y-%m-%d')
        
        categoria = classificar_justificativa(justificativa, categorias_config) if categorias_config else None
        
        cursor.execute("""
        SELECT id FROM chamadas
        WHERE aluno_id = ? AND data = ? AND status = 'Faltou'
        """, (aluno_id, data_falta_str))
        
        registo = cursor.fetchone()
        
        if registo:
            cursor.execute("""
            UPDATE chamadas
            SET justificativa = ?,
                professor_responsavel = ?,
                ligacao_feita = ?,
                categoria_justificativa = ?
            WHERE id = ?
            """, (justificativa, professor, ligacao_feita, categoria, registo['id']))
        else:
            cursor.execute("""
            INSERT INTO chamadas (
                aluno_id, data, status, justificativa,
                professor_responsavel, ligacao_feita, categoria_justificativa
            )
            VALUES (?, ?, 'Faltou', ?, ?, ?, ?)
            """, (aluno_id, data_falta_str, justificativa, professor, ligacao_feita, categoria))
        
        conn.commit()
        logging.info(f"Justificativa para aluno_id {aluno_id} na data {data_falta_str} salva/atualizada.")
        return True, None
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Erro ao salvar justificativa: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()

def salvar_chamada_db(
    aluno_id: int,
    data_chamada: date,
    horario: str,
    status: str,
    professor: str
) -> bool:
    """Salva um registro de chamada no banco de dados, ou atualiza se já existir para o mesmo aluno, data e horário."""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        data_str = data_chamada.strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT id FROM chamadas
            WHERE aluno_id = ? AND data = ? AND horario = ?
        """, (aluno_id, data_str, horario))
        
        existing_id = cursor.fetchone()
        
        if existing_id:
            cursor.execute("""
                UPDATE chamadas
                SET status = ?, professor_responsavel = ?
                WHERE id = ?
            """, (status, professor, existing_id['id']))
            logging.info(f"Chamada para aluno_id {aluno_id} em {data_str} ({horario}) atualizada para {status}.")
        else:
            cursor.execute("""
            INSERT INTO chamadas (
                aluno_id, data, horario, status, professor_responsavel
            )
            VALUES (?, ?, ?, ?, ?)
            """, (aluno_id, data_str, horario, status, professor))
            logging.info(f"Chamada para aluno_id {aluno_id} em {data_str} ({horario}) inserida como {status}.")
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Erro ao salvar chamada: {e}")
        return False
    finally:
        if conn:
            conn.close()

def carregar_todas_faltas() -> pd.DataFrame:
    """Carrega todas as chamadas registradas com informações dos alunos."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
        
    try:
        query = """
        SELECT
            c.id,
            c.horario,
            c.data,
            c.status,
            c.justificativa,
            c.ligacao_feita,
            c.professor_responsavel,
            c.categoria_justificativa,
            a.id as aluno_id,
            a.nome as nome_aluno, -- Nome do aluno vindo da tabela 'alunos'
            a.nome_responsavel,
            a.telefone_responsavel
        FROM chamadas c
        JOIN alunos a ON c.aluno_id = a.id
        ORDER BY c.data DESC
        """
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            df['data'] = pd.to_datetime(df['data'])
            df['ligacao_feita'] = df['ligacao_feita'].apply(lambda x: bool(x) if x is not None else False)
            
        return df
    except Exception as e:
        logging.error(f"Erro ao carregar todas as faltas: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def carregar_faltas_por_periodo(
    data_inicio: date,
    data_fim: date,
    categorias: Optional[List[str]] = None
) -> pd.DataFrame:
    """Carrega faltas em um período específico."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
        
    try:
        query = """
        SELECT
            c.*,
            a.nome as nome_aluno
        FROM chamadas c
        JOIN alunos a ON c.aluno_id = a.id
        WHERE c.data BETWEEN ? AND ?
        AND c.status = 'Faltou'
        """
        params = [data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d')]
        
        if categorias:
            categorias_db_format = [cat.title() for cat in categorias]
            placeholders = ', '.join(['?'] * len(categorias_db_format))
            query += f" AND c.categoria_justificativa IN ({placeholders})"
            params.extend(categorias_db_format)
            
        query += " ORDER BY c.data DESC"
        
        df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            df['data'] = pd.to_datetime(df['data'])
            df['ligacao_feita'] = df['ligacao_feita'].astype(bool)
            
        return df
    except Exception as e:
        logging.error(f"Erro ao carregar faltas por período: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

def salvar_alunos_sponte_db(lista_nomes_sponte: List[str]) -> int:
    """Salva alunos do Sponte que não existem na base local."""
    conn = get_db_connection()
    if not conn:
        return 0
        
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT nome FROM alunos")
        alunos_existentes = {row['nome'].upper().strip() for row in cursor.fetchall()}
        
        alunos_novos = [
            (nome,) for nome in lista_nomes_sponte 
            if nome.upper().strip() not in alunos_existentes
        ]
        
        if alunos_novos:
            cursor.executemany(
                "INSERT OR IGNORE INTO alunos (nome) VALUES (?)",
                alunos_novos
            )
            conn.commit()
            logging.info(f"{len(alunos_novos)} novos alunos do Sponte inseridos.")
            
        return len(alunos_novos)
    except Exception as e:
        conn.rollback()
        logging.error(f"Erro ao salvar alunos do Sponte: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def atualizar_no_banco(aluno: str, novo_status: str) -> bool:
    """Atualiza o status de um aluno no banco de dados."""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE chamadas
        SET status = ?
        WHERE aluno_id = (SELECT id FROM alunos WHERE nome = ?)
        AND date(data) = date('now')
        """, (novo_status, aluno))
        
        conn.commit()
        logging.info(f"Status de {aluno} atualizado para {novo_status} na data de hoje.")
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        logging.error(f"Erro ao atualizar status: {e}")
        return False
    finally:
        if conn:
            conn.close()

def verificar_discrepancias() -> pd.DataFrame:
    """Verifica discrepâncias entre a planilha de horários e o banco de dados."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        if not ARQUIVO_HORARIOS.exists():
            logging.warning(f"Arquivo de horários '{ARQUIVO_HORARIOS.name}' não encontrado para verificar discrepâncias.")
            return pd.DataFrame()

        # Usar pd.read_excel para arquivos .xlsx
        # Assumindo a planilha de horários tem uma aba como 'SEGUNDA' e alunos na coluna 1 (index 0)
        df_planilha_bruta = pd.read_excel(ARQUIVO_HORARIOS, sheet_name="SEGUNDA", header=None) # header=None para ler tudo primeiro
        
        # Ajuste para pegar os nomes dos alunos, similar ao sponte_scraper
        header_row_index = -1
        for i, row in df_planilha_bruta.iterrows():
            # Procura por uma linha que contenha horários para identificar o cabeçalho
            if row.astype(str).str.contains('às', na=False).any():
                header_row_index = i
                break
        
        if header_row_index != -1:
            # Pula as linhas acima do cabeçalho real e remove a primeira coluna (dia da semana)
            df_planilha = df_planilha_bruta.iloc[header_row_index + 1:].drop(columns=[0], errors='ignore')
            all_names_in_sheet = set()
            for col in df_planilha.columns:
                for name in df_planilha[col].dropna().unique():
                    all_names_in_sheet.add(str(name).strip().upper())
            
            df_planilha_nomes = pd.DataFrame(list(all_names_in_sheet), columns=['nome'])
        else:
            logging.warning("Não foi possível identificar a estrutura da planilha de horários para discrepâncias.")
            return pd.DataFrame()

        df_db = pd.read_sql_query(
            "SELECT nome FROM alunos",
            conn
        )
        df_db['nome'] = df_db['nome'].str.strip().str.upper()

        discrepantes = df_planilha_nomes[
            ~df_planilha_nomes['nome'].isin(df_db['nome'])
        ].copy()
        
        return discrepantes[['nome']]
    except Exception as e:
        logging.error(f"Erro ao verificar discrepâncias: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()

# --- Funções de Lembretes e Comportamento ---
def salvar_lembrete(aluno_id: int, lembrete_txt: str, professor: str) -> bool:
    """Salva um novo lembrete no banco de dados."""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO lembretes (aluno_id, data_criacao, lembrete, professor_responsavel) VALUES (?, date('now'), ?, ?)",
            (aluno_id, lembrete_txt, professor)
        )
        conn.commit()
        logging.info(f"Lembrete salvo para aluno_id {aluno_id}.")
        return True
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Erro ao salvar lembrete: {e}")
        return False
    finally:
        if conn: conn.close()

def carregar_lembretes_aluno(aluno_id: int) -> pd.DataFrame:
    """Carrega o histórico de lembretes de um aluno."""
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    try:
        query = """
            SELECT data_criacao, lembrete, professor_responsavel, concluido
            FROM lembretes
            WHERE aluno_id = ?
            ORDER BY data_criacao DESC
        """
        df = pd.read_sql_query(query, conn, params=(aluno_id,))
        if not df.empty:
            df['data_criacao'] = pd.to_datetime(df['data_criacao']).dt.strftime('%d/%m/%Y')
        return df
    except Exception as e:
        logging.error(f"Erro ao carregar lembretes para aluno_id {aluno_id}: {e}")
        return pd.DataFrame()
    finally:
        if conn: conn.close()

def salvar_comportamento(aluno_id: int, tipo: str, observacao: str, data: str, professor: str) -> bool:
    """Salva um registro de comportamento."""
    conn = get_db_connection()
    if not conn: return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO comportamentos (aluno_id, data, observacao, tipo, professor_responsavel) VALUES (?, ?, ?, ?, ?)",
            (aluno_id, data, observacao, tipo, professor)
        )
        conn.commit()
        logging.info(f"Comportamento salvo para aluno_id {aluno_id}.")
        return True
    except sqlite3.Error as e:
        conn.rollback()
        logging.error(f"Erro ao salvar comportamento: {e}")
        return False
    finally:
        if conn: conn.close()

def carregar_comportamento_aluno(aluno_id: int) -> pd.DataFrame:
    """Carrega o histórico de comportamento de um aluno."""
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    try:
        query = """
            SELECT data, tipo, observacao, professor_responsavel
            FROM comportamentos
            WHERE aluno_id = ?
            ORDER BY data DESC
        """
        df = pd.read_sql_query(query, conn, params=(aluno_id,))
        if not df.empty:
            df['data'] = pd.to_datetime(df['data']).dt.strftime('%d/%m/%Y')
        return df
    except Exception as e:
        logging.error(f"Erro ao carregar comportamento para aluno_id {aluno_id}: {e}")
        return pd.DataFrame()
    finally:
<<<<<<< HEAD
        if conn: conn.close()

# A FUNÇÃO ABAIXO FOI MOVIDA PARA O NÍVEL CORRETO DE INDENTAÇÃO
def get_student_history(aluno_id: int) -> pd.DataFrame:
    """Carrega o histórico de faltas de um aluno."""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
        
    try:
        query = """
        SELECT data, status, justificativa, professor_responsavel as justificado_por
        FROM chamadas
        WHERE aluno_id = ? AND status = 'Faltou'
        ORDER BY data DESC
        """
        df = pd.read_sql_query(query, conn, params=(aluno_id,))
        return df
    except Exception as e:
        logging.error(f"Erro ao carregar histórico do aluno {aluno_id}: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            conn.close()
=======
        if conn: conn.close()
>>>>>>> c19bda253a042a39f0d8d16acd0dc96f2b1dabae
