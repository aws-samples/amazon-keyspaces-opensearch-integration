#!/usr/bin/env python3
import os

from cdk_stacks import (
  OpsCollectionPipelineRoleStack,
  OpsServerlessStack,
  OpsServerlessIngestionStack,
  OpsKeyspacesStack,
  OpsApigwLambdaStack
)

import aws_cdk as cdk


AWS_ENV = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION'))

app = cdk.App()

collection_pipeline_role = OpsCollectionPipelineRoleStack(app, 'OpsCollectionPipelineRoleStack')

ops_serverless_stack = OpsServerlessStack(app, "OpsServerlessStack",
  collection_pipeline_role.iam_role.role_arn,
  env=AWS_ENV)
ops_serverless_stack.add_dependency(collection_pipeline_role)

ops_serverless_ingestion_stack = OpsServerlessIngestionStack(app, "OpsServerlessIngestionStack",
  collection_pipeline_role.iam_role.role_arn,
  ops_serverless_stack.collection_endpoint,
  env=AWS_ENV)
ops_serverless_ingestion_stack.add_dependency(ops_serverless_stack)

ops_keyspaces_stack = OpsKeyspacesStack(app, "OpsKeyspacesStack", env=AWS_ENV)

apigw_lambda_stack = OpsApigwLambdaStack(app, "OpsApigwLambdaStack", env=AWS_ENV)
apigw_lambda_stack.add_dependency(ops_serverless_ingestion_stack)

app.synth()
