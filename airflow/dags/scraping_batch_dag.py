"""
DAG Airflow pour le scraping batch + ETL vers Data Warehouse
Exécute toutes les heures via Docker
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
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
    description='Scraping batch + ETL vers Data Warehouse (Espacevoiture.com)',
    schedule_interval='0 * * * *',  # Toutes les heures à H:00
    catchup=False,
    tags=['scraping', 'espacevoiture', 'batch', 'etl', 'gold'],
)

# ============================================================
# TÂCHE 1: Scraping batch (Bronze)
# ============================================================
scraping_task = BashOperator(
    task_id='scraping_batch',
    bash_command="""
    cd /opt/airflow/project && \
    pip install --quiet requests beautifulsoup4 pandas minio && \
    python ingestion/batch_ingestion.py
    """,
    dag=dag,
)

# ============================================================
# TÂCHE 2: ETL Bronze → Silver (Nettoyage)
# ============================================================
bronze_to_silver_task = BashOperator(
    task_id='bronze_to_silver',
    bash_command="""
    cd /opt/airflow/project && \
    pip install --quiet pandas pyarrow && \
    python etl/bronze_to_silver_v2.py
    """,
    dag=dag,
)

# ============================================================
# TÂCHE 3: ETL Silver → Gold (Data Warehouse)
# ============================================================
silver_to_gold_task = BashOperator(
    task_id='silver_to_gold',
    bash_command="""
    cd /opt/airflow/project && \
    pip install --quiet psycopg2-binary && \
    python etl/silver_to_gold.py
    """,
    dag=dag,
)

# ============================================================
# TÂCHE 4: Vérification MinIO (optionnel)
# ============================================================
check_minio_task = BashOperator(
    task_id='check_minio',
    bash_command='curl -s http://minio:9000/minio/health/live && echo "MinIO OK" || echo "MinIO KO"',
    dag=dag,
)

# ============================================================
# TÂCHE 5: Nettoyage des fichiers temporaires
# ============================================================
cleanup_task = BashOperator(
    task_id='cleanup',
    bash_command='rm -f /opt/airflow/project/batch_*.csv 2>/dev/null || echo "No temp files"',
    dag=dag,
)

# ============================================================
# ORDRE D'EXÉCUTION
# ============================================================
scraping_task >> bronze_to_silver_task >> silver_to_gold_task >> check_minio_task >> cleanup_task