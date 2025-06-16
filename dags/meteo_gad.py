from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.email import EmailOperator
import sys
import os

sys.path.append('/opt/airflow/project') 

from extract import extract_and_store
from transform import retrieve_and_display_complete
from Load import load

default_args = {
    'owner': 'Electro choc',
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
    'meteo_villes_pipeline',
    default_args=default_args,
    description='Pipeline météo & qualité d’air',
    schedule_interval='@hourly',  # Tous les jours à 08h06
    catchup=False
)




# Tâches ETL
extract_task = PythonOperator(
    task_id='extract_data',
    python_callable=extract_and_store,
    dag=dag
)

transform_task = PythonOperator(
    task_id='transform_data',
    python_callable=retrieve_and_display_complete,
    dag=dag
)

load_task = PythonOperator(
    task_id='load_data',
    python_callable=load,
    dag=dag
)


# send_success_email = EmailOperator(
#     task_id='send_success_email',
#     to=['v.mbanziladimbou@ecoles-epsi.net', 'lyes.boumrah@ecoles-epsi.net', 'belkis.coskun@ecoles-epsi.net', 'lucas.chipan@ecoles-epsi.net'],
#     subject='Pipeline météo exécuté avec succès | {{ ds }}',
#     html_content="""
#     <h3>Le pipeline météo & qualité d'air s'est exécuté avec succès</h3>
#     <p>Date d'exécution: {{ ds }}</p>
#     <p>Heure d'exécution: {{ execution_date.strftime('%H:%M:%S') }}</p>
#     """,
#     dag=dag
# )

extract_task >> transform_task >> load_task 
# >> send_success_email
