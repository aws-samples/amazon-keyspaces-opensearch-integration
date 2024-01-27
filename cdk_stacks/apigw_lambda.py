import os
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import (
    Stack,
    aws_apigateway as apigw_,
    aws_lambda as lambda_,
    aws_iam as iam_,
    aws_kms as kms_,
    )

class OpsApigwLambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        #Create a lambda layer with the requests library.
        requests_layer = lambda_.LayerVersion(
            self,
            "requests-cassandra",
            code=lambda_.Code.from_asset("lambda_layers/requests-cassandra.zip"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9]
        )
        #Create a lambda layer with the latest boto3.
        boto3_layer = lambda_.LayerVersion(
            self,
            "boto3",
            code=lambda_.Code.from_asset("lambda_layers/boto3.zip"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9]
        )

        #Create a requests-auth-aws-sigv4 lambda layer.
        requests_auth_aws_sigv4_layer = lambda_.LayerVersion(
            self,
            "requests-auth-aws-sigv4",
            code=lambda_.Code.from_asset("lambda_layers/requests-auth-aws-sigv4.zip"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9]
        )

        #Create an IAM policy with permission osis:ingest
        ingest_policy_doc = iam_.PolicyDocument()
        ingest_policy_doc.add_statements(iam_.PolicyStatement(**{
          "effect": iam_.Effect.ALLOW,
          "resources": [ f"arn:aws:osis:*:{cdk.Aws.ACCOUNT_ID}:pipeline/*"],
          "actions": [
              "osis:Ingest"
          ] 
        }))          

        #Create an IAM role for the Lambda function
        lambda_role = iam_.Role(
            self,
            "LambdaRole",
            assumed_by=iam_.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam_.ManagedPolicy.from_aws_managed_policy_name('AmazonKeyspacesFullAccess'),
                iam_.ManagedPolicy.from_aws_managed_policy_name('service-role/AWSLambdaBasicExecutionRole')
            ],
            inline_policies={
                "IngestPolicy": ingest_policy_doc
            }
        )
                      
        #Create the Lambda function to insert/update/delete a keyspaces table. 
        apigw_lambda = lambda_.Function(
            self,
            "ApiHandler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                "TABLE_NAME": "product_by_item",
                "KEYSPACE_NAME": "productsearch",
                "INGESTION_ENDPOINT": cdk.Fn.import_value('OpsServerlessIngestionStackPipelineUrl')
            },
            layers=[requests_layer, boto3_layer, requests_auth_aws_sigv4_layer],
            role=lambda_role
        )

        #Create the API Gateway.
        api = apigw_.LambdaRestApi(
            self,
            "Keyspaces-OpenSearch-Endpoint",
            handler=apigw_lambda
            )

        deployment = apigw_.Deployment(
            self,
            "Deployment",
            api=api,
            retain_deployments=False
        )

        cdk.CfnOutput(
            self,
            "ApiUrl",
            value=api.url
        )


