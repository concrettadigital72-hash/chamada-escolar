from typing import Optional, Dict, Any
import streamlit as st
import pandas as pd
from datetime import date, datetime
import plotly.express as px
import matplotlib.pyplot as plt
import toml
from pathlib import Path


# Importações de módulos locais
from .db_utils import (
    get_db_connection,
    carregar_alunos_db,
    carregar_horarios,
    salvar_justificativa_db,
    salvar_chamada_db,
    atualizar_no_banco,
    carregar_todas_faltas,
    classificar_justificativa,
    salvar_lembrete,
    carregar_lembretes_aluno,
    salvar_comportamento,
    carregar_comportamento_aluno,
    # verificar_e_inserir_dados_teste # Removido: esta função está em database_setup.py
)
from .analysis import (
    detectar_padroes_de_falta,
    gerar_grafico_calendario,
    gerar_grafico_top_faltas,
    gerar_ranking_faltas,
    gerar_resumo_estatistico
)
from .reports import gerar_relatorio_excel_completo
# from .sponte_scraper import configurar_driver, extrair_dados_chamada # Removido: sponte_scraper não usado diretamente aqui

def pagina_chamada(xls_horarios: pd.ExcelFile, df_base_alunos: pd.DataFrame, professor_logado: str) -> None:
    st.header("📅 Realizar Chamada Diária")
    
    if not isinstance(xls_horarios, pd.ExcelFile) or df_base_alunos.empty:
        st.error("Dados necessários não disponíveis. Verifique o arquivo de horários ou a base de alunos.")
        return
        
    col1, col2 = st.columns(2)
    with col1:
        abas_disponiveis = [aba for aba in xls_horarios.sheet_names if "Planilha" not in str(aba)]
        dia_selecionado = st.selectbox("Dia da Semana:", abas_disponiveis)
    
    df_dia_raw = pd.read_excel(xls_horarios, sheet_name=dia_selecionado, header=None)
    header_row_index = next(
        (i for i, row in df_dia_raw.iterrows() 
         if row.astype(str).str.lower().str.contains('às').any()), 
        -1
    )
    
    if header_row_index == -1:
        st.error("Não foi possível identificar os horários na planilha.")
        return
        
    horarios_disponiveis = [h for h in df_dia_raw.iloc[header_row_index] if "às" in str(h).lower()]
    
    with col2:
        horario_selecionado = st.selectbox("Horário:", horarios_disponiveis)
    
    if not horario_selecionado:
        return
        
    st.divider()
    
    header_series = df_dia_raw.iloc[header_row_index]
    col_index = next(
        (i for i, col_name in enumerate(header_series) 
         if str(col_name) == horario_selecionado), 
        -1
    )
    
    if col_index == -1:
        st.error(f"Horário '{horario_selecionado}' não encontrado.")
        return
        
    lista_alunos_bruta = df_dia_raw.iloc[header_row_index + 1:, col_index].dropna()
    lista_alunos_filtrada = [
        aluno for aluno in lista_alunos_bruta 
        if "PC EM MANUTENÇÃO" not in str(aluno).upper()
    ]
    
    turma_id = f"{dia_selecionado}-{horario_selecionado}"
    if 'chamadas_da_sessao' not in st.session_state:
        st.session_state.chamadas_da_sessao = {}
    
    if turma_id not in st.session_state.chamadas_da_sessao:
        st.session_state.chamadas_da_sessao[turma_id] = {
            aluno: 'Presente' for aluno in sorted(lista_alunos_filtrada)
        }
    
    st.subheader(f"Chamada: {dia_selecionado.title()} - {horario_selecionado}")
    
    if not st.session_state.chamadas_da_sessao[turma_id]:
        st.warning("Nenhum aluno cadastrado para este horário.")
        return
        
    col_turma1, col_turma2 = st.columns(2)
    alunos = sorted(st.session_state.chamadas_da_sessao[turma_id].keys())
    metade = len(alunos) // 2 + len(alunos) % 2
    
    for i, aluno in enumerate(alunos):
        col = col_turma1 if i < metade else col_turma2
        
        with col:
            status_atual = st.session_state.chamadas_da_sessao[turma_id][aluno]
            novo_status = st.radio(
                f"**{aluno}**",
                options=['Presente', 'Faltou'],
                index=0 if status_atual == 'Presente' else 1,
                key=f"{aluno}_{turma_id}",
                horizontal=True
            )
            st.session_state.chamadas_da_sessao[turma_id][aluno] = novo_status
    
    st.divider()
    
    if st.button("💾 Salvar Presenças e Faltas", type="primary", use_container_width=True):
        with st.spinner("Salvando registros..."):
            for aluno, status in st.session_state.chamadas_da_sessao[turma_id].items():
                aluno_info = df_base_alunos[df_base_alunos['nome'] == aluno]
                
                if not aluno_info.empty:
                    aluno_id = int(aluno_info.iloc[0]['id'])
                    salvar_chamada_db(
                        aluno_id=aluno_id,
                        data_chamada=date.today(),
                        horario=horario_selecionado,
                        status=status,
                        professor=professor_logado
                    )
                    
                    if status == 'Faltou' and aluno not in st.session_state.ausentes_do_dia:
                        st.session_state.ausentes_do_dia[aluno] = {
                            "ligacao": False,
                            "justificativa": "",
                            "id": aluno_id
                        }
            
            st.success("Chamada salva com sucesso!")
            st.rerun()

def pagina_gestao_individual(df_base_alunos: pd.DataFrame, professor_logado: str) -> None:
    st.header("👤 Gestão Individual de Alunos")
    
    if df_base_alunos.empty:
        st.warning("Base de alunos vazia. Por favor, cadastre alunos no banco de dados.")
        return
        
    lista_nomes_alunos = [""] + sorted(df_base_alunos['nome'].tolist())
    aluno_selecionado = st.selectbox("Selecione um aluno:", lista_nomes_alunos)
    
    if not aluno_selecionado:
        return
        
    aluno_info = df_base_alunos[df_base_alunos['nome'] == aluno_selecionado].iloc[0]
    aluno_id = int(aluno_info['id'])
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Histórico", 
        "📝 Justificar", 
        "🔔 Lembretes", 
        "📌 Comportamento"
    ])
    
    with tab1:
        st.subheader(f"Histórico de {aluno_selecionado}")
        
        conn = get_db_connection()
        if conn:
            try:
                df_historico = pd.read_sql_query(
                    f"""SELECT data, status, justificativa, professor_responsavel 
                        FROM chamadas 
                        WHERE aluno_id = {aluno_id} 
                        ORDER BY data DESC""",
                    conn
                )
                
                if df_historico.empty:
                    st.success("Nenhum registro de chamada encontrado para este aluno.")
                else:
                    df_historico['data'] = pd.to_datetime(df_historico['data'])
                    df_display = df_historico.copy()
                    df_display['data_formatada'] = df_display['data'].dt.strftime('%d/%m/%Y')
                    
                    st.dataframe(
                        df_display[['data_formatada', 'status', 'justificativa', 'professor_responsavel']],
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    st.subheader("Frequência Mensal")
                    faltas_mes = df_historico[df_historico['status'] == 'Faltou']
                    faltas_mes = faltas_mes.set_index('data').groupby(pd.Grouper(freq='M')).size()
                    
                    if not faltas_mes.empty:
                        faltas_mes.index = faltas_mes.index.strftime('%b/%Y')
                        st.bar_chart(faltas_mes)
                    else:
                        st.info("Nenhuma falta registrada para este aluno.")
            finally:
                conn.close()
    
    with tab2:
        st.subheader("Justificar Faltas")
        
        data_falta = st.date_input("Data da falta:")
        justificativa = st.text_area("Justificativa:")
        
        if st.button("Salvar Justificativa", type="primary"):
            if not justificativa:
                st.warning("Informe a justificativa.")
            else:
                sucesso, erro = salvar_justificativa_db(
                    aluno_id=aluno_id,
                    data_falta=data_falta,
                    justificativa=justificativa,
                    professor=professor_logado,
                    ligacao_feita=True,
                    categorias_config=st.session_state.get('CATEGORIAS_JUSTIFICATIVAS', {})
                )
                
                if sucesso:
                    st.success("Justificativa salva com sucesso!")
                else:
                    st.error(f"Erro: {erro}")
    
    with tab3:
        st.subheader("Lembretes")
        
        with st.form("novo_lembrete"):
            novo_lembrete_txt = st.text_area("Novo Lembrete:")
            if st.form_submit_button("Salvar Lembrete"):
                if novo_lembrete_txt:
                    sucesso = salvar_lembrete(aluno_id, novo_lembrete_txt, professor_logado)
                    if sucesso:
                        st.success("Lembrete salvo com sucesso!")
                    else:
                        st.error("Erro ao salvar lembrete.")
        
        st.subheader("Lembretes Registrados")
        df_lembretes = carregar_lembretes_aluno(aluno_id)
        if not df_lembretes.empty:
            for _, row in df_lembretes.iterrows():
                st.write(f"**{row['data_criacao']}** - {row['lembrete']} (Por: {row['professor_responsavel']})")
        else:
            st.info("Nenhum lembrete encontrado para este aluno.")
    
    with tab4:
        st.subheader("Registro de Comportamento")
        
        with st.form("novo_comportamento"):
            tipo_comportamento = st.radio("Tipo:", ["Elogio", "Ocorrência"])
            observacao_comportamento = st.text_area("Observação:")
            data_comportamento = st.date_input("Data do Registro:")
            if st.form_submit_button("Registrar Comportamento"):
                if observacao_comportamento:
                    sucesso = salvar_comportamento(
                        aluno_id, 
                        tipo_comportamento, 
                        observacao_comportamento, 
                        data_comportamento.isoformat(), 
                        professor_logado
                    )
                    if sucesso:
                        st.success("Registro de comportamento salvo!")
                    else:
                        st.error("Erro ao salvar registro de comportamento.")
        
        st.subheader("Histórico de Comportamento")
        df_comportamento = carregar_comportamento_aluno(aluno_id)
        if not df_comportamento.empty:
            for _, row in df_comportamento.iterrows():
                st.write(f"**{row['data']}** - {row['tipo']}: {row['observacao']} (Por: {row['professor_responsavel']})")
        else:
            st.info("Nenhum registro de comportamento encontrado para este aluno.")

def pagina_dashboard(categorias_config: Dict[str, Any]) -> None:
    """Renderiza o dashboard de análise de faltas."""
    st.header("📊 Dashboard de Análise", divider="rainbow")
    
    df_faltas = carregar_todas_faltas()
    
    if df_faltas.empty:
        st.info("Nenhum dado de falta disponível para análise. O sistema pode estar vazio ou ainda não há registros.")
        return
        
    st.subheader("🚨 Alertas e Padrões")
    df_alertas = detectar_padroes_de_falta(df_faltas)
    
    if df_alertas.empty:
        st.success("✅ Nenhum padrão preocupante detectado.")
    else:
        st.dataframe(df_alertas, use_container_width=True, hide_index=True)
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 Faltas por Mês")
        if not df_faltas.empty:
            df_faltas['data'] = pd.to_datetime(df_faltas['data'])
            faltas_por_mes = df_faltas.set_index('data').groupby(pd.Grouper(freq='M')).size()
            faltas_por_mes.index = faltas_por_mes.index.strftime('%B %Y')
            st.bar_chart(faltas_por_mes)
        else:
            st.info("Nenhum dado de falta para mostrar a frequência mensal.")
        
        st.subheader("🏆 Alunos com Mais Presenças")
        df_presentes = df_faltas[df_faltas['status'].str.upper() == 'P']
        if not df_presentes.empty:
            contagem_presencas = df_presentes['nome_aluno'].value_counts().reset_index()
            contagem_presencas.columns = ['Aluno', 'Total de Presenças']
            st.dataframe(contagem_presencas.head(5), 
                        hide_index=True, 
                        column_config={"Aluno": "Aluno", "Total de Presenças": "Presenças"})
        else:
            st.info("Nenhum registro de presença encontrado.")
    
    with col2:
        st.subheader("📌 Motivos das Faltas")
        if 'justificativa' in df_faltas.columns and not df_faltas['justificativa'].empty:
            df_faltas_justificadas = df_faltas[df_faltas['status'].str.lower() == 'faltou'].dropna(subset=['justificativa'])
            
            if not df_faltas_justificadas.empty:
                df_faltas_justificadas['categoria'] = df_faltas_justificadas['justificativa'].apply(
                    lambda x: classificar_justificativa(x, categorias_config))
                
                contagem_categorias = df_faltas_justificadas['categoria'].value_counts()
                fig_pie = px.pie(
                    contagem_categorias, 
                    values=contagem_categorias.values,
                    names=contagem_categorias.index,
                    title="Distribuição de Justificativas"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Nenhuma justificativa válida para faltas encontrada para classificação.")
        else:
            st.info("Nenhuma justificativa registrada.")

def pagina_relatorios() -> None:
    """Renderiza a página de relatórios e ferramentas."""
    st.header("📋 Relatórios e Ferramentas", divider="rainbow")
    
    with st.expander("📊 Gerar Relatórios", expanded=True):
        try:
            config_path = Path(__file__).resolve().parents[2] / "config.toml"
            config = toml.load(config_path)
            categorias = config.get("categorias", {})
            lista_categorias = [
                cat.replace("motivo_", "").replace("_", " ").title()
                for cat in categorias if isinstance(categorias.get(cat), list)
            ]
        except FileNotFoundError:
            lista_categorias = []
            st.warning("Arquivo config.toml não encontrado para categorização.")
        except Exception as e:
            lista_categorias = []
            st.error(f"Erro ao carregar categorias do config.toml: {e}")
        
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data inicial:", value=datetime.today().replace(day=1))
        with col2:
            data_fim = st.date_input("Data final:", value=datetime.today())
        
        categorias_selecionadas = st.multiselect(
            "Filtrar por categoria de justificativa:",
            options=lista_categorias,
            default=[]
        )
        
        if st.button("📥 Gerar Relatório Completo (Excel)", type="primary"):
            with st.spinner("Gerando relatório..."):
                sucesso, resultado = gerar_relatorio_excel_completo(
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                    categorias=categorias_selecionadas
                )
                
                if sucesso and isinstance(resultado, Path):
                    with open(resultado, "rb") as f:
                        st.download_button(
                            "⬇️ Baixar Relatório",
                            data=f,
                            file_name=resultado.name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    st.success("Relatório gerado com sucesso!")
                else:
                    st.error(resultado)

    st.divider()
    
    with st.expander("📈 Visualizações Analíticas", expanded=True):
        tab1, tab2, tab3 = st.tabs(["Calendário", "Ranking", "Top 10"])
        
        df_faltas = carregar_todas_faltas()

        with tab1:
            st.subheader("Calendário de Faltas")
            fig_calendario = gerar_grafico_calendario(df_faltas)
            
            if fig_calendario:
                st.plotly_chart(fig_calendario, use_container_width=True)
            else:
                st.info("Nenhum dado de falta disponível para o calendário.")
        
        with tab2:
            st.subheader("Ranking de Faltas")
            df_ranking = gerar_ranking_faltas(df_faltas)
            
            if not df_ranking.empty: # Verifica se está vazio, não se é None
                st.dataframe(df_ranking, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum dado disponível para o ranking.")
        
        with tab3:
            st.subheader("Top 10 Alunos com Mais Faltas")
            fig_top10 = gerar_grafico_top_faltas(df_faltas)
            
            if fig_top10:
                st.pyplot(fig_top10)
            else:
                st.info("Nenhum dado disponível para o gráfico Top 10.")