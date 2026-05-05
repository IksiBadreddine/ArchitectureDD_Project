"""
DAG Airflow pour le scraping batch des annonces
Exécute toutes les heures via Docker
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import os

default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'start_date': datetime(2026, 5, 4),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'espacevoiture_batch_scraping',
    default_args=default_args,
    description='Scraping batch des annonces Espacevoiture.com',
    schedule_interval='0 * * * *',  # Toutes les heures à H:00
    catchup=False,
    tags=['scraping', 'espacevoiture', 'batch'],
)

# Tâche 1: Scraping batch avec installation des dépendances
scraping_task = BashOperator(
    task_id='scraping_batch',
    bash_command="""
    cd /opt/airflow/project && \
    pip install --quiet requests beautifulsoup4 pandas minio && \
    python ingestion/batch_ingestion.py
    """,
    dag=dag,
)

# Tâche 2: Vérification MinIO (optionnel)
check_minio_task = BashOperator(
    task_id='check_minio',
    bash_command='curl -s http://minio:9000/minio/health/live && echo "MinIO OK" || echo "MinIO KO"',
    dag=dag,
)

# Tâche 3: Nettoyage des fichiers temporaires
cleanup_task = BashOperator(
    task_id='cleanup',
    bash_command='rm -f /opt/airflow/project/batch_*.csv 2>/dev/null || echo "No temp files"',
    dag=dag,
)

# Ordre des tâches
scraping_task >> check_minio_task >> cleanup_task