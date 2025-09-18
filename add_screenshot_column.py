from sqlalchemy import create_engine, text
from db.base import engine

def add_screenshot_column():
    try:
        # Conecta ao banco de dados
        conn = engine.connect()
        
        # Verifica se a coluna já existe
        result = conn.execute(text("PRAGMA table_info(cameras)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'screenshot_base64' not in columns:
            print("Adicionando coluna screenshot_base64 à tabela cameras...")
            conn.execute(text("ALTER TABLE cameras ADD COLUMN screenshot_base64 TEXT"))
            print("Coluna adicionada com sucesso!")
        else:
            print("A coluna screenshot_base64 já existe na tabela cameras.")
        
        conn.close()
        
    except Exception as e:
        print(f"Erro ao adicionar coluna: {e}")

if __name__ == "__main__":
    add_screenshot_column()
