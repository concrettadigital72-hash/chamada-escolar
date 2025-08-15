from typing import Optional, Tuple, Dict, Any, Union
import streamlit as st
import toml
from datetime import datetime
from pathlib import Path
from scripts.db_utils import carregar_todas_faltas, carregar_faltas_por_periodo, EXPORT_DIR
from scripts.reports import gerar_relatorio_excel_completo
import pandas as pd
import logging
from scripts.db_utils import get_db_connection
import matplotlib.pyplot as plt
<<<<<<< HEAD
from .db_utils import carregar_todas_faltas

=======
>>>>>>> c19bda253a042a39f0d8d16acd0dc96f2b1dabae
from scripts.analysis import (
    gerar_ranking_faltas,
    gerar_grafico_calendario,
    gerar_grafico_top_faltas,
    gerar_resumo_estatistico
)
from scripts.sponte_scraper import executar_scraper_sponte
from scripts.sync_data import sincronizar_dados

def pagina_relatorios() -> None:
    """Renderiza a página de relatórios e ferramentas."""
    st.header("📋 Relatórios e Ferramentas", divider="rainbow")
<<<<<<< HEAD
    df_total_faltas = carregar_todas_faltas()

    if df_total_faltas.empty:
        st.warning("Nenhum dado de falta foi encontrado na base de dados. Execute o script de migração (migrate_to_db.py) se tiver dados históricos em planilhas.")
=======
    df_total_faltas = pd.DataFrame()  # Inicializa um DataFrame vazio

    if df_total_faltas.empty:
        st.warning("Nenhum dado de falta foi encontrado nos arquivos CSV. Verifique se os arquivos estão na pasta correta e não estão vazios.")
>>>>>>> c19bda253a042a39f0d8d16acd0dc96f2b1dabae
        return

    tab1, tab2, tab3 = st.tabs(["🗓️ Calendário", "🏆 Ranking", "🔟 Top 10"])

    with tab1:
        st.subheader("Calendário de Faltas")
        with st.spinner("Gerando calendário..."):
            fig_calendario = gerar_grafico_calendario(df_total_faltas)
            if fig_calendario:
<<<<<<< HEAD
                st.plotly_chart(fig_calendario, use_container_width=True, key="relatorio_calendario")
=======
                st.plotly_chart(fig_calendario, use_container_width=True)
>>>>>>> c19bda253a042a39f0d8d16acd0dc96f2b1dabae
            else:
                st.info("Nenhum dado de falta disponível para gerar o calendário.")

    with tab2:
        st.subheader("Ranking de Faltas")
        with st.spinner("Gerando ranking..."):
            df_ranking = gerar_ranking_faltas(df_total_faltas)
            if not df_ranking.empty:
                st.dataframe(df_ranking, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum dado disponível para gerar o ranking.")

    with tab3:
        st.subheader("Top 10 Alunos com Mais Faltas")
        with st.spinner("Gerando gráfico..."):
            fig_top10 = gerar_grafico_top_faltas(df_total_faltas)
            if fig_top10:
<<<<<<< HEAD
                st.plotly_chart(fig_top10, use_container_width=True, key="relatorio_top10")
=======
                st.pyplot(fig_top10)
                plt.close(fig_top10) # Limpa a figura da memória
>>>>>>> c19bda253a042a39f0d8d16acd0dc96f2b1dabae
            else:
                st.info("Nenhum dado disponível para o gráfico de Top 10.")

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM alunos")
            num_alunos = cursor.fetchone()[0]
            if num_alunos == 0:
                st.warning("Nenhum aluno cadastrado no banco de dados. Por favor, sincronize com o Sponte primeiro.")
        finally:
            conn.close()
    
    # Carregar categorias do config.toml
    try:
        config = toml.load(Path(__file__).resolve().parents[1] / "config.toml")
        categorias = config.get("categorias", {})
        lista_categorias = [
            cat.replace("motivo_", "").replace("_", " ").title()
            for cat in categorias
        ]
    except FileNotFoundError:
        lista_categorias = []
        st.warning("Arquivo config.toml não encontrado.")
    
    # Seção de sincronização
    with st.expander("🔄 Sincronização com Sponte Web", expanded=False):
        st.write("Sincronize os dados com o sistema Sponte Web.")
        
        credenciais = {
            'username': st.secrets.get("SPONTE", {}).get("username", ""),
            'password': st.secrets.get("SPONTE", {}).get("password", "")
        }
        
        if st.button("🔄 Buscar Dados no Sponte", help="Pode levar alguns minutos."):
            if not credenciais['username'] or not credenciais['password']:
                st.error("Credenciais do Sponte não configuradas. Verifique o arquivo secrets.toml")
            else:
                sincronizar_dados(credenciais)
    
    st.divider()
    
    # Seção de relatórios e filtros
    with st.expander("📊 Gerar Relatórios", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data inicial:")
        with col2:
            data_fim = st.date_input("Data final:", value=datetime.today())
        
        categorias_selecionadas = st.multiselect(
            "Filtrar por categoria:",
            options=lista_categorias,
            default=None
        )
        
        if st.button("📥 Gerar Relatório Completo (Excel)", type="primary"):
            with st.spinner("Gerando relatório..."):
                sucesso, resultado = gerar_relatorio_excel_completo(
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    categorias=categorias_selecionadas
                )
                
                if sucesso:
                    with open(resultado, "rb") as f:
                        st.download_button(
                            "⬇️ Baixar Relatório",
                            data=f,
                            file_name=resultado.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    st.success("Relatório gerado com sucesso!")
                else:
                    if resultado:
                        st.error(resultado)
                    else:
                        st.error("Erro desconhecido ao gerar o relatório.")
    
    st.divider()
    
    # Seção de visualizações
    with st.expander("📈 Visualizações Analíticas", expanded=True):
        tab1, tab2, tab3 = st.tabs(["Calendário", "Ranking", "Top 10"])
        
        df_faltas = carregar_todas_faltas()
        
        with tab1:
            st.subheader("Calendário de Faltas")
            fig_calendario = gerar_grafico_calendario(df_faltas)
            
            if fig_calendario:
                st.plotly_chart(fig_calendario, use_container_width=True)
            else:
                st.info("Nenhum dado disponível para o calendário.")
        
        with tab2:
            st.subheader("Ranking de Faltas")
            df_ranking = gerar_ranking_faltas(df_faltas)
            
            if df_ranking is not None and not df_ranking.empty:
                st.dataframe(df_ranking, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum dado disponível para o ranking.")
        
        with tab3:
            st.subheader("Top 10 Alunos com Mais Faltas")
            fig_top10 = gerar_grafico_top_faltas(df_faltas)
            
            if fig_top10:
                st.pyplot(fig_top10)
            else:
                st.info("Nenhum dado disponível para o gráfico.")

def gerar_relatorio_excel_completo(
    data_inicio: datetime,
    data_fim: datetime,
    categorias: Optional[list] = None
) -> Tuple[bool, Union[Path, str]]:
    """Gera um relatório Excel com dados de faltas no período especificado."""
    try:
        df_faltas = carregar_faltas_por_periodo(data_inicio, data_fim, categorias)
        if df_faltas.empty:
            return False, "Nenhuma falta encontrada para este período."
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"relatorio_faltas_{timestamp}.xlsx"
        caminho_arquivo = EXPORT_DIR / nome_arquivo
        
        with pd.ExcelWriter(caminho_arquivo, engine='openpyxl') as writer:
            df_faltas.to_excel(writer, sheet_name='Faltas Detalhadas', index=False)
            
            df_ranking = gerar_ranking_faltas(df_faltas)
            if df_ranking is not None and not df_ranking.empty:
                df_ranking.to_excel(writer, sheet_name='Ranking de Faltas', index=False)
            else:
                logging.info("Nenhum dado para o ranking de faltas no relatório.")
            
            resumo = gerar_resumo_estatistico(df_faltas)
            if not resumo.empty:
                resumo.to_excel(writer, sheet_name='Resumo Estatístico', index=True)
            else:
                logging.info("Nenhum dado para o resumo estatístico no relatório.")
        
        logging.info(f"Relatório Excel gerado em: {caminho_arquivo}")
        return True, caminho_arquivo
    except Exception as e:
        logging.error(f"Erro ao gerar relatório Excel: {e}")
        return False, f"Erro ao gerar relatório: {e}"   