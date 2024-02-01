import os
import aws_cdk as cdk
from constructs import Construct
import cdk_nag
from cdk_nag import AwsSolutionsChecks, NagSuppressions
from aws_cdk import (
    Aspects,
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
        ingest_policy_doc.add_statements(
            iam_.PolicyStatement(
                effect=iam_.Effect.ALLOW,
                resources=[cdk.Fn.import_value('OpsServerlessIngestionStackPipelineArn')],
                actions=["osis:Ingest"]
            ),
            iam_.PolicyStatement(
                effect=iam_.Effect.ALLOW,
                resources=[
                    f"arn:aws:cassandra:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:/keyspace/productsearch/table/product_by_item",
                    f"arn:aws:cassandra:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:/keyspace/productsearch/"                    
                ],
                actions=[
                    "cassandra:SelectMultiRegionResource",
                    "cassandra:DropMultiRegionResource",
                    "cassandra:Drop",
                    "cassandra:Create",
                    "cassandra:Alter",
                    "cassandra:ModifyMultiRegionResource",
                    "cassandra:Select",
                    "cassandra:CreateMultiRegionResource",
                    "cassandra:AlterMultiRegionResource",
                    "cassandra:Modify"                    
                ]
            ),
            iam_.PolicyStatement(
                effect=iam_.Effect.ALLOW,
                resources=[
                    f"arn:aws:logs:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:log-group:/aws/lambda/*"
                ],
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ]
            )
        )   
         
        #Create an IAM role for the Lambda function
        lambda_role = iam_.Role(
            self,
            "LambdaRole",
            assumed_by=iam_.ServicePrincipal("lambda.amazonaws.com"),
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

        Aspects.of(self).add(cdk_nag.AwsSolutionsChecks())
        NagSuppressions.add_stack_suppressions(stack=self, suppressions=[
        {"id": "AwsSolutions-IAM5", "reason": "The wildcard is required for the Lambda function to write logs to CloudWatch."}
    ])