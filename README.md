
# Amazon Keyspaces integration with Amazon Opensearch

This project shows you how to integrate Amazon Keyspaces with Amazon Opensearch to provide fast search capabilities on Keyspaces tables.

The solution is defined in an [AWS CDK](https://aws.amazon.com/cdk/) project and published in this AWS [blog](https://aws.amazon.com/blogs/big-data/enable-advanced-search-capabilities-for-amazon-keyspaces-data-by-integrating-with-amazon-opensearch-service/). 

## Deployment Steps

First, you’ll need to install the following prerequisites:

1. [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
2. AWS CLI [user profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
3. [Node.js and npm](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)
4. IDE for your programming language
5. [AWS CDK Toolkit](https://aws.amazon.com/getting-started/guides/setup-cdk/module-two/)
6. [Python](https://docs.python-guide.org/starting/install3/osx/)

Clone the repository to your IDE and change directory to the cloned repository.
```
git clone <repo-link>
cd <repo-dir>
```

This project is set up like a standard Python project. Create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the virtualenv is created, you can use the following step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
(.venv) $ pip install -r requirements.txt
```
Bootstrap CDK in your account:
```
(.venv) $ cdk bootstrap aws://<aws_account_id>/<aws_region>
```
Once the boostrap process is completed, you will see a CDKToolkit CloudFormation stack in your CloudFormation console and CDK is ready for use. You can now synthesize the CloudFormation template for this code.

```
(.venv) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
(.venv) $ export CDK_DEFAULT_REGION=<aws_region>
(.venv) $ cdk synth -c iam_user_name=<your-iam-user-name> --all
```

Use `cdk deploy` command to create the stack shown above.

```
(.venv) $ cdk deploy -c iam_user_name=<your-iam-user-name> --all
```
Once the deploy process is completed, you will see the following CloudFormation stacks in the CloudFormation console:
- OpsApigwLambdaStack
- OpsServerlessIngestionStack
- OpsServerlessStack
- OpsKeyspacesStack
- OpsCollectionPipelineRoleStack


## Clean Up

Delete the CloudFormation stacks by running the below command.

```
(.venv) $ cdk destroy -c iam_user_name=<your-iam-user-name> --force --all
```

Verify the following CloudFormation stacks are deleted from the CloudFormation console:
- OpsApigwLambdaStack
- OpsServerlessIngestionStack
- OpsServerlessStack
- OpsKeyspacesStack
- OpsCollectionPipelineRoleStack

Finally, delete the CDKToolkit CloudFormation stack to remove the CDK resources. 


## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

## Security

See [CONTRIBUTING](https://github.com/aws-samples/amazon-keyspaces-opensearch-integration/blob/main/CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
