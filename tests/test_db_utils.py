# Em tests/test_db_utils.py

import pytest
from scripts.db_utils import classificar_justificativa

# 1. Definir as categorias de exemplo que seriam carregadas do config.toml
#    Isto simula a configuração real da sua aplicação para os testes.
@pytest.fixture
def categorias_config():
    """Um pytest fixture que fornece uma configuração de categorias para os testes."""
    return {
        "motivo_saude": ["médico", "doente", "hospital", "dentista", "mal", "passando mal"],
        "motivo_pessoal": ["problema pessoal", "familiar", "resolvendo"],
        "motivo_transporte": ["ônibus", "onibus", "trânsito", "carro quebrou"],
        "outros": []
    }

# 2. Escrever os testes para a função `classificar_justificativa`

def test_classificar_justificativa_saude(categorias_config):
    """Verifica se justificativas relacionadas à saúde são classificadas corretamente."""
    assert classificar_justificativa("Faltou porque foi ao médico", categorias_config) == "Saude"
    assert classificar_justificativa("Não veio pois estava passando mal", categorias_config) == "Saude"
    assert classificar_justificativa("Atestado de dentista", categorias_config) == "Saude"

def test_classificar_justificativa_pessoal(categorias_config):
    """Verifica se justificativas pessoais são classificadas corretamente."""
    assert classificar_justificativa("Teve um problema pessoal hoje.", categorias_config) == "Pessoal"
    assert classificar_justificativa("Precisei ficar para resolver um assunto familiar", categorias_config) == "Pessoal"

def test_classificar_justificativa_transporte(categorias_config):
    """Verifica se justificativas de transporte são classificadas corretamente."""
    assert classificar_justificativa("Perdeu o ônibus", categorias_config) == "Transporte"
    assert classificar_justificativa("O carro quebrou no caminho", categorias_config) == "Transporte"

def test_classificar_justificativa_outros(categorias_config):
    """Verifica se justificativas não mapeadas caem em 'Outros'."""
    assert classificar_justificativa("Dormiu demais e perdeu a hora", categorias_config) == "Outros"
    assert classificar_justificativa("Simplesmente não veio.", categorias_config) == "Outros"

def test_classificar_justificativa_texto_vazio_ou_na(categorias_config):
    """Verifica o comportamento com entradas vazias ou nulas."""
    assert classificar_justificativa("", categorias_config) == "Outros"
    assert classificar_justificativa(None, categorias_config) == "Não Especificado"