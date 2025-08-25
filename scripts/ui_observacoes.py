    # scripts/ui_observacoes.py

import streamlit as st
import pandas as pd
from datetime import date
from .db_utils import get_db_connection, carregar_alunos_db

def pagina_observacoes(professor_logado):
        """
        Renderiza a página para adicionar e visualizar observações diárias.
        """
        st.title("📝 Registro de Observações Diárias")
        st.divider()

        alunos_df, _ = carregar_alunos_db()
        if alunos_df.empty:
            st.warning("Nenhum aluno encontrado no banco de dados. Importe os alunos primeiro.")
            st.stop()

        # --- Formulário para adicionar nova observação ---
        with st.form("form_nova_observacao", clear_on_submit=True):
            st.subheader("Adicionar Nova Observação")

            # Mapeia 'nome (turma)' para o ID do aluno
            alunos_map = {f"{row['nome']} ({row['turma']})": row['id'] for index, row in alunos_df.iterrows()}
            aluno_selecionado_display = st.selectbox(
                "Selecione o Aluno:",
                options=alunos_map.keys()
            )

            tipo_observacao = st.selectbox(
                "Tipo de Observação:",
                ["Atraso", "Comportamento", "Entrega de Tarefa", "Participação", "Material Esquecido", "Uniforme Irregular", "Problema de Saúde", "Outro"]
            )
            
            detalhes = st.text_area("Detalhes:", placeholder="Ex: Chegou 30 minutos atrasado, justificou com problema de transporte")
            
            acao_tomada = st.selectbox(
                "Ação Tomada:",
                ["Nenhuma ação específica", "Comunicação com os pais", "Advertência oral", "Advertência escrita", "Encaminhamento à coordenação", "Outra medida"]
            )

            submitted = st.form_submit_button("➕ Adicionar Observação", type="primary")

            if submitted:
                if not detalhes:
                    st.error("O campo 'Detalhes' é obrigatório.")
                else:
                    aluno_id = alunos_map[aluno_selecionado_display]
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO observacoes (data, aluno_id, tipo, detalhes, acao_tomada, professor)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            str(date.today()),
                            aluno_id,
                            tipo_observacao,
                            detalhes,
                            acao_tomada,
                            professor_logado
                        ))
                        conn.commit()
                        st.success(f"Observação para '{aluno_selecionado_display}' adicionada com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar no banco de dados: {e}")
                    finally:
                        if conn:
                            conn.close()

        st.divider()

        # --- Visualização das observações do dia ---
        st.subheader(f"Observações de Hoje ({date.today().strftime('%d/%m/%Y')})")

        try:
            conn = get_db_connection()
            # Usamos um JOIN para pegar o nome do aluno em vez do ID
            query = """
                SELECT 
                    o.data,
                    a.nome as Aluno,
                    a.turma as Turma,
                    o.tipo as Tipo,
                    o.detalhes as Detalhes,
                    o.acao_tomada as "Ação Tomada",
                    o.professor as Professor
                FROM observacoes o
                JOIN alunos a ON o.aluno_id = a.id
                WHERE o.data = ?
                ORDER BY o.id DESC
            """
            df_observacoes = pd.read_sql_query(query, conn, params=(str(date.today()),))
            
            if df_observacoes.empty:
                st.info("Nenhuma observação registrada hoje.")
            else:
                st.dataframe(df_observacoes, use_container_width=True)

        except Exception as e:
            st.error(f"Erro ao carregar observações: {e}")
        finally:
            if conn:
                conn.close()
# --- Fim do arquivo ui_observacoes.py ---