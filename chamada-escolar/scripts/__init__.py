# scripts/__init__.py

# Importa funções que serão diretamente acessíveis via 'from scripts import funcao'
# Ou importadas pelos outros módulos dentro de 'scripts'
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
)

from .ui_pages import (
    pagina_chamada,
    pagina_gestao_individual,
    pagina_dashboard
)

from .ui_reports import pagina_relatorios

from .analysis import (
    detectar_padroes_de_falta,
    gerar_ranking_faltas,
    gerar_grafico_calendario,
    gerar_grafico_top_faltas,
    gerar_resumo_estatistico
)

from .reports import (
    gerar_relatorio_excel_completo
)

from .sponte_scraper import (
    configurar_driver,
    executar_scraper_sponte,
    buscar_alunos_sponte
)