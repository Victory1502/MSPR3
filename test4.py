import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        port=15432,  # <-- Attention au port !
        database="mspr3",
        user="admin",
        password="admin123"
    )
    print("Connexion OK")
    conn.close()
except Exception as e:
    print("Erreur:", e)