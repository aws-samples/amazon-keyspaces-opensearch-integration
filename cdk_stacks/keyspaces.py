import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_cassandra as cassandra
)
from constructs import Construct

class OpsKeyspacesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ks = cassandra.CfnKeyspace(
            self, "OpsKeyspaces", keyspace_name="productsearch"
        )
        cassandra.CfnTable(
            self,
            "productsearch",
            table_name="product_by_item",
            keyspace_name="productsearch",
            regular_columns=[
                cassandra.CfnTable.ColumnProperty(
                    column_name="product_description", 
                    column_type="text"
                ),
                cassandra.CfnTable.ColumnProperty(
                    column_name="product_name", 
                    column_type="text"
                ),                               
            ],
            partition_key_columns=[
                cassandra.CfnTable.ColumnProperty(
                    column_name="product_id", column_type="int"
                )                
            ],
        ).add_depends_on(ks)