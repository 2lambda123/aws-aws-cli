# Copyright 2012-2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import logging
import os
import tempfile
import zipfile
import contextlib
import uuid
from awscli.compat import six

from six.moves.urllib.parse import urlparse, parse_qs
from contextlib import contextmanager
from awscli.customizations.cloudformation import exceptions
from awscli.customizations.cloudformation.yamlhelper import yaml_dump, \
    yaml_parse

LOG = logging.getLogger(__name__)


def is_path_value_valid(path):
    return isinstance(path, six.string_types)


def make_abs_path(directory, path):
    if is_path_value_valid(path) and not os.path.isabs(path):
        return os.path.normpath(os.path.join(directory, path))
    else:
        return path


def is_s3_url(url):
    try:
        parse_s3_url(url)
        return True
    except ValueError:
        return False


def is_local_folder(path):
    return is_path_value_valid(path) and os.path.isdir(path)


def is_local_file(path):
    return is_path_value_valid(path) and os.path.isfile(path)


def parse_s3_url(url,
                 bucket_name_property="Bucket",
                 object_key_property="Key",
                 version_property=None):

    if isinstance(url, six.string_types) \
            and url.startswith("s3://"):

        # Python < 2.7.10 don't parse query parameters from URI with custom
        # scheme such as s3://blah/blah. As a workaround, remove scheme
        # altogether to trigger the parser "s3://foo/bar?v=1" =>"//foo/bar?v=1"
        parsed = urlparse(url[3:])
        query = parse_qs(parsed.query)

        if parsed.netloc and parsed.path:
            result = dict()
            result[bucket_name_property] = parsed.netloc
            result[object_key_property] = parsed.path.lstrip('/')

            # If there is a query string that has a single versionId field,
            # set the object version and return
            if version_property is not None \
                    and 'versionId' in query \
                    and len(query['versionId']) == 1:
                result[version_property] = query['versionId'][0]

            return result

    raise ValueError("URL given to the parse method is not a valid S3 url "
                     "{0}".format(url))


def upload_local_artifacts(resource_id, resource_dict, property_name,
                           parent_dir, uploader):
    """
    Upload local artifacts referenced by the property at given resource and
    return S3 URL of the uploaded object. It is the responsibility of callers
    to ensure property value is a valid string

    If path refers to a file, this method will upload the file. If path refers
    to a folder, this method will zip the folder and upload the zip to S3.
    If path is omitted, this method will zip the current working folder and
    upload.

    If path is already a path to S3 object, this method does nothing.

    :param resource_id:     Id of the CloudFormation resource
    :param resource_dict:   Dictionary containing resource definition
    :param property_name:   Property name of CloudFormation resource where this
                            local path is present
    :param parent_dir:      Resolve all relative paths with respect to this
                            directory
    :param uploader:        Method to upload files to S3

    :return:                S3 URL of the uploaded object
    :raise:                 ValueError if path is not a S3 URL or a local path
    """

    local_path = resource_dict.get(property_name, None)

    if local_path is None:
        # Build the root directory and upload to S3
        local_path = parent_dir

    if is_s3_url(local_path):
        # A valid CloudFormation template will specify artifacts as S3 URLs.
        # This check is supporting the case where your resource does not
        # refer to local artifacts
        # Nothing to do if property value is an S3 URL
        LOG.debug("Property {0} of {1} is already a S3 URL"
                  .format(property_name, resource_id))
        return local_path

    local_path = make_abs_path(parent_dir, local_path)

    # Or, pointing to a folder. Zip the folder and upload
    if is_local_folder(local_path):
        return zip_and_upload(local_path, uploader)

    # Path could be pointing to a file. Upload the file
    elif is_local_file(local_path):
        return uploader.upload_with_dedup(local_path)

    raise exceptions.InvalidLocalPathError(
            resource_id=resource_id,
            property_name=property_name,
            local_path=local_path)


def zip_and_upload(local_path, uploader):
    with zip_folder(local_path) as zipfile:
            return uploader.upload_with_dedup(zipfile)


@contextmanager
def zip_folder(folder_path):
    """
    Zip the entire folder and return a file to the zip. Use this inside
    a "with" statement to cleanup the zipfile after it is used.

    :param folder_path:
    :return: Name of the zipfile
    """

    filename = os.path.join(
        tempfile.gettempdir(), "data-" + uuid.uuid4().hex)

    zipfile_name = make_zip(filename, folder_path)
    try:
        yield zipfile_name
    finally:
        if os.path.exists(zipfile_name):
            os.remove(zipfile_name)


def make_zip(filename, source_root):
    zipfile_name = "{0}.zip".format(filename)
    source_root = os.path.abspath(source_root)
    with open(zipfile_name, 'wb') as f:
        zip_file = zipfile.ZipFile(f, 'w', zipfile.ZIP_DEFLATED)
        with contextlib.closing(zip_file) as zf:
            for root, dirs, files in os.walk(source_root):
                for filename in files:
                    full_path = os.path.join(root, filename)
                    relative_path = os.path.relpath(
                        full_path, source_root)
                    zf.write(full_path, relative_path)

    return zipfile_name


@contextmanager
def mktempfile():
    directory = tempfile.gettempdir()
    filename = os.path.join(directory, uuid.uuid4().hex)

    try:
        with open(filename, "w+") as handle:
            yield handle
    finally:
        if os.path.exists(filename):
            os.remove(filename)


class Resource(object):
    """
    Base class representing a CloudFormation resource that can be exported
    """

    PROPERTY_NAME = None

    def __init__(self, uploader, template_params={}):
        self.uploader = uploader
        self.template_params = template_params

    def export(self, resource_id, resource_dict, parent_dir):
        if resource_dict is None:
            return

        property_value = resource_dict.get(self.PROPERTY_NAME, None)
        property_value = self.resolve_param_reference(property_value)
        if property_value:
            resource_dict[self.PROPERTY_NAME] = property_value

        if isinstance(property_value, dict):
            LOG.debug("Property {0} of {1} resource is not a URL"
                      .format(self.PROPERTY_NAME, resource_id))
            return

        try:
            self.do_export(resource_id, resource_dict, parent_dir)

        except Exception as ex:
            LOG.debug("Unable to export", exc_info=ex)
            raise exceptions.ExportFailedError(
                    resource_id=resource_id,
                    property_name=self.PROPERTY_NAME,
                    property_value=property_value,
                    ex=ex)

    def do_export(self, resource_id, resource_dict, parent_dir):
        """
        Default export action is to upload artifacts and set the property to
        S3 URL of the uploaded object
        """
        resource_dict[self.PROPERTY_NAME] = \
            upload_local_artifacts(resource_id, resource_dict,
                                   self.PROPERTY_NAME,
                                   parent_dir, self.uploader)

    def resolve_param_reference(self, property_value):
        """
        Resolves a reference to parameter in a property value

        :param property_value: string
        :return: value of the template parameter referenced by the property.
                 If the property is  not a Ref to a parameter the original
                 property value is returned.
        """
        if not isinstance(property_value, dict):
            # Not a intrinsic function
            return property_value

        ref = property_value.get("Ref", None)

        parameter = self.template_params.get(ref, None)

        # return property_value if parameter isn't a string
        if not isinstance(parameter, six.string_types):
            return property_value

        return parameter


class ResourceWithS3UrlDict(Resource):
    """
    Represents CloudFormation resources that need the S3 URL to be specified as
    an dict like {Bucket: "", Key: "", Version: ""}
    """

    BUCKET_NAME_PROPERTY = None
    OBJECT_KEY_PROPERTY = None
    VERSION_PROPERTY = None

    def do_export(self, resource_id, resource_dict, parent_dir):
        """
        Upload to S3 and set property to an dict representing the S3 url
        of the uploaded object
        """

        artifact_s3_url = \
            upload_local_artifacts(resource_id, resource_dict,
                                   self.PROPERTY_NAME,
                                   parent_dir, self.uploader)

        resource_dict[self.PROPERTY_NAME] = parse_s3_url(
                artifact_s3_url,
                bucket_name_property=self.BUCKET_NAME_PROPERTY,
                object_key_property=self.OBJECT_KEY_PROPERTY,
                version_property=self.VERSION_PROPERTY)


class ServerlessFunctionResource(Resource):
    PROPERTY_NAME = "CodeUri"


class ServerlessApiResource(Resource):
    PROPERTY_NAME = "DefinitionUri"


class LambdaFunctionResource(ResourceWithS3UrlDict):
    PROPERTY_NAME = "Code"
    BUCKET_NAME_PROPERTY = "S3Bucket"
    OBJECT_KEY_PROPERTY = "S3Key"
    VERSION_PROPERTY = "S3ObjectVersion"


class ApiGatewayRestApiResource(ResourceWithS3UrlDict):
    PROPERTY_NAME = "BodyS3Location"
    BUCKET_NAME_PROPERTY = "Bucket"
    OBJECT_KEY_PROPERTY = "Key"
    VERSION_PROPERTY = "Version"


class ElasticBeanstalkApplicationVersion(ResourceWithS3UrlDict):
    PROPERTY_NAME = "SourceBundle"
    BUCKET_NAME_PROPERTY = "S3Bucket"
    OBJECT_KEY_PROPERTY = "S3Key"
    VERSION_PROPERTY = None


class CloudFormationStackResource(Resource):
    """
    Represents CloudFormation::Stack resource that can refer to a nested
    stack template via TemplateURL property.
    """
    PROPERTY_NAME = "TemplateURL"

    def do_export(self, resource_id, resource_dict, parent_dir):
        """
        If the nested stack template is valid, this method will
        export on the nested template, upload the exported template to S3
        and set property to URL of the uploaded S3 template
        """

        template_path = resource_dict.get(self.PROPERTY_NAME, None)

        if template_path is None or is_s3_url(template_path):
            # Nothing to do
            return

        abs_template_path = make_abs_path(parent_dir, template_path)
        if not is_local_file(abs_template_path):
            raise exceptions.InvalidTemplateUrlParameterError(
                    property_name=self.PROPERTY_NAME,
                    resource_id=resource_id,
                    template_path=abs_template_path)

        stack_params = self.get_params(resource_dict, parent_dir)

        exported_template_dict = \
            Template(template_path, parent_dir, self.uploader, template_params=stack_params).export()

        exported_template_str = yaml_dump(exported_template_dict)

        with mktempfile() as temporary_file:
            temporary_file.write(exported_template_str)
            temporary_file.flush()

            url = self.uploader.upload_with_dedup(
                    temporary_file.name, "template")

            resource_dict[self.PROPERTY_NAME] = url

    def get_params(self, resource_dict, parent_dir):
        """
        Parses the Parameters resource, resolves them to the template parameters and
        makes them an absolute path relative to the current template's parent directory

        :param resource_dict: dict
        :param parent_dir: dict
        :return: dict of parsed parameters and their values
        """
        parameters = resource_dict.get("Parameters", {})

        for parameter_id, parameter in parameters.items():
            # resolve reference to template parameter
            parameter = self.resolve_param_reference(parameter)

            # make any path passed to stack relative to the current template
            parameters[parameter_id] = make_abs_path(parent_dir, parameter)

        return parameters


EXPORT_DICT = {
    "AWS::Serverless::Function": ServerlessFunctionResource,
    "AWS::Serverless::Api": ServerlessApiResource,
    "AWS::ApiGateway::RestApi": ApiGatewayRestApiResource,
    "AWS::Lambda::Function": LambdaFunctionResource,
    "AWS::ElasticBeanstalk::ApplicationVersion":
        ElasticBeanstalkApplicationVersion,
    "AWS::CloudFormation::Stack": CloudFormationStackResource
}


class Template(object):
    """
    Class to export a CloudFormation template
    """

    def __init__(self, template_path, parent_dir, uploader,
                 resources_to_export=EXPORT_DICT, template_params={}):
        """
        Reads the template and makes it ready for export
        """

        if not (is_local_folder(parent_dir) and os.path.isabs(parent_dir)):
            raise ValueError("parent_dir parameter must be "
                             "an absolute path to a folder {0}"
                             .format(parent_dir))

        abs_template_path = make_abs_path(parent_dir, template_path)
        template_dir = os.path.dirname(abs_template_path)

        with open(abs_template_path, "r") as handle:
            template_str = handle.read()

        self.template_dict = yaml_parse(template_str)
        self.template_dir = template_dir
        self.resources_to_export = resources_to_export
        self.uploader = uploader
        self.template_params = template_params

    def export(self):
        """
        Exports the local artifacts referenced by the given template to an
        s3 bucket.

        :return: The template with references to artifacts that have been
        exported to s3.
        """
        if "Resources" not in self.template_dict:
            return self.template_dict

        for resource_id, resource in self.template_dict["Resources"].items():

            resource_type = resource.get("Type", None)
            resource_dict = resource.get("Properties", None)

            if resource_type in self.resources_to_export:
                # Export code resources
                exporter = self.resources_to_export[resource_type](
                        self.uploader, self.template_params)
                exporter.export(resource_id, resource_dict, self.template_dir)

        return self.template_dict
