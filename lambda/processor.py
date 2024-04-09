import os
import json
import boto3
import base64
import pymysql

host = os.environ.get("DB_ENDPOINT")
port = int(os.environ.get("DB_PORT") or 3306)
user = os.environ.get("DB_USERNAME")
password = os.environ.get("DB_PASSWORD")
database = os.environ.get("DB_NAME")

sns = boto3.client("sns")

sns_topic_arn = os.environ["SNS_TOPIC_ARN"]

# Connect to the database
connection = pymysql.connect(
    host=host, port=port, user=user, password=password, database=database
)


def lambda_handler(event, context):
    output = []

    for record in event["records"]:
        # Decode from base64
        decoded_data = base64.b64decode(record["data"]).decode("utf-8")
        payload = json.loads(decoded_data)

        # Processing logic
        process_record(payload)

        # Append the original record data to the output, unchanged
        output_record = {
            "recordId": record["recordId"],
            "result": "Ok",
            "data": record["data"],
        }
        output.append(output_record)

    return {"records": output}


def process_record(payload):

    # store records in rds
    cursor = connection.cursor()
    # Check if temperature_log table exists
    cursor.execute("SHOW TABLES LIKE 'temperature_log'")
    table_exists = cursor.fetchone()

    if table_exists:
        # Table exists, insert records
        sql = "INSERT INTO temperature_log (room, temperature, timestamp, is_outside_temperature) VALUES (%s, %s, %s, %s)"
        cursor.execute(
            sql,
            (
                payload["room"],
                payload["temperature"],
                payload["timestamp"],
                str(payload["is_outside_temperature"]),
            ),
        )
        connection.commit()
    else:
        # Table does not exist, create table and insert records
        create_table_sql = """
        CREATE TABLE temperature_log (
            id INT AUTO_INCREMENT PRIMARY KEY,
            room VARCHAR(255),
            temperature FLOAT,
            timestamp DATETIME,
            is_outside_temperature BOOLEAN
        )
        """
        cursor.execute(create_table_sql)
        connection.commit()
        sql = "INSERT INTO temperature_log (room, temperature, timestamp, is_outside_temperature) VALUES (%s, %s, %s, %s)"
        cursor.execute(
            sql,
            (
                payload["room"],
                payload["temperature"],
                payload["timestamp"],
                str(payload["is_outside_temperature"]),
            ),
        )
        connection.commit()

    detect_anomaly(payload)


def detect_anomaly(payload):

    # detect anomalies in temperature and send to sns
    if "temperature" in payload:
        temperature = payload["temperature"]
        if int(temperature) > 36:
            sns.publish(
                TopicArn=sns_topic_arn,
                Message=f"Alert: Temperature in room {payload['room']} is {temperature} degrees Celsius.",
                Subject="Temperature Raise Alert",
            )
