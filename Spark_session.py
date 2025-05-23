from pyspark.sql import SparkSession

def get_spark_session():
    spark = SparkSession.builder \
        .appName("GoodAir Data Pipeline") \
        .master("local[*]") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()
    return spark
