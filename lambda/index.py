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

def ingest_data(ingestion_endpoint, payload):
    """Ingests data into the Opensearch ingestion pipeline"""
    endpoint = 'https://' + ingestion_endpoint
    payload_list = [payload]
    operation = payload['operation']
    item = payload['item']
    product_id = item['product_id']
    print(f'## product_id is: {product_id}')
    logging.info(f"## Ingesting payload: {payload} into the ingestion pipeline at endpoint: {endpoint}.")    
    r = requests.request('POST', f'{endpoint}/product-pipeline/test_ingestion_path', 
                         headers={"Content-Type": "application/json"},
                         json=payload_list,
                         auth=AWSSigV4('osis'))
    if r.status_code == 200:
        logging.info(f"## {operation} item: {item} into the ingestion pipeline succeeded with response: {r.text}")
    else:
        raise Exception(f"## {operation} item: {item} into the ingestion pipeline failed with response: {r.text}")
    return r


def handler(event, context):
    print(event)
    cert_file_path = get_tls_cert()
    keyspace_name = os.environ.get("KEYSPACE_NAME")
    logging.info(f"## Loaded Keyspace name from environemt variable KEYSPACE_NAME: {keyspace_name}")
    table_name = os.environ.get("TABLE_NAME")
    logging.info(f"## Loaded table name from environemt variable TABLE_NAME: {table_name}")
    ingestion_endpoint = os.environ.get("INGESTION_ENDPOINT")
    logging.info(f"## Loaded ingestion endpoint from environemt variable INGESTION_ENDPOINT: {ingestion_endpoint}")
    full_table_name = f"{keyspace_name}.{table_name}"
    if event["body"]:
        body = json.loads(event["body"])
        logging.info(f"## Received payload: {body}")
        operation = body.get("operation") 
        try:
            assert operation in ["insert", "update", "delete"]
            logging.info(f"## Received operation: {operation}")
            assert isinstance(body.get("item"), dict)
            logging.info(f"## Received item: {body.get('item')}")
        except AssertionError as e:
            logging.error(f"## Invalid payload: {body}.")
            message = f"Invalid payload: {body}. Allowed operations are insert/update/delete, followed by item."
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": message}),
            }            
        item = body.get("item")  
        boto3_session = boto3.session.Session()
        with QueryManager(
                cert_file_path, boto3_session, keyspace_name
            ) as qm:
            if operation == "insert":
                response_qm = qm.insert_item(full_table_name, item)
            elif operation == "update":
                response_qm = qm.update_item(full_table_name, item)
            else:
                response_qm = qm.delete_item(full_table_name, item)
        logging.info(f"## Response from keyspace operation: {response_qm}")

        # If keyspace operation is successful, then ingest the data into Opensearch.
        if response_qm == 200:
            response_osis = ingest_data(ingestion_endpoint, body)
            status_code = response_osis.status_code
            if status_code  == 200:
                message = f"Ingestion completed successfully for {body}."
            else: 
                message = f"Ingestion failed for {body}."
        else:
            status_code = response_qm
            message = f"Keyspace {operation} operation failed."
        return {
                "statusCode": status_code,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": message}),
            }
