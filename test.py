from sqlalchemy import create_engine, inspect, text

# Connexion à la base de données PostgreSQL
engine = create_engine('postgresql+psycopg2://admin:admin123@localhost:15432/mspr3')

# Inspection des schémas
inspector = inspect(engine)
print(inspector.get_schema_names())

# Liste des tables du schéma 'public'
tables = inspector.get_table_names(schema='public')
print(tables)

# Exécution d'une requête SQL (compatible SQLAlchemy 2.0)
with engine.connect() as connection:
    result = connection.execute(text("SELECT * FROM dim_villes LIMIT 5"))
    for row in result:
        print(row)


    result = connection.execute(text("SELECT COUNT(*) FROM dim_villes"))
    print(result.scalar())  # Affiche le nombre de lignes

