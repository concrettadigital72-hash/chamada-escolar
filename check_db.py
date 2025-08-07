# Em check_db.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "escola.db"

if not DB_PATH.exists():
    print(f"❌ ERRO: O arquivo da base de dados não foi encontrado em '{DB_PATH}'")
    print("➡️ Execute 'python database_setup.py' primeiro.")
else:
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("--- Verificando a Base de Dados ---")

        # Verifica a tabela de alunos
        cursor.execute("SELECT count(*) FROM alunos")
        num_alunos = cursor.fetchone()[0]
        print(f"✅ Tabela 'alunos': {num_alunos} registos encontrados.")

        # Verifica a tabela de chamadas
        cursor.execute("SELECT count(*) FROM chamadas")
        num_chamadas = cursor.fetchone()[0]
        print(f"✅ Tabela 'chamadas': {num_chamadas} registos encontrados.")

        print("---------------------------------")

        if num_chamadas == 0:
            print("⚠️ AVISO: A base de dados está pronta, mas vazia.")
            print("➡️ Para popular com seus dados históricos, execute 'python migrate_to_db.py'")
        else:
            print("🎉 SUCESSO: Sua base de dados contém os dados de chamadas!")

    except Exception as e:
        print(f"❌ ERRO ao conectar ou ler a base de dados: {e}")
    finally:
        if conn:
            conn.close()