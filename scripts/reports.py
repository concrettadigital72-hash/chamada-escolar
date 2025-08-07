from typing import Tuple, Optional, Union
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

from .db_utils import carregar_faltas_por_periodo, EXPORT_DIR
from .analysis import gerar_ranking_faltas, gerar_resumo_estatistico

def gerar_relatorio_excel_completo(
    data_inicio: datetime,
    data_fim: datetime,
    categorias: Optional[list] = None
) -> Tuple[bool, Union[Path, str]]:
    """Gera um relatório Excel com dados de faltas no período especificado.
    
    Args:
        data_inicio: Data de início do período
        data_fim: Data de fim do período
        categorias: Lista de categorias para filtrar (opcional)
        
    Returns:
        Tuple com sucesso (bool) e caminho do arquivo ou mensagem de erro
    """
    try:
        df_faltas = carregar_faltas_por_periodo(data_inicio, data_fim, categorias)
        if df_faltas.empty:
            logging.info("Nenhuma falta encontrada para este período para gerar relatório.")
            return False, "Nenhuma falta encontrada para este período."
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"relatorio_faltas_{timestamp}.xlsx"
        caminho_arquivo = EXPORT_DIR / nome_arquivo
        
        with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
            df_faltas.to_excel(
                writer,
                sheet_name='Faltas Detalhadas',
                index=False
            )
            
            df_ranking = gerar_ranking_faltas(df_faltas)
            # gerar_ranking_faltas agora retorna um DataFrame vazio se não houver dados
            if not df_ranking.empty:
                df_ranking.to_excel(
                    writer,
                    sheet_name='Ranking de Faltas',
                    index=False
                )
            else:
                logging.info("Nenhum dado para o ranking de faltas no relatório.")
            
            resumo = gerar_resumo_estatistico(df_faltas)
            if not resumo.empty:
                resumo.to_excel(
                    writer,
                    sheet_name='Resumo Estatístico',
                    index=True
                )
            else:
                logging.info("Nenhum dado para o resumo estatístico no relatório.")
        
        logging.info(f"Relatório Excel gerado em: {caminho_arquivo}")
        return True, caminho_arquivo
    except Exception as e:
        logging.error(f"Erro ao gerar relatório Excel: {e}")
        return False, f"Erro ao gerar relatório: {e}"