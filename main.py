import streamlit as st
from pathlib import Path
import toml
# import streamlit_authenticator as stauth # REMOVIDO: Não usaremos mais esta biblioteca
from datetime import date
import time
import sys
import traceback
import psutil
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
import logging
import bcrypt # Usado para verificar senhas hasheadas (se estiverem no secrets.toml)

# --- GARANTIA ABSOLUTA DE CAMINHO PARA IMPORTAÇÕES LOCAIS ---
project_root = Path(__file__).resolve().parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from scripts.ui_reports import pagina_relatorios

# --- Impressões de depuração ---
# Estes prints podem ser removidos após a depuração inicial, se o app rodar sem problemas
print(f"Diretório raiz do projeto: {project_root}")
print(f"Conteúdo de sys.path: {sys.path}")
print(f"Current working directory: {Path.cwd()}")
print(f"Scripts directory exists: {(project_root / 'scripts').exists()}")

# --- IMPORTAÇÕES DE MÓDULOS LOCAIS (DEPOIS DO sys.path) ---
from scripts.sponte_scraper import configurar_driver, executar_scraper_sponte
from scripts.ui_reports import pagina_relatorios
from scripts.db_utils import (
    get_db_connection,
    carregar_alunos_db,
    carregar_horarios,
    salvar_justificativa_db,
)
from database_setup import setup_database


from scripts.ui_pages import (
    pagina_chamada,
    pagina_gestao_individual,
    pagina_dashboard
)


# --- FUNÇÕES AUXILIARES GLOBAIS ---
def show_error(e):
    """Exibe erros de forma mais amigável"""
    st.error(f"Ocorreu um erro: {str(e)}")
    with st.expander("Detalhes do erro"):
        st.code(traceback.format_exc())

def verificar_dependencias():
    """Verifica se as dependências essenciais estão instaladas."""
    try:
        import pandas, streamlit, selenium # Verificação para pacotes instalados
        return True
    except ImportError as e:
        st.error(f"Faltam dependências: {str(e)}")
        st.info("Execute: pip install -r requirements.txt")
        return False

def verificar_credenciais_sponte():
    """Verifica se as credenciais do Sponte estão configuradas no secrets.toml."""
    if not st.secrets.get("SPONTE", {}).get("username") or \
       not st.secrets.get("SPONTE", {}).get("password"):
        st.error("Credenciais do Sponte (username/password) não configuradas no secrets.toml!")
        st.info("Por favor, adicione as chaves 'username' e 'password' dentro da seção [SPONTE].")
        return False
    return True

def verificar_driver_local():
    """
    Verifica se o ChromeDriver pode ser inicializado e se comunica.
    Esta função usa a função configurar_driver do sponte_scraper.
    """
    try:
        from scripts.sponte_scraper import configurar_driver 
        driver_test = configurar_driver() 
        driver_test.get("https://www.google.com")
        driver_test.quit()
        return True
    except WebDriverException as e:
        st.error(f"Erro no ChromeDriver. Mensagem: {str(e)}")
        st.warning("""
            Problema com o ChromeDriver. Verifique:
            1. Se o navegador Google Chrome está instalado no seu sistema.
            2. Se há conexão com a internet para o 'webdriver-manager' baixar o driver.
            3. Permissões de execução na pasta onde o driver será salvo (.wdm/drivers).
            4. A versão do Chrome pode ser incompatível com o driver baixado.
            5. Verifique seu firewall/antivírus para bloqueios de conexão (Erro 10061).
            6. Verifique se não há um servidor IIS ou proxy redirecionando 'sponteweb.com.br' localmente (Erro 404.0).
        """)
        return False
    except Exception as e:
        st.error(f"Erro inesperado ao verificar o driver: {str(e)}")
        return False


# --- CONFIGURAÇÃO INICIAL DO APP (EXECUTA UMA VEZ NA INICIALIZAÇÃO) ---
ROOT = Path(__file__).resolve().parent

# Executa as verificações iniciais de dependências Python
if not verificar_dependencias():
    st.stop()

# Inicializa o sistema (verifica/cria DB, insere dados de teste se vazio)
def inicializar_sistema_app():
    try:
        data_dir = ROOT / "data"
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Pasta 'data' criada em: {data_dir}")

        db_path = data_dir / "escola.db"
        
        # Cria DB se não existe ou está vazio
        if not db_path.exists() or Path(db_path).stat().st_size == 0:
            st.warning("Banco de dados 'escola.db' não encontrado ou vazio. Criando estrutura e dados iniciais...")
            if not setup_database():
                st.error("Falha ao criar o banco de dados. Verifique os logs.")
                st.stop()
            else:
                st.success("Banco de dados criado com sucesso!")
        
        # Garante que as tabelas estejam setup (chamada mesmo se DB já existe)
        setup_database()

        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM alunos")
            if cur.fetchone()[0] == 0:
                st.info("Nenhum aluno no banco de dados. Inserindo dados de teste...")
                # A função setup_database() já cuida de inserir os dados de teste
                setup_database()
                st.success("Dados de teste inseridos!")
        finally:
            if conn: conn.close()
            
    except Exception as e:
        st.error(f"Falha na inicialização do sistema: {str(e)}")
        st.stop()

inicializar_sistema_app() # Chama a função de inicialização do sistema

# Carrega config.toml
try:
    CFG = toml.load(ROOT / "config.toml")
    NOME_ESCOLA = CFG.get("whatsapp", {}).get("escola", "a Escola")
    CATEGORIAS_JUSTIFICATIVAS = CFG.get("categorias", {})
except FileNotFoundError:
    st.error("O ficheiro 'config.toml' não foi encontrado! Por favor, crie-o na raiz do projeto.")
    st.stop()
except Exception as e:
    st.error(f"Erro ao carregar 'config.toml': {str(e)}")
    st.stop()

# --- CONFIGURAÇÃO DA PÁGINA STREAMLIT E AUTENTICAÇÃO ---
st.set_page_config(layout="wide", page_title="Assistente de Chamada")

# --- AUTENTICAÇÃO MANUAL BÁSICA (Substitui streamlit_authenticator) ---
# Usamos st.session_state para gerenciar o estado de autenticação.
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None

# Lógica da interface de login
if st.session_state['authentication_status'] is None:
    st.subheader("Login")
    username_input = st.text_input("Usuário", key="login_username")
    password_input = st.text_input("Senha", type="password", key="login_password")

    login_button = st.button("Entrar", type="primary", key="login_button")

    if login_button:
        try:
            credentials = st.secrets.get("credentials", {}).get("usernames", {})
            username_input = st.session_state.get("login_username", "")
            password_input = st.session_state.get("login_password", "")

            if username_input in credentials:
                stored_password_hash = credentials[username_input]["password"]

                # --- VERIFICAÇÃO DE SENHA APENAS COM BCRYPT (MAIS SEGURO) ---
                # Garante que a senha armazenada é uma string e parece um hash bcrypt
                if isinstance(stored_password_hash, str) and stored_password_hash.startswith('$2b$'):
                    # A verificação só pode acontecer com bcrypt.
                    if bcrypt.checkpw(password_input.encode('utf-8'), stored_password_hash.encode('utf-8')):
                        st.session_state['authentication_status'] = True
                        st.session_state['name'] = credentials[username_input]["name"]
                        st.session_state['username'] = username_input
                        st.success(f"Bem-vindo, {st.session_state['name']}!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        # Senha incorreta
                        st.error("Usuário ou senha incorretos.")
                        st.session_state['authentication_status'] = False
                else:
                    # Se a senha não for um hash válido, o login deve falhar por segurança.
                    st.error("Erro de configuração de segurança: A senha para este usuário não está armazenada de forma segura. Contate o administrador.")
                    st.session_state['authentication_status'] = False
            else:
                # Usuário não encontrado
                st.error("Usuário ou senha incorretos.")
                st.session_state['authentication_status'] = False

        except KeyError as ke:
            st.error(f"Erro de configuração: Credenciais ausentes em 'secrets.toml' para o usuário '{username_input}' ou seção 'credentials'.")
            st.session_state['authentication_status'] = False
        except Exception as e:
            st.error(f"Erro inesperado na autenticação: {str(e)}")
            st.session_state['authentication_status'] = False
elif st.session_state['authentication_status'] is False:
    st.error('Nome de utilizador ou senha incorretos.')
    # Após erro, resetamos para None para que o formulário de login apareça novamente
    st.session_state['authentication_status'] = None 
    time.sleep(0.5)
    st.rerun() 

# --- LÓGICA PRINCIPAL DO APP APÓS LOGIN BEM-SUCEDIDO ---
# Este bloco só será executado se authentication_status for True
if st.session_state['authentication_status'] == True:
    st.sidebar.title(f"👨‍🏫 Bem-vindo, {st.session_state['name']}!")

    # Botão de Logout manual
    if st.sidebar.button('Sair'):
        st.session_state['authentication_status'] = None
        st.session_state['name'] = None
        st.session_state['username'] = None
        st.info("Você saiu com sucesso.")
        time.sleep(0.5)
        st.rerun()

    st.sidebar.divider()

    professor_logado = st.session_state['name']

    # Menu principal
    pagina = st.sidebar.radio(
        "Escolha uma ferramenta:",
        ["Realizar Chamada", "Gestão Individual", "Dashboard de Análise", "Relatórios e Ferramentas", "Scraper Sponte"]
    )

    # Painel de faltas do dia
    if 'ausentes_do_dia' not in st.session_state:
        st.session_state.ausentes_do_dia = {}

    if st.sidebar.button("🗑️ Iniciar Novo Dia (Limpar Painel)"):
        st.session_state.ausentes_do_dia = {}
        st.sidebar.success("Painel de faltas do dia foi limpo!")

    st.sidebar.divider()
    st.sidebar.subheader("☎️ Painel de Faltas do Dia")
    df_base_alunos, msg = carregar_alunos_db()

    if not st.session_state.ausentes_do_dia:
        st.sidebar.write("Nenhum aluno ausente registado hoje.")
    else:
        ausentes_items = list(st.session_state.ausentes_do_dia.items())
        for aluno, dados in ausentes_items:
            ligacao_feita = st.sidebar.checkbox(
                f"~~{aluno}~~" if dados["ligacao"] else aluno,
                value=dados["ligacao"],
                key=f"check_{aluno}"
            )
            st.session_state.ausentes_do_dia[aluno]["ligacao"] = ligacao_feita

            justificativa = st.sidebar.text_input(
                "Justificativa:",
                value=dados.get("justificativa", ""),
                key=f"just_{aluno}",
                placeholder="Motivo da falta..."
            )
            st.session_state.ausentes_do_dia[aluno]["justificativa"] = justificativa
            st.sidebar.markdown("---")

        if st.sidebar.button("💾 Salvar Justificativas no BD", type="primary"):
            with st.spinner("A salvar..."):
                for aluno, dados in st.session_state.ausentes_do_dia.items():
                    if dados.get('id'):
                        sucesso, erro = salvar_justificativa_db(
                            dados['id'],
                            date.today(),
                            dados['justificativa'],
                            professor_logado,
                            dados['ligacao']
                        )
                        if not sucesso:
                            st.sidebar.error(f"Erro ao salvar para {aluno}: {erro}")
            st.sidebar.success("Justificativas salvas!")
            time.sleep(1)
            st.rerun()

    st.sidebar.divider()
    st.sidebar.info(msg)

    # --- PÁGINAS PRINCIPAIS ---
    if pagina == "Realizar Chamada":
        try:
            xls_horarios = carregar_horarios()
            if xls_horarios:
                pagina_chamada(xls_horarios, df_base_alunos, professor_logado)
        except Exception as e:
            st.error(f"Erro ao carregar horários: {e}")

    elif pagina == "Gestão Individual":
        st.divider()
        st.subheader("Atualização Manual de Status")

        alunos_df, _ = carregar_alunos_db()
        # Garante que a lista de alunos não esteja vazia para evitar erros no selectbox
        if alunos_df.empty:
            st.warning("Não há alunos carregados na base de dados.")
        else:
            lista_alunos = alunos_df['nome'].tolist()

            aluno_selecionado = st.selectbox("Selecione o aluno:", lista_alunos)
            novo_status = st.radio("Novo status:", ("Presente", "Faltou"), key="status_radio")

            if st.button("Atualizar Status"):
                conn = None  # Inicializa a conexão como None
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    status_db = "P" if novo_status == "Presente" else "F"

                    # FORMA CORRETA E SEGURA com placeholders
                    cursor.execute("""
                        UPDATE chamadas
                        SET status = ?
                        WHERE aluno_id = (SELECT id FROM alunos WHERE nome = ?)
                        AND data = date('now')
                    """, (status_db, aluno_selecionado))

                    conn.commit()
                    # Verifica se alguma linha foi de fato atualizada
                    if cursor.rowcount > 0:
                        st.success(f"Status de {aluno_selecionado} atualizado para {novo_status}!")
                    else:
                        st.warning(f"Nenhum registo de chamada encontrado para {aluno_selecionado} na data de hoje. Nenhuma alteração foi feita.")

                except Exception as e:
                    st.error(f"Erro ao atualizar: {str(e)}")
                finally:
                    # Garante que a conexão seja sempre fechada, mesmo se ocorrer um erro
                    if conn:
                        conn.close()

        # Chama a página de gestão individual, garantindo que df_base_alunos foi definido
        pagina_gestao_individual(df_base_alunos, professor_logado)

    elif pagina == "Relatórios e Ferramentas":
        try:
            pagina_relatorios()
        except Exception as e:
            st.error(f"Erro ao gerar relatórios: {e}")

    elif pagina == "Scraper Sponte": # Nova página dedicada ao Scraper
        st.subheader("Ferramenta de Scraping do Sponte")
        st.write("Aqui você pode executar o scraper para obter dados atualizados do Sponte.")
        
        if verificar_credenciais_sponte(): # Reutiliza a função de verificação
            credenciais = {
                "username": st.secrets["SPONTE"]["username"],
                "password": st.secrets["SPONTE"]["password"]
            }
        else:
            st.stop()

        if st.button("Executar Scraper Sponte Agora", type="primary"):
            with st.spinner("Conectando ao Sponte e coletando dados... Isso pode levar alguns minutos."):
                if not verificar_driver_local(): # Chama a função de verificação do driver
                    st.error("Scraper não pode ser executado sem um ChromeDriver funcional.")
                else:
                    try:
                        resultado = executar_scraper_sponte(credenciais)
                        if resultado['sucesso']:
                            st.success(f"Scraper do Sponte executado com sucesso! Encontrados {len(resultado['alunos'])} alunos.")
                            if resultado['alunos']:
                                st.subheader("Alunos encontrados:")
                                st.json(resultado['alunos'])
                            else:
                                st.info("Nenhum aluno encontrado.")
                        else:
                            st.error(f"Falha ao executar scraper do Sponte: {resultado['mensagem']}")
                            if "Timeout" in resultado['mensagem']:
                                st.info("Verifique sua conexão de internet ou tente novamente mais tarde. O Sponte pode estar lento.")

                    except TimeoutException:
                        st.error("Timeout ao acessar o Sponte. O processo demorou demais.")
                    except WebDriverException as e:
                        st.error(f"Erro no WebDriver durante o scraping: {str(e)}")
                        st.info("O navegador pode ter fechado inesperadamente ou houve um problema de comunicação.")
                    except Exception as e:
                        show_error(f"Erro inesperado ao executar o scraper do Sponte: {e}")
        st.info("O scraper abre uma janela invisível do navegador Chrome para coletar os dados.")

    else: # Dashboard Principal (Se nenhuma das opções acima for selecionada)
        try:
            pagina_dashboard(CATEGORIAS_JUSTIFICATIVAS)
        except Exception as e:
            st.error(f"Erro no dashboard: {e}")

# A função main para execução direta (não usada pelo Streamlit, mas boa prática)
if __name__ == "__main__":
    pass