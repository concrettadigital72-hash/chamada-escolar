# Em scripts/sponte_scraper.py

import streamlit as st
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
from typing import Tuple, List, Dict, Any
from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('webdriver_manager').setLevel(logging.WARNING)

# Constantes
MAX_ATTEMPTS = 3  # Número máximo de tentativas

@st.cache_resource(ttl=86400)
def configurar_driver() -> webdriver.Chrome:
    """
    Configura e inicializa o WebDriver do Chrome de forma mais robusta, com tentativas.
    """
    attempt = 0
    while attempt < MAX_ATTEMPTS:
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920x1080")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")

            servico = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=servico, options=chrome_options)
            
            driver.set_page_load_timeout(60)
            
            logging.info(f"✅ Tentativa {attempt + 1}: WebDriver configurado com sucesso.")
            return driver

        except Exception as e:
            attempt += 1
            logging.error(f"❌ Tentativa {attempt}/{MAX_ATTEMPTS} falhou: {e}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(3)
            else:
                st.error("Falha ao configurar o WebDriver após múltiplas tentativas.")
                raise
    return None

def buscar_alunos_sponte(username: str, password: str) -> Tuple[bool, List[str] | str]:
    """
    Realiza o scraping do Sponte Web para obter lista de alunos.
    """
    driver = None  # Inicializa o driver como None
    try:
        driver = configurar_driver()
        if not driver:
            return False, "Não foi possível iniciar o navegador."
            
        logging.info("Acessando portal Sponte...")
        driver.get("https://www.sponteweb.com.br/Default.aspx")
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "txtLogin"))
        ).send_keys(username)
        
        driver.find_element(By.ID, "txtSenha").send_keys(password)
        driver.find_element(By.ID, "btnok").click()
        
        try:
            WebDriverWait(driver, 45).until(
                EC.url_contains("Home.aspx")
            )
            logging.info("Login realizado com sucesso.")
        except TimeoutException:
            current_url = driver.current_url
            logging.warning(f"Tempo limite de login excedido. URL atual: {current_url}")
            try:
                error_message_element = driver.find_element(By.CLASS_NAME, "erro_login_msg")
                error_text = error_message_element.text
                return False, f"Falha no login: {error_text}"
            except NoSuchElementException:
                return False, "Tempo limite excedido. Verifique credenciais e conexão."
        
        logging.info("Acessando lista de alunos...")
        driver.get("https://www.sponteweb.com.br/SPCad/Alunos.aspx")
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_tab_tabGrid_grdAlunos"))
        )
        
        tabela = driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_tab_tabGrid_grdAlunos")
        linhas = tabela.find_elements(By.TAG_NAME, "tr")[1:]
        
        alunos = []
        for linha in linhas:
            celulas = linha.find_elements(By.TAG_NAME, "td")
            if len(celulas) > 1:
                nome_aluno = celulas[1].text.strip()
                if nome_aluno:
                    alunos.append(nome_aluno)
        
        logging.info(f"Encontrados {len(alunos)} alunos.")
        return True, sorted(alunos)
            
    except TimeoutException as e:
        error_msg = f"Tempo limite excedido: {str(e)}"
        logging.error(error_msg)
        return False, error_msg
    except WebDriverException as e:
        error_msg = f"Erro no WebDriver: {str(e)}"
        logging.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Erro inesperado: {str(e)}"
        logging.error(error_msg)
        return False, error_msg
    finally:
        if driver:
            driver.quit()

def executar_scraper_sponte(credenciais: Dict[str, str]) -> Dict[str, Any]:
    """
    Função principal para realizar scraping completo do sistema Sponte.
    """
    resultado = {
        'sucesso': False,
        'alunos': [],
        'frequencias': [],
        'mensagem': '',
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        status, dados = buscar_alunos_sponte(
            credenciais['username'],
            credenciais['password']
        )
        
        if status:
            resultado['sucesso'] = True
            resultado['alunos'] = dados
        else:
            resultado['mensagem'] = dados
            
    except Exception as e:
        error_msg = f"Erro inesperado ao executar o scraper principal: {str(e)}"
        logging.error(error_msg)
        resultado['mensagem'] = error_msg
    
    return resultado

if __name__ == "__main__":
    print("Iniciando teste de sponte_scraper...")
    
    # Adicione suas credenciais de teste para executar o teste localmente
    # Cuidado: Não envie suas credenciais para o modelo!
    test_credenciais = {"username": "SEU_USUARIO_SPONTE", "password": "SUA_SENHA_SPONTE"}
    
    if test_credenciais["username"] != "SEU_USUARIO_SPONTE":
        scraper_result = executar_scraper_sponte(test_credenciais)
        print(f"Resultado do Scraper: {scraper_result}")
    else:
        print("Pulei o teste do scraper Sponte pois as credenciais de teste são placeholders.")