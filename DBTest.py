import psycopg2

try:
    # Connexion à la base de données PostgreSQL
    connection = psycopg2.connect(
        host="localhost",
        port=15432,
        database="mspr3",
        user="admin",
        password="admin123"
    )
    print("Connexion réussie !")

    # Exemple d'exécution d'une requête SQL
    cursor = connection.cursor()
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print("Version de PostgreSQL :", db_version)

    # Fermeture du curseur et de la connexion
    cursor.close()
    connection.close()

except Exception as e:
    print("Erreur lors de la connexion :", e)
