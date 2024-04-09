import os
import json
import boto3
import pymysql

host = os.environ.get("DB_ENDPOINT")
port = int(os.environ.get("DB_PORT") or 3306)
user = os.environ.get("DB_USERNAME")
password = os.environ.get("DB_PASSWORD")
database = os.environ.get("DB_NAME")

sns = boto3.client("sns")

sns_topic_arn = os.environ["SNS_TOPIC_ARN"]


def lambda_handler(event, context):
    # Connect to RDS
    connection = pymysql.connect(
        host=host, port=port, user=user, password=password, database=database
    )

    statistics = {}

    # Retrieve statistics on records
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT AVG(CAST(temperature AS FLOAT)) FROM temperature_log WHERE is_outside_temperature = 0"
        )
        inside_avg_temperature = cursor.fetchone()[0]

        cursor.execute(
            "SELECT AVG(CAST(temperature AS FLOAT)) FROM temperature_log WHERE is_outside_temperature = 1"
        )
        outside_avg_temperature = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM temperature_log WHERE CAST(temperature AS FLOAT) > 36"
        )
        anomaly_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM temperature_log")
        total_records = cursor.fetchone()[0]

        statistics.update(
            {
                "inside_avg_temperature": inside_avg_temperature,
                "outside_avg_temperature": outside_avg_temperature,
                "anomaly_count": anomaly_count,
                "total_records": total_records,
            }
        )

    # Close the database connection
    connection.close()

    sns.publish(
        TopicArn=sns_topic_arn,
        Message=f"Building Temperature Statistics: {json.dumps(statistics, indent=4)}",
        Subject="Temperature Statistics",
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Statistics generated and sent to SNS topic.",
            "statistics": statistics,
        }, indent=4),
    }
