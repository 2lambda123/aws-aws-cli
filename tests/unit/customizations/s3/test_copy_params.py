#!/usr/bin/env python
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os
import sys

from awscli.testutils import BaseAWSCommandParamsTest

if sys.version_info[:2] == (2, 6):
    pass


# file is gone in python3, so instead IOBase must be used.
# Given this test module is the only place that cares about
# this type check, we do the check directly in this test module.
try:
    file_type = file
except NameError:
    import io

    file_type = io.IOBase


class TestGetObject(BaseAWSCommandParamsTest):
    prefix = 's3 cp '

    def setUp(self):
        super(TestGetObject, self).setUp()
        self.file_path = os.path.join(
            os.path.dirname(__file__), 'test_copy_params_data'
        )
        self.parsed_response = {
            'ETag': '"120ea8a25e5d487bf68b5f7096440019"',
        }

    def assert_params(self, cmdline, result):
        foo = self.assert_params_for_cmd(
            cmdline, result, expected_rc=0, ignore_params=['Body']
        )

    def test_simple(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        result = {'Bucket': 'mybucket', 'Key': 'mykey'}
        self.assert_params(cmdline, result)

    def test_sse(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --sse'
        result = {
            'Bucket': 'mybucket',
            'Key': 'mykey',
            'ServerSideEncryption': 'AES256',
        }
        self.assert_params(cmdline, result)

    def test_storage_class(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --storage-class REDUCED_REDUNDANCY'
        result = {
            'Bucket': 'mybucket',
            'Key': 'mykey',
            'StorageClass': 'REDUCED_REDUNDANCY',
        }
        self.assert_params(cmdline, result)

    def test_standard_ia_storage_class(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --storage-class STANDARD_IA'
        result = {
            'Bucket': 'mybucket',
            'Key': 'mykey',
            'StorageClass': 'STANDARD_IA',
        }
        self.assert_params(cmdline, result)

    def test_glacier_ir_storage_class(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --storage-class GLACIER_IR'
        result = {
            'Bucket': 'mybucket',
            'Key': 'mykey',
            'StorageClass': 'GLACIER_IR',
        }
        self.assert_params(cmdline, result)

    def test_website_redirect(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --website-redirect /foobar'
        result = {
            'Bucket': 'mybucket',
            'Key': 'mykey',
            'WebsiteRedirectLocation': '/foobar',
        }
        self.assert_params(cmdline, result)

    def test_acl(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --acl public-read'
        result = {'Bucket': 'mybucket', 'Key': 'mykey', 'ACL': 'public-read'}
        self.assert_params(cmdline, result)

    def test_content_params(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --content-encoding x-gzip'
        cmdline += ' --content-language piglatin'
        cmdline += ' --cache-control max-age=3600,must-revalidate'
        cmdline += ' --content-disposition attachment;filename="fname.ext"'
        result = {
            'Bucket': 'mybucket',
            'Key': 'mykey',
            'ContentEncoding': 'x-gzip',
            'ContentLanguage': 'piglatin',
            'ContentDisposition': 'attachment;filename="fname.ext"',
            'CacheControl': 'max-age=3600,must-revalidate',
        }
        self.assert_params(cmdline, result)

    def test_grants(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --grants read=bob'
        cmdline += ' full=alice'
        result = {
            'Bucket': 'mybucket',
            'GrantFullControl': 'alice',
            'GrantRead': 'bob',
            'Key': 'mykey',
        }
        self.assert_params(cmdline, result)

    def test_grants_bad(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --grants read:bob'
        self.assert_params_for_cmd(
            cmdline, expected_rc=1, ignore_params=['Payload']
        )

    def test_content_type(self):
        cmdline = self.prefix
        cmdline += self.file_path
        cmdline += ' s3://mybucket/mykey'
        cmdline += ' --content-type text/xml'
        result = {
            'Bucket': 'mybucket',
            'ContentType': 'text/xml',
            'Key': 'mykey',
        }
        self.assert_params(cmdline, result)


if __name__ == "__main__":
    unittest.main()
