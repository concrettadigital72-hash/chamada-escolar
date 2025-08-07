from typing import Dict, List, Optional, Any
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from datetime import timedelta, datetime
import logging
from plotly.graph_objs import Figure

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def detectar_padroes_de_falta(df_faltas: pd.DataFrame) -> pd.DataFrame:
    """Detecta padrões preocupantes de frequência escolar."""
    if df_faltas.empty:
        return pd.DataFrame(columns=["Aluno", "Alerta"])
    
    df_faltas.columns = [col.lower() for col in df_faltas.columns]
    
    if 'data' not in df_faltas.columns or 'nome_aluno' not in df_faltas.columns:
        logging.warning("DataFrame de faltas vazio ou colunas 'data'/'nome_aluno' ausentes para detectar padrões.")
        return pd.DataFrame(columns=["Aluno", "Alerta"]) # Retorna DataFrame vazio
    
    alertas = []
    df_faltas['data'] = pd.to_datetime(df_faltas['data'], errors='coerce')
    df_faltas.dropna(subset=['data'], inplace=True) # Remove linhas com data inválida
    
    if df_faltas.empty:
        logging.info("Nenhum dado válido de faltas após processamento para detectar padrões.")
        return pd.DataFrame(columns=["Aluno", "Alerta"])

    for nome, grupo in df_faltas.groupby('nome_aluno'):
        grupo_valido = grupo.dropna(subset=['data']).sort_values('data')
        if len(grupo_valido) < 2:
            continue
            
        sete_dias_atras = datetime.now() - timedelta(days=7)
        faltas_recentes = grupo_valido[
            (grupo_valido['data'] >= sete_dias_atras) &
            (grupo_valido['status'].str.lower() == 'faltou')
        ]
        if len(faltas_recentes) >= 3:
            alertas.append({
                "Aluno": nome, 
                "Alerta": f"⚠️ {len(faltas_recentes)} faltas nos últimos 7 dias"
            })
        
        faltas_consecutivas_grupo = grupo_valido[grupo_valido['status'].str.lower() == 'faltou'].copy()
        if len(faltas_consecutivas_grupo) > 1:
            faltas_consecutivas_grupo = faltas_consecutivas_grupo.sort_values('data')
            dias_faltas = faltas_consecutivas_grupo['data'].diff().dt.days
            if (dias_faltas == 1).any():
                alertas.append({
                    "Aluno": nome, 
                    "Alerta": "ℹ️ Possui faltas em dias consecutivos"
                })
    
    return pd.DataFrame(alertas) if alertas else pd.DataFrame(columns=["Aluno", "Alerta"])

def gerar_ranking_faltas(df_faltas: pd.DataFrame) -> pd.DataFrame:
    """
    Gera um ranking dos alunos com mais faltas.
    Espera um DataFrame com as colunas 'nome_aluno' e 'status'.
    """
    try:
        # Garante que as colunas existem antes de tentar acessá-las
        if df_faltas.empty or 'nome_aluno' not in df_faltas.columns or 'status' not in df_faltas.columns:
            logging.warning("DataFrame de faltas vazio ou colunas 'nome_aluno'/'status' ausentes para o ranking.")
            return pd.DataFrame(columns=['Aluno', 'Total de Faltas']) # Retorna um DataFrame vazio com as colunas esperadas
        
        # Filtra apenas as faltas
        df_faltas_apenas = df_faltas[df_faltas['status'].str.lower() == 'faltou'].copy()
        
        if df_faltas_apenas.empty:
            logging.info("Nenhuma falta registrada para gerar o ranking.")
            return pd.DataFrame(columns=['Aluno', 'Total de Faltas'])
        
        # Agrupa por 'nome_aluno' e conta as faltas
        ranking = df_faltas_apenas['nome_aluno'].value_counts().reset_index()
        ranking.columns = ['Aluno', 'Total de Faltas'] # Renomeia as colunas para exibição
        
        return ranking.sort_values('Total de Faltas', ascending=False)
    except Exception as e:
        logging.error(f"Erro ao gerar ranking: {e}")
        return pd.DataFrame(columns=['Aluno', 'Total de Faltas']) # Retorna DataFrame vazio em caso de erro

def gerar_grafico_calendario(df_faltas: pd.DataFrame) -> Optional[Figure]:
    """Gera um gráfico de calor (heatmap) para faltas por dia."""
    if df_faltas.empty or 'data' not in df_faltas.columns or 'status' not in df_faltas.columns:
        logging.warning("DataFrame de faltas vazio ou colunas 'data'/'status' ausentes para o calendário.")
        return None
        
    try:
        df_faltas['data'] = pd.to_datetime(df_faltas['data'])
        df_faltas.dropna(subset=['data'], inplace=True) # Remove linhas com data inválida

        faltas_por_dia = df_faltas[df_faltas['status'].str.lower() == 'faltou']
        
        if faltas_por_dia.empty:
            logging.info("Nenhuma falta registrada para o gráfico de calendário.")
            return None
            
        faltas_por_dia = faltas_por_dia.groupby(faltas_por_dia['data'].dt.date).size().reset_index(name='Faltas')
        faltas_por_dia.columns = ['Data', 'Faltas']
        
        fig = px.density_heatmap(
            faltas_por_dia,
            x='Data',
            y='Faltas',
            title="Faltas por Dia",
            color_continuous_scale="Viridis"
        )
        return fig
    except Exception as e:
        logging.error(f"Erro ao gerar gráfico de calendário: {e}")
        return None

def gerar_grafico_top_faltas(df_faltas: pd.DataFrame, top_n: int = 10) -> Optional[plt.Figure]:
    """Gera gráfico de barras com alunos com mais faltas."""
    try:
        ranking_df = gerar_ranking_faltas(df_faltas) # Esta função agora retorna DataFrame vazio em caso de erro/sem dados
        if ranking_df.empty: # Verifica se está vazio, não se é None
            logging.info("Nenhum dado de ranking para gerar o gráfico Top N faltas.")
            return None
            
        top_alunos = ranking_df.head(top_n)
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bars = ax.barh(
            top_alunos['Aluno'],
            top_alunos['Total de Faltas'],
            color='#1f77b4'
        )
        
        ax.bar_label(bars, padding=3, fontsize=10)
        ax.invert_yaxis()
        ax.set_xlabel('Total de Faltas', fontsize=12)
        ax.set_title(f"Top {top_n} Alunos com Mais Faltas", fontsize=14, pad=20)
        plt.tight_layout()
        
        return fig
    except Exception as e:
        logging.error(f"Erro ao gerar gráfico de top faltas: {e}")
        return None

def gerar_resumo_estatistico(df_faltas: pd.DataFrame) -> pd.DataFrame:
    """Gera um resumo estatístico das faltas."""
    if df_faltas.empty:
        logging.info("DataFrame de faltas vazio para gerar resumo estatístico.")
        return pd.DataFrame()
    
    resumo = pd.DataFrame()
    
    if 'categoria_justificativa' in df_faltas.columns:
        contagem_categorias = df_faltas['categoria_justificativa'].value_counts()
        if not contagem_categorias.empty:
            resumo['Faltas por Categoria'] = contagem_categorias
        else:
            logging.info("Nenhuma categoria de justificativa encontrada.")
    
    if 'professor_responsavel' in df_faltas.columns:
        contagem_professor = df_faltas['professor_responsavel'].value_counts()
        if not contagem_professor.empty:
            resumo['Faltas por Professor'] = contagem_professor
        else:
            logging.info("Nenhum professor responsável encontrado.")
    
    if 'ligacao_feita' in df_faltas.columns:
        contato_realizado = df_faltas['ligacao_feita'].value_counts().rename(
            {True: 'Sim', False: 'Não'}
        )
        if not contato_realizado.empty:
            resumo['Contato Realizado'] = contato_realizado
        else:
            logging.info("Nenhum status de 'ligacao_feita' encontrado.")
    
    return resumo