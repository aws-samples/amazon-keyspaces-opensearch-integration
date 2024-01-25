import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_logs,
  aws_osis
)
from constructs import Construct


class OpsServerlessIngestionStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, pipeline_role_arn, collection_endpoint, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    pipeline_name = "serverless-ingestion"

    pipeline_configuration_body = f'''version: "2"
product-pipeline:
  source:
    http:
      path: "/${{pipelineName}}/test_ingestion_path"
  processor:
    - date:
        from_time_received: true
        destination: "@timestamp"
  sink:
    - opensearch:
        hosts: [ "{collection_endpoint}" ]
        document_root_key: "item"
        index_type: custom
        index: "products"
        document_id_field: "item/product_id"
        flush_timeout: -1
        actions:
          - type: "delete"
            when: '/operation == "delete"'
          - type: "index"                      
        aws:
          sts_role_arn: "{pipeline_role_arn}"
          region: "{cdk.Aws.REGION}"
          serverless: true'''

    osis_pipeline_log_group = aws_logs.LogGroup(self, 'OSISPipelineLogGroup',
      log_group_name=f"/aws/vendedlogs/OpenSearchIngestion/{pipeline_name}/audit-logs",
      retention=aws_logs.RetentionDays.THREE_DAYS,
      removal_policy=cdk.RemovalPolicy.DESTROY
    )

    cfn_pipeline = aws_osis.CfnPipeline(self, "CfnOSISPipeline",
      max_units=4,
      min_units=1,
      pipeline_configuration_body=pipeline_configuration_body,
      pipeline_name=pipeline_name,

      # the properties below are optional
      log_publishing_options=aws_osis.CfnPipeline.LogPublishingOptionsProperty(
        cloud_watch_log_destination=aws_osis.CfnPipeline.CloudWatchLogDestinationProperty(
          log_group=osis_pipeline_log_group.log_group_name,
        ),
        is_logging_enabled=True
      )
    )

    cdk.CfnOutput(self, f'{self.stack_name}PipelineName', value=cfn_pipeline.pipeline_name)
    cdk.CfnOutput(
      self, f'{self.stack_name}PipelineUrl', 
      value=cdk.Fn.select(0, cfn_pipeline.attr_ingest_endpoint_urls),
      export_name=f'{self.stack_name}PipelineUrl'
      )