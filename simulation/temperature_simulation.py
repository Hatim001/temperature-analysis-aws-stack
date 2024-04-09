import os
import csv
import json
import boto3
from time import sleep
from datetime import datetime

S3_KEY = os.getenv("S3_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
KINESIS_STREAM_NAME = os.getenv("KINESIS_STREAM_NAME")

s3 = boto3.client("s3", region_name="us-east-1")
s3_resource = boto3.resource("s3", region_name="us-east-1")
kinesis_client = boto3.client("kinesis", region_name="us-east-1")


def temperature_data_simulator():
    """simulates temperature from custom csv file stored in s3 bucket"""

    print(f"Reading data from S3 bucket: {S3_BUCKET} and key: {S3_KEY}")

    csv_resource = s3_resource.Object(S3_BUCKET, S3_KEY)
    csv_response = csv_resource.get()
    csv_data = csv_response["Body"].read().decode("utf-8").split("\n")

    trimmed_records = csv_data[:2000]

    for record in csv.DictReader(trimmed_records):
        parsed_record = {
            "id": record.get("id"),
            "room": record.get("room_id/id"),
            "timestamp": datetime.now().isoformat(),
            "temperature": record.get("temp"),
            "is_outside_temperature": 1 if record.get("out/in") == "Out" else 0,
        }
        response = kinesis_client.put_record(
            StreamName=KINESIS_STREAM_NAME,
            Data=json.dumps(parsed_record),
            PartitionKey=str(parsed_record.get("is_outside_temperature")),
        )
        print(
            f"Response ({response.get('ResponseMetadata').get('HTTPStatusCode')}) - Record sent to Kinesis (SequenceNumber: {response.get('SequenceNumber')})"
        )

        sleep(1)


if __name__ == "__main__":
    try:
        temperature_data_simulator()
    except Exception as e:
        print(f"Error: {e}")
        raise e
