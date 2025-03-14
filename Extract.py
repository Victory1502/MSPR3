import psycopg2
import pandas as pd
from tabulate import tabulate
import matplotlib.pyplot as plt
import seaborn as sns
from io import StringIO
import os
from datetime import datetime

# Configuration PostgreSQL
pg_config = {
    "host": "localhost",
    "port": 15432,
    "database": "mspr3",
    "user": "admin",
    "password": "admin123"
}

# Requêtes SQL avec titres
queries = [
    {
        "title": "LISTE DES VILLES ENREGISTRÉES",
        "query": """
        SELECT nom, latitude, longitude FROM villes
        ORDER BY nom;
        """
    },
    {
        "title": "NOMBRE TOTAL DE VILLES DANS LA BASE",
        "query": """
        SELECT COUNT(*) AS nombre_villes FROM villes;
        """
    },
    {
        "title": "CONDITIONS MÉTÉOROLOGIQUES ACTUELLES",
        "query": """
        SELECT v.nom AS ville, 
               ROUND(m.temperature::numeric, 1) AS temperature_celsius,
               ROUND(m.temperature_ressentie::numeric, 1) AS ressenti,
               m.humidite AS humidite_pct,
               m.description_meteo AS conditions
        FROM meteo m
        JOIN villes v ON m.ville_id = v.id
        ORDER BY v.nom;
        """
    },
    {
        "title": "INDICES DE QUALITÉ DE L'AIR PAR VILLE",
        "query": """
        SELECT v.nom AS ville, 
               qa.aqi AS indice_qualite_air, 
               qa.polluant_dominant,
               CASE 
                   WHEN qa.aqi <= 50 THEN 'Bon'
                   WHEN qa.aqi <= 100 THEN 'Modéré'
                   WHEN qa.aqi <= 150 THEN 'Mauvais pour groupes sensibles'
                   WHEN qa.aqi <= 200 THEN 'Mauvais'
                   WHEN qa.aqi <= 300 THEN 'Très mauvais'
                   ELSE 'Dangereux'
               END AS qualification
        FROM qualite_air qa
        JOIN villes v ON qa.ville_id = v.id
        ORDER BY qa.aqi;
        """
    },
    {
        "title": "PRÉVISIONS DE QUALITÉ DE L'AIR (PM2.5) POUR LES PROCHAINS JOURS",
        "query": """
        SELECT v.nom AS ville, 
               pqa.date_prevision, 
               pqa.valeur_moyenne AS pm25_moyen,
               pqa.valeur_max AS pm25_max
        FROM previsions_qualite_air pqa
        JOIN villes v ON pqa.ville_id = v.id
        WHERE pqa.date_prevision >= CURRENT_DATE
        AND pqa.type_polluant = 'pm25'
        ORDER BY v.nom, pqa.date_prevision;
        """
    },
    {
        "title": "TOP 5 DES VILLES AVEC LA MEILLEURE QUALITÉ D'AIR",
        "query": """
        SELECT v.nom AS ville, qa.aqi AS indice_qualite_air,
               qa.polluant_dominant
        FROM qualite_air qa
        JOIN villes v ON qa.ville_id = v.id
        ORDER BY qa.aqi ASC
        LIMIT 5;
        """
    },
    {
        "title": "TOP 5 DES VILLES AVEC LA QUALITÉ D'AIR LA PLUS DÉGRADÉE",
        "query": """
        SELECT v.nom AS ville, qa.aqi AS indice_qualite_air,
               qa.polluant_dominant
        FROM qualite_air qa
        JOIN villes v ON qa.ville_id = v.id
        ORDER BY qa.aqi DESC
        LIMIT 5;
        """
    },
    {
        "title": "CONCENTRATION DE POLLUANTS PAR VILLE (PM2.5, PM10, O3, NO2)",
        "query": """
        SELECT v.nom AS ville, 
               qa.pm25, 
               qa.pm10, 
               qa.o3 AS ozone, 
               qa.no2 AS dioxyde_azote
        FROM qualite_air qa
        JOIN villes v ON qa.ville_id = v.id
        ORDER BY v.nom;
        """
    },
    {
        "title": "RAPPORT DE CORRÉLATION TEMPÉRATURE/QUALITÉ DE L'AIR",
        "query": """
        SELECT v.nom AS ville,
               ROUND(AVG(m.temperature)::numeric, 1) AS temperature_moyenne,
               AVG(qa.aqi) AS aqi_moyen,
               ROUND(CORR(m.temperature, qa.aqi)::numeric, 2) AS correlation
        FROM villes v
        JOIN meteo m ON v.id = m.ville_id
        JOIN qualite_air qa ON v.id = qa.ville_id
        GROUP BY v.nom
        ORDER BY correlation DESC;
        """
    },
    {
        "title": "COMPARAISON DES CONDITIONS MÉTÉO ENTRE VILLES",
        "query": """
        SELECT v.nom AS ville, 
               ROUND(m.temperature::numeric, 1) AS temperature,
               m.humidite,
               m.pression,
               ROUND(m.vitesse_vent::numeric, 1) AS vitesse_vent,
               m.nuages_pourcentage
        FROM meteo m
        JOIN villes v ON m.ville_id = v.id
        ORDER BY m.temperature DESC;
        """
    }
]

def execute_query_to_df(conn, query):
    """Exécute une requête SQL et retourne un DataFrame pandas"""
    return pd.read_sql_query(query, conn)

def create_report():
    """Génère un rapport avec tous les résultats"""
    try:
        # Connexion à PostgreSQL
        conn = psycopg2.connect(**pg_config)
        print("Connexion à PostgreSQL réussie")
        
        # Créer un dossier pour les rapports dans l'emplacement spécifié
        report_dir = r"C:\Users\lucas\OneDrive\Desktop\EPSI\MSPR BLOC 3\MSPR3\Files"
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
        
        # Nom du fichier de rapport avec horodatage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(report_dir, f"rapport_meteo_{timestamp}.txt")
        
        # Créer le rapport
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=================================================================\n")
            f.write("                RAPPORT MÉTÉO ET QUALITÉ DE L'AIR                \n")
            f.write("=================================================================\n")
            f.write(f"Date de génération: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            # Exécuter chaque requête et écrire les résultats dans le fichier
            for item in queries:
                title = item["title"]
                query = item["query"]
                
                # Exécution de la requête
                df = execute_query_to_df(conn, query)
                
                # Ajout du titre et des résultats au rapport
                f.write(f"\n{'=' * 65}\n")
                f.write(f"{title.center(65)}\n")
                f.write(f"{'=' * 65}\n\n")
                
                # Utiliser tabulate pour formater le tableau
                table = tabulate(df, headers=df.columns, tablefmt="grid", showindex=False)
                f.write(table)
                f.write("\n\n")
            
            f.write("\n=================================================================\n")
            f.write("                        FIN DU RAPPORT                          \n")
            f.write("=================================================================\n")
            
        print(f"Rapport généré avec succès: {report_file}")
        
        # Génération d'un graphique pour la qualité de l'air
        df_aqi = execute_query_to_df(conn, """
            SELECT v.nom AS ville, qa.aqi AS indice_qualite_air
            FROM qualite_air qa
            JOIN villes v ON qa.ville_id = v.id
            ORDER BY qa.aqi;
        """)
        
        plt.figure(figsize=(12, 6))
        sns.barplot(x='ville', y='indice_qualite_air', data=df_aqi)
        plt.title('Indice de qualité de l\'air par ville')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Sauvegarder le graphique
        graph_file = os.path.join(report_dir, f"graphique_qualite_air_{timestamp}.png")
        plt.savefig(graph_file)
        print(f"Graphique généré avec succès: {graph_file}")
        
        # Fermeture de la connexion
        conn.close()
        
        return report_file
        
    except psycopg2.Error as e:
        print(f"Erreur PostgreSQL: {e}")
    except Exception as e:
        print(f"Erreur inattendue: {e}")

if __name__ == "__main__":
    report_file = create_report()
    
    # Affichage d'un extrait du rapport dans le terminal
    if report_file and os.path.exists(report_file):
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print("\nExtrait du rapport:")
            print(content[:1000] + "...\n")
            print(f"Rapport complet disponible dans le fichier: {report_file}")