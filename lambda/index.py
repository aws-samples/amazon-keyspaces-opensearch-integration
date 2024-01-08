import asyncio
import boto3
import os
import json
import logging
import requests
from requests_auth_aws_sigv4 import AWSSigV4
from query import QueryManager
from boto3.session import Session as boto3_session

logger = logging.getLogger()
logger.setLevel(logging.INFO)

example_json_input = {
    "operation": "insert",
    "item": {
        "product_id": 100,
        "product_name": "Reindeer sweater",
        "product_description": "A Christmas sweater for everyone in the family."
    }
}

def get_tls_cert():
    """
    This function downloads a TLS certificate to use to secure the connection
    to the keyspace.
    """
    cert_path = os.path.join(
        "/tmp", QueryManager.DEFAULT_CERT_FILE
    )
    if not os.path.exists(cert_path):
        cert = requests.get(QueryManager.CERT_URL).text
        with open(cert_path, "w") as cert_file:
            cert_file.write(cert)
    return cert_path

async def ingest_data_async(ingestion_endpoint, payload):
    """Ingests data into the Opensearch ingestion pipeline"""
    endpoint = 'https://' + ingestion_endpoint
    payload_list = [payload]
    operation = payload['operation']
    item = payload['item']
    product_id = item['product_id']
    print(f'## product_id is: {product_id}')
    logging.info(f"## Ingesting payload: {payload} into the ingestion pipeline at endpoint: {endpoint}.")    
    response = requests.request('POST', f'{endpoint}/product-pipeline/test_ingestion_path', 
                         headers={"Content-Type": "application/json"},
                         json=payload_list,
                         auth=AWSSigV4('osis'))
    if response.status_code == 200:
        logging.info(f"## {operation} item: {item} into the ingestion pipeline succeeded with response: {response.text}")
    else:
        raise Exception(f"## {operation} item: {item} into the ingestion pipeline failed with response: {response.text}")
    return response


async def process_payload_async(cert_file_path, keyspace_name, table_name, ingestion_endpoint, body):
    """
    This function inserts/deletes/updates payloads in Amazon Keyspaces, and then asynchronously ingest payloads into Amazon OpenSearch using Amazon Opensearch Ingestion.
    """
    with QueryManager(cert_file_path, boto3_session(), keyspace_name) as qm:
        operation = body.get("operation")

        try:
            assert operation in ["insert", "update", "delete"]
            logger.info(f"## Received operation: {operation}")
            assert isinstance(body.get("item"), dict)
            logger.info(f"## Received item: {body.get('item')}")
        except AssertionError as e:
            logger.error(f"## Invalid payload: {body}.")
            message = f"Invalid payload: {body}. Please ensure your operation is one of the following: insert, update or delete, followed by an item. Example JSON input: {example_json_input}"
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": message}),
            }

        item = body.get("item")

        if operation == "insert":
            response_qm = qm.insert_item(table_name, item)
        elif operation == "update":
            response_qm = qm.update_item(table_name, item)
        else:
            response_qm = qm.delete_item(table_name, item)

        logger.info(f"## Response from keyspace operation: {response_qm}")

        # If keyspace operation is successful, then ingest the data into Opensearch asynchronously.
        if response_qm == 200:
            response_osis = await ingest_data_async(ingestion_endpoint, body)
            status_code = response_osis.status_code if response_osis else 500
            if status_code == 200:
                message = f"Opensearch ingestion completed successfully for {body}."
            else:
                message = f"Opensearch ingestion failed for {body}."
        else:
            status_code = response_qm
            message = f"Keyspace {operation} operation failed for {body}."
        return {
            "statusCode": status_code,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": message}),
        }

def handler(event, context):
    logger.info(event)
    cert_file_path = get_tls_cert()
    keyspace_name = os.environ.get("KEYSPACE_NAME")
    logger.info(f"## Loaded Keyspace name from environment variable KEYSPACE_NAME: {keyspace_name}")
    table_name = os.environ.get("TABLE_NAME")
    logger.info(f"## Loaded table name from environment variable TABLE_NAME: {table_name}")
    ingestion_endpoint = os.environ.get("INGESTION_ENDPOINT")
    logger.info(f"## Loaded ingestion endpoint from environment variable INGESTION_ENDPOINT: {ingestion_endpoint}")
    full_table_name = f"{keyspace_name}.{table_name}"

    if event["body"]:
        body = json.loads(event["body"])
        logger.info(f"## Received payload: {body}")

        # Run the payload processing asynchronously
        response = asyncio.run(process_payload_async(cert_file_path, keyspace_name, full_table_name, ingestion_endpoint, body))

        return response
