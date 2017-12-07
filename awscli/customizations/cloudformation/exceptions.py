
class CloudFormationCommandError(Exception):
    fmt = 'An unspecified error occurred'

    def __init__(self, **kwargs):
        msg = self.fmt.format(**kwargs)
        Exception.__init__(self, msg)
        self.kwargs = kwargs


class InvalidTemplatePathError(CloudFormationCommandError):
    fmt = "Invalid template path {template_path}"


class ChangeEmptyError(CloudFormationCommandError):
    fmt = "No changes to deploy. Stack {stack_name} is up to date"


class InvalidLocalPathError(CloudFormationCommandError):
    fmt = ("Parameter {property_name} of resource {resource_id} refers "
           "to a file or folder that does not exist {local_path}")


class InvalidTemplateUrlParameterError(CloudFormationCommandError):
    fmt = ("{property_name} parameter of {resource_id} resource is invalid. "
           "It must be a S3 URL or path to CloudFormation "
           "template file. Actual: {template_path}")


class ExportFailedError(CloudFormationCommandError):
    fmt = ("Unable to upload artifact {property_value} referenced "
           "by {property_name} parameter of {resource_id} resource."
           "\n"
           "{ex}")


class InvalidParameterOverrideArgumentError(CloudFormationCommandError):
    fmt = ("{value} value passed to --{argname} must be of format "
           "ParameterKey=ParameterValue")


class DeployFailedError(CloudFormationCommandError):
    fmt = \
        ("Failed to create/update the stack. Run the following command"
         "\n"
         "to fetch the list of events leading up to the failure"
         "\n"
         "aws cloudformation describe-stack-events --stack-name {stack_name}")


class PackageFailedRegionMismatchError(CloudFormationCommandError):
    fmt = \
        ("Failed to create package as deployment and S3 bucket region mismatch"
         "\n\n"
         "\tS3 Bucket region: {bucket_region}"
         "\n"
         "\tDeployment region: {deploy_region}")
