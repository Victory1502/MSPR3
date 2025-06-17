import matplotlib.pyplot as plt
import json
import pandas as pd
from datetime import datetime, timedelta

def create_ml_dashboard():
    """Crée un dashboard des prédictions ML"""
    
    # Lecture des prédictions
    try:
        with open('/opt/airflow/project/ml_predictions.json', 'r') as f:
            predictions = [json.loads(line) for line in f]
    except:
        print("Aucune prédiction disponible")
        return
    
    df = pd.DataFrame(predictions)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Graphique des prédictions
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 2, 1)
    plt.plot(df['timestamp'], df['predicted_duration'])
    plt.title('Durée Prédite du Pipeline')
    plt.ylabel('Secondes')
    plt.xticks(rotation=45)
    
    plt.subplot(2, 2, 2)
    plt.bar(df['optimal_time'].value_counts().index, df['optimal_time'].value_counts().values)
    plt.title('Heures Optimales Recommandées')
    plt.xlabel('Heure')
    plt.ylabel('Fréquence')
    
    plt.subplot(2, 2, 3)
    plt.plot(df['timestamp'], df['confidence_level'])
    plt.title('Niveau de Confiance')
    plt.ylabel('Confiance')
    plt.xticks(rotation=45)
    
    plt.subplot(2, 2, 4)
    # Heatmap des performances par heure
    current_hour = datetime.now().hour
    hours = list(range(24))
    colors = ['red' if h == current_hour else 'blue' for h in hours]
    plt.bar(hours, [1]*24, color=colors, alpha=0.6)
    plt.title('Charge Prédite par Heure (Rouge = Maintenant)')
    plt.xlabel('Heure')
    
    plt.tight_layout()
    plt.savefig('/opt/airflow/project/ml_dashboard.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("Dashboard ML généré: ml_dashboard.png")

if __name__ == "__main__":
    create_ml_dashboard()