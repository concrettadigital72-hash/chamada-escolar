import streamlit as st
import logging
import pandas as pd
from .sponte_scraper import executar_scraper_sponte
from scripts.db_utils import get_db_connection
from migrate_to_db import migrar_historico_chamadas
import traceback
from scripts.sponte_scraper import executar_scraper_sponte

logging.basicConfig(level=logging.INFO)

def sincronizar_dados(credenciais: dict):
    """Função principal de sincronização de dados."""
    st.info("Iniciando sincronização de dados...")
    
    # Verifica se as credenciais estão presentes
    if not credenciais.get('username') or not credenciais.get('password'):
        st.error("Credenciais do Sponte não configuradas corretamente.")
        return
    
    # 1. Sincronização de alunos via Sponte Web
    with st.spinner("Buscando dados de alunos no Sponte Web..."):
        try:
            resultado_scraper = executar_scraper_sponte(credenciais)
            
            if resultado_scraper.get('sucesso'):
                st.success(f"Dados de alunos obtidos do Sponte Web com sucesso! {len(resultado_scraper['alunos'])} alunos encontrados.")
                
                # Salva os alunos no banco de dados
                conn = get_db_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        alunos_novos = [
                            (nome,) for nome in resultado_scraper['alunos']
                            if nome and nome.strip()
                        ]
                        
                        if alunos_novos:
                            cursor.executemany(
                                "INSERT OR IGNORE INTO alunos (nome) VALUES (?)",
                                alunos_novos
                            )
                            conn.commit()
                            st.success(f"{len(alunos_novos)} novos alunos salvos no banco de dados.")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Erro ao salvar alunos no banco: {e}")
                    finally:
                        conn.close()
            else:
                st.error(f"Erro ao buscar dados de alunos no Sponte: {resultado_scraper.get('mensagem', 'Erro desconhecido')}")
                return
                
        except Exception as e:
            st.error(f"Erro inesperado durante a sincronização: {e}")
            logging.error(f"Erro na sincronização: {traceback.format_exc()}")
            return
    
    st.success("Sincronização concluída!")