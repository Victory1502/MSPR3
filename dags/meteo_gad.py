from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator
from airflow.operators.bash import BashOperator
import sys
import os
import json
import time

sys.path.append('/opt/airflow/project') 

from extract import extract_and_store
from transform import retrieve_and_display_complete
from Load import load

# =====================================
# NOUVELLES FONCTIONS ML
# =====================================

def ml_pipeline_optimization(**context):
    """Fonction d'optimisation ML du pipeline"""
    print("🤖 Démarrage de l'optimisation ML du pipeline")
    
    try:
        # Import du module ML
        from ml_predictor import PipelineLoadPredictor
        import pandas as pd
        import numpy as np
        
        predictor = PipelineLoadPredictor()
        
        # Simulation de données d'entraînement basées sur votre contexte GoodAir
        print("📊 Génération des données d'entraînement...")
        np.random.seed(42)
        n_samples = 150
        
        # Simulation réaliste pour un laboratoire de recherche
        historical_data = pd.DataFrame({
            'hour': np.random.randint(0, 24, n_samples),
            'day_of_week': np.random.randint(0, 7, n_samples),
            'cpu_usage': np.random.normal(25, 8, n_samples),  # Usage CPU modéré
            'memory_usage': np.random.normal(35, 12, n_samples),  # Usage RAM modéré
            'active_connections': np.random.randint(5, 50, n_samples),  # 10 chercheurs max
            'disk_io_read': np.random.randint(500000, 5000000, n_samples),
            'disk_io_write': np.random.randint(200000, 2000000, n_samples),
            'duration_seconds': np.random.normal(120, 45, n_samples)  # 2 min ± 45s
        })
        
        # Patterns réalistes pour GoodAir
        # Nuits (22h-6h) : plus rapide (moins de chercheurs)
        night_mask = (historical_data['hour'] >= 22) | (historical_data['hour'] <= 6)
        historical_data.loc[night_mask, 'duration_seconds'] *= 0.6
        
        # Heures de bureau (8h-18h) : plus lent (chercheurs actifs)
        work_mask = (historical_data['hour'] >= 8) & (historical_data['hour'] <= 18)
        historical_data.loc[work_mask, 'duration_seconds'] *= 1.4
        
        # Weekends : plus rapide (moins d'activité)
        weekend_mask = historical_data['day_of_week'].isin([5, 6])
        historical_data.loc[weekend_mask, 'duration_seconds'] *= 0.8
        
        # Entraînement du modèle
        print("🧠 Entraînement du modèle ML...")
        success = predictor.train_model(historical_data)
        
        if success:
            # Prédiction pour l'exécution actuelle
            prediction = predictor.predict_pipeline_duration()
            
            if prediction:
                print("="*60)
                print("🎯 RÉSULTATS DE PRÉDICTION ML - GOODAIR")
                print("="*60)
                print(f"⏱️  Durée prédite: {prediction['predicted_duration']:.1f} secondes")
                print(f"🕐 Heure optimale: {prediction['optimal_time']}h00")
                print(f"📊 Niveau de confiance: {prediction['confidence_level']:.2%}")
                print(f"🔍 Recommandation: {'Exécution immédiate OK' if prediction['predicted_duration'] < 180 else 'Reporter à une heure creuse'}")
                print("="*60)
                
                # Sauvegarde des prédictions
                prediction_log = {
                    **prediction,
                    'execution_date': context['ds'],
                    'dag_run_id': context['dag_run'].dag_id
                }
                
                os.makedirs('/opt/airflow/project/ml_logs', exist_ok=True)
                with open('/opt/airflow/project/ml_logs/predictions.json', 'a') as f:
                    json.dump(prediction_log, f, default=str)
                    f.write('\n')
                
                # Contexte pour les tâches suivantes
                context['task_instance'].xcom_push(key='ml_prediction', value=prediction)
                
                # Alerte si surcharge prédite
                if prediction['predicted_duration'] > 240:  # > 4 minutes
                    print("⚠️  ALERTE: Surcharge du pipeline prédite!")
                    print("💡 Conseil: Programmer l'exécution à une heure creuse")
                    return "ALERT_HIGH_LOAD"
                elif prediction['predicted_duration'] < 90:  # < 1.5 minutes
                    print("✅ Conditions optimales détectées pour l'exécution")
                    return "OPTIMAL_CONDITIONS"
                    
            return "ML_SUCCESS"
        else:
            print("❌ Échec de l'entraînement du modèle ML")
            return "ML_TRAINING_FAILED"
            
    except Exception as e:
        print(f"❌ Erreur dans l'optimisation ML: {str(e)}")
        return "ML_ERROR"

def enhanced_extract_with_monitoring(**context):
    """Extraction avec monitoring des performances"""
    start_time = datetime.now()
    print(f"🚀 Démarrage de l'extraction - {start_time}")
    
    try:
        # Récupération de la prédiction ML
        ml_prediction = context['task_instance'].xcom_pull(task_ids='ml_optimization', key='ml_prediction')
        if ml_prediction:
            print(f"🤖 Durée prédite par ML: {ml_prediction['predicted_duration']:.1f}s")
        
        # Exécution de l'extraction normale
        extract_and_store()
        
        end_time = datetime.now()
        actual_duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Extraction terminée - Durée réelle: {actual_duration:.1f}s")
        
        # Comparaison avec la prédiction
        if ml_prediction:
            predicted_duration = ml_prediction['predicted_duration']
            accuracy = 1 - abs(actual_duration - predicted_duration) / predicted_duration
            print(f"🎯 Précision ML: {accuracy:.2%}")
            
            # Log des performances pour améliorer le modèle
            performance_log = {
                'task': 'extract',
                'predicted_duration': predicted_duration,
                'actual_duration': actual_duration,
                'accuracy': accuracy,
                'timestamp': start_time.isoformat(),
                'system_load': get_system_metrics()
            }
            
            with open('/opt/airflow/project/ml_logs/performance.json', 'a') as f:
                json.dump(performance_log, f, default=str)
                f.write('\n')
        
        return "EXTRACT_SUCCESS"
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"❌ Erreur lors de l'extraction après {duration:.1f}s: {str(e)}")
        raise

def enhanced_transform_with_monitoring(**context):
    """Transformation avec monitoring des performances"""
    start_time = datetime.now()
    print(f"🔄 Démarrage de la transformation - {start_time}")
    
    try:
        retrieve_and_display_complete()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"✅ Transformation terminée - Durée: {duration:.1f}s")
        
        return "TRANSFORM_SUCCESS"
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"❌ Erreur lors de la transformation après {duration:.1f}s: {str(e)}")
        raise

def enhanced_load_with_monitoring(**context):
    """Chargement avec monitoring des performances"""
    start_time = datetime.now()
    print(f"📤 Démarrage du chargement - {start_time}")
    
    try:
        load()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"✅ Chargement terminé - Durée: {duration:.1f}s")
        
        return "LOAD_SUCCESS"
        
    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"❌ Erreur lors du chargement après {duration:.1f}s: {str(e)}")
        raise

def get_system_metrics():
    """Collecte des métriques système"""
    try:
        import psutil
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent
        }
    except:
        return {'cpu_percent': 0, 'memory_percent': 0, 'disk_usage': 0}

def generate_ml_report(**context):
    """Génère un rapport ML de performance"""
    print("📊 Génération du rapport ML...")
    
    try:
        # Lecture des logs de performance
        performance_file = '/opt/airflow/project/ml_logs/performance.json'
        if os.path.exists(performance_file):
            performances = []
            with open(performance_file, 'r') as f:
                for line in f:
                    try:
                        performances.append(json.loads(line))
                    except:
                        continue
            
            if performances:
                latest = performances[-1]
                avg_accuracy = sum(p.get('accuracy', 0) for p in performances[-10:]) / min(len(performances), 10)
                
                report = f"""
📈 RAPPORT ML - PIPELINE GOODAIR
================================

🎯 Dernière exécution:
   • Durée prédite: {latest.get('predicted_duration', 'N/A'):.1f}s
   • Durée réelle: {latest.get('actual_duration', 'N/A'):.1f}s
   • Précision: {latest.get('accuracy', 0):.2%}

📊 Performance moyenne (10 dernières exécutions):
   • Précision moyenne: {avg_accuracy:.2%}
   • Nombre d'exécutions: {len(performances)}

💡 Recommandations:
   • Modèle {'performant' if avg_accuracy > 0.8 else 'à améliorer'}
   • {'Prédictions fiables' if avg_accuracy > 0.8 else 'Collecte plus de données'}
   
🔧 Prochaine optimisation: {datetime.now() + timedelta(hours=1)}
"""
                print(report)
                
                # Sauvegarde du rapport
                with open('/opt/airflow/project/ml_logs/latest_report.txt', 'w') as f:
                    f.write(report)
                    
    except Exception as e:
        print(f"Erreur lors de la génération du rapport: {e}")

# =====================================
# CONFIGURATION DAG
# =====================================

default_args = {
    'owner': 'Electro choc - ML Enhanced',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 1),
    'email': ['v.mbanziladimbou@ecoles-epsi.net', 'lyes.boumrah@ecoles-epsi.net', 'belkis.coskun@ecoles-epsi.net', 'lucas.chipan@ecoles-epsi.net'],
    'email_on_failure': True,
    'email_on_retry': True,
    'email_on_success': True,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'meteo_villes_pipeline_ml_enhanced',
    default_args=default_args,
    description='Pipeline météo & qualité d\'air avec ML optimisé pour GoodAir',
    schedule_interval='@hourly',
    catchup=False,
    tags=['goodair', 'machine-learning', 'etl', 'bloc3']
)

# =====================================
# DÉFINITION DES TÂCHES
# =====================================

# 1. Tâche d'optimisation ML (première)
ml_optimization_task = PythonOperator(
    task_id='ml_optimization',
    python_callable=ml_pipeline_optimization,
    dag=dag,
    doc_md="""
    ## Optimisation ML du Pipeline
    
    Cette tâche utilise un modèle de Machine Learning pour:
    - Prédire la durée d'exécution du pipeline
    - Identifier les heures optimales d'exécution
    - Détecter les risques de surcharge
    - Optimiser l'allocation des ressources
    """
)

# 2. Tâches ETL améliorées avec monitoring
extract_task_enhanced = PythonOperator(
    task_id='extract_data_with_ml',
    python_callable=enhanced_extract_with_monitoring,
    dag=dag,
    doc_md="Extraction des données avec monitoring ML des performances"
)

transform_task_enhanced = PythonOperator(
    task_id='transform_data_with_ml',
    python_callable=enhanced_transform_with_monitoring,
    dag=dag,
    doc_md="Transformation des données avec monitoring ML des performances"
)

load_task_enhanced = PythonOperator(
    task_id='load_data_with_ml',
    python_callable=enhanced_load_with_monitoring,
    dag=dag,
    doc_md="Chargement des données avec monitoring ML des performances"
)

# 3. Tâche de génération de rapport ML
ml_report_task = PythonOperator(
    task_id='generate_ml_report',
    python_callable=generate_ml_report,
    dag=dag,
    doc_md="Génération du rapport de performance ML"
)

# 4. Tâche de nettoyage des logs (optionnelle)
cleanup_logs_task = BashOperator(
    task_id='cleanup_ml_logs',
    bash_command="""
    # Garde seulement les 100 dernières lignes des logs ML
    cd /opt/airflow/project/ml_logs
    if [ -f performance.json ]; then
        tail -n 100 performance.json > temp_perf.json
        mv temp_perf.json performance.json
    fi
    if [ -f predictions.json ]; then
        tail -n 100 predictions.json > temp_pred.json
        mv temp_pred.json predictions.json
    fi
    echo "Nettoyage des logs ML terminé"
    """,
    dag=dag
)

# 5. Email de succès avec informations ML
def send_ml_enhanced_email(**context):
    """Envoi d'email avec les résultats ML"""
    try:
        # Récupération de la prédiction ML
        ml_prediction = context['task_instance'].xcom_pull(task_ids='ml_optimization', key='ml_prediction')
        
        if ml_prediction:
            ml_info = f"""
            <h4>🤖 Résultats Machine Learning:</h4>
            <ul>
                <li>Durée prédite: {ml_prediction['predicted_duration']:.1f} secondes</li>
                <li>Heure optimale: {ml_prediction['optimal_time']}h00</li>
                <li>Confiance: {ml_prediction['confidence_level']:.2%}</li>
            </ul>
            """
        else:
            ml_info = "<p>Prédiction ML non disponible</p>"
            
        return ml_info
    except:
        return "<p>Erreur lors de la récupération des données ML</p>"

email_success_ml = EmailOperator(
    task_id='send_ml_success_email',
    to=['v.mbanziladimbou@ecoles-epsi.net', 'lyes.boumrah@ecoles-epsi.net', 'belkis.coskun@ecoles-epsi.net', 'lucas.chipan@ecoles-epsi.net'],
    subject='🤖 Pipeline GoodAir ML-Enhanced exécuté avec succès | {{ ds }}',
    html_content="""
    <h2>🌟 Pipeline GoodAir - Exécution Réussie</h2>
    
    <h3>📊 Informations d'exécution:</h3>
    <ul>
        <li>Date: {{ ds }}</li>
        <li>Heure: {{ execution_date.strftime('%H:%M:%S') }}</li>
        <li>DAG: {{ dag.dag_id }}</li>
    </ul>
    
    <h3>🤖 Intelligence Artificielle:</h3>
    <p>Ce pipeline utilise un modèle de Machine Learning pour optimiser automatiquement les performances et prédire les besoins de la plateforme GoodAir.</p>
    
    <h3>✅ Tâches exécutées:</h3>
    <ol>
        <li>🧠 Optimisation ML</li>
        <li>📥 Extraction des données météo et qualité d'air</li>
        <li>🔄 Transformation et normalisation</li>
        <li>📤 Chargement en base de données</li>
        <li>📊 Génération du rapport ML</li>
    </ol>
    
    <p><em>Pipeline développé par l'équipe Electro Choc pour le laboratoire GoodAir</em></p>
    """,
    dag=dag
)

# =====================================
# DÉFINITION DU WORKFLOW
# =====================================

# Workflow principal avec ML
ml_optimization_task >> extract_task_enhanced >> transform_task_enhanced >> load_task_enhanced >> ml_report_task >> cleanup_logs_task >> email_success_ml

# Documentation du DAG
dag.doc_md = """
# Pipeline GoodAir avec Machine Learning (BLOC 3)

## 🎯 Objectif
Pipeline ETL optimisé par Machine Learning pour le laboratoire de recherche GoodAir, 
collectant et traitant les données de qualité d'air et météorologiques des principales villes françaises.

## 🤖 Intelligence Artificielle
- **Prédiction** de la durée d'exécution du pipeline
- **Optimisation** automatique des ressources
- **Détection** des risques de surcharge
- **Recommandations** pour les heures d'exécution optimales

## 📊 Sources de données
- API Qualité d'air: https://aqicn.org/json-api/doc/
- API Météo: https://openweathermap.org/api

## 🏗️ Architecture
- **Stockage**: MinIO (Data Lake) + PostgreSQL (Data Warehouse)
- **Orchestration**: Apache Airflow
- **ML**: Scikit-learn avec modèle RandomForest
- **Monitoring**: Métriques système et performances

## 👥 Équipe
Electro Choc - Certification Expert Ingénierie des Données (BLOC 3)
"""