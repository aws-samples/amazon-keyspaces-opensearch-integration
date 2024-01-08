# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from datetime import date
import json
from ssl import SSLContext, PROTOCOL_TLSv1_2, CERT_REQUIRED

from cassandra.cluster import (
    Cluster,
    ExecutionProfile,
    EXEC_PROFILE_DEFAULT,
    DCAwareRoundRobinPolicy,
)
from cassandra import ConsistencyLevel
from cassandra.query import SimpleStatement
from cassandra_sigv4.auth import SigV4AuthProvider


class QueryManager:
    """
    Manages inserts/updates/deletes to an Amazon Keyspaces (for Apache Cassandra) keyspace.
    Queries are secured by TLS and authenticated by using the Signature V4 (SigV4)
    AWS signing protocol. This is more secure than sending username and password
    with a plain-text authentication provider.

    This example downloads a default certificate to secure TLS, or lets you specify
    your own.
    """

    DEFAULT_CERT_FILE = "sf-class2-root.crt"
    CERT_URL = f"https://certs.secureserver.net/repository/sf-class2-root.crt"

    def __init__(self, cert_file_path, boto_session, keyspace_name):
        """
        :param cert_file_path: The path and file name of the certificate used for TLS.
        :param boto_session: A Boto3 session. This is used to acquire your AWS credentials.
        :param keyspace_name: The name of the keyspace to connect.
        """
        self.cert_file_path = cert_file_path
        self.boto_session = boto_session
        self.ks_name = keyspace_name
        self.cluster = None
        self.session = None

    def __enter__(self):
        """
        Creates a session connection to the keyspace that is secured by TLS and
        authenticated by SigV4.
        """
        ssl_context = SSLContext(PROTOCOL_TLSv1_2)
        ssl_context.load_verify_locations(self.cert_file_path)
        ssl_context.verify_mode = CERT_REQUIRED
        auth_provider = SigV4AuthProvider(self.boto_session)
        contact_point = f"cassandra.{self.boto_session.region_name}.amazonaws.com"
        exec_profile = ExecutionProfile(
            consistency_level=ConsistencyLevel.LOCAL_QUORUM,
            load_balancing_policy=DCAwareRoundRobinPolicy(),
        )
        self.cluster = Cluster(
            [contact_point],
            ssl_context=ssl_context,
            auth_provider=auth_provider,
            port=9142,
            execution_profiles={EXEC_PROFILE_DEFAULT: exec_profile},
            protocol_version=4,
        )
        self.cluster.__enter__()
        self.session = self.cluster.connect(self.ks_name)
        return self

    def __exit__(self, *args):
        """
        Exits the cluster. This shuts down all existing session connections.
        """
        self.cluster.__exit__(*args)

    def insert_item(self, table_name, item):
        """
        Insert an item into a table in the keyspace.

        :param table_name: The name of the table.
        :param item: The item to insert. The item is a json object.
        :return: The return code of the operation.
        """
        statement = self.session.prepare(
            f"INSERT INTO {table_name} (product_id, product_name, product_description) VALUES (?,?,?);"
        )
        try:            
            response = self.session.execute(
                statement,
                parameters=[
                    item["product_id"],
                    item["product_name"],
                    item["product_description"],
                ])
            results = response.response_future
            print(f"### Keyspaces insert succeeded with response: {results}")
            status_code = 200
        except Exception as e:
            print(f"### Keyspaces insert failed with exception: {str(e)}.")
            status_code = 500
        return status_code
    

    def update_item(self, table_name, item):
        """
        Update an item in a table in the keyspace.

        :param table_name: The name of the table.
        :param item: The item to update. The item is a json object.
        :return: The return code of the operation. 
        """
        statement = self.session.prepare(
            f"UPDATE {table_name} SET product_name=?, product_description=? WHERE product_id=?"
        )
        try:            
            response = self.session.execute(
                statement,
                parameters=[
                    item["product_name"],
                    item["product_description"],
                    item["product_id"]
                ])
            results = response.response_future
            print(f"### Keyspaces update succeeded with response: {results}")
            status_code = 200
        except Exception as e:
            print(f"### Keyspaces update failed with exception: {str(e)}.")
            status_code = 500  
        return status_code


    def delete_item(self, table_name, item):
        """
        Delete an item from a table in the keyspace.

        :param table_name: The name of the table.
        :param item: The item to delete.
        :return: The return code of the operation.
        """
        statement = self.session.prepare(
            f"DELETE FROM {table_name} WHERE product_id = ?"
        )
        try:            
            response = self.session.execute(
                statement,
                parameters=[
                    item["product_id"]
                ])
            results = response.response_future
            print(f"### Keyspaces delete succeeded with response:: {results}")
            status_code = 200
        except Exception as e:
            print(f"### Keyspaces delete failed with exception: {str(e)}.")
            status_code = 500
        return status_code

