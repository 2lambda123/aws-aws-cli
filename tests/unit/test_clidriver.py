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
from tests import unittest
import sys

import mock
import six

from awscli.clidriver import CLIDriver
from botocore.hooks import HierarchicalEmitter, EventHooks


GET_DATA = {
    'cli': {
        'description': 'description',
        'options': {
            "service_name": {
                "choices": "{provider}/_services",
                "metavar": "service_name"
            },
            "--debug": {
                "action": "store_true",
                "help": "Turn on debug logging"
            },
            "--output": {
                "choices": [
                    "json",
                    "text",
                    "table"
                ],
                "metavar": "output_format"
            },
            "--profile": {
                "help": "Use a specific profile from your credential file",
                "metavar": "profile_name"
            },
            "--region": {
                "choices": "{provider}/_regions",
                "metavar": "region_name"
            },
            "--endpoint-url": {
                "help": "Override service's default URL with the given URL",
                "metavar": "endpoint_url"
            },
            "--no-verify-ssl": {
                "action": "store_true",
                "help": "Override default behavior of verifying SSL certificates"
            },
            "--no-paginate": {
                "action": "store_false",
                "help": "Disable automatic pagination",
                "dest": "paginate"
            },
        }
    },
    'aws/_services': {'s3':{}},
    'aws/_regions': {},
}

GET_VARIABLE = {
    'provider': 'aws',
    'output': 'json',
}


class FakeSession(object):
    def __init__(self, emitter=None):
        self.operation = None
        if emitter is None:
            emitter = HierarchicalEmitter(EventHooks())
        self.emitter = emitter

    def register(self, event_name, handler):
        self.emitter.register(event_name, handler)

    def emit(self, event_name, **kwargs):
        return self.emitter.emit(event_name, **kwargs)

    def get_data(self, name):
        return GET_DATA[name]

    def get_variable(self, name):
        return GET_VARIABLE[name]

    def get_service(self, name):
        # Get service returns a service object,
        # so we'll just return a Mock object with
        # enough of the "right stuff".
        service = mock.Mock()
        list_objects = mock.Mock(name='operation')
        list_objects.cli_name = 'list-objects'
        list_objects.params = []
        operation = mock.Mock()
        param = mock.Mock()
        param.type = 'string'
        param.py_name = 'bucket'
        param.cli_name = '--bucket'
        operation.params = [param]
        operation.cli_name = 'list-objects'
        operation.is_streaming.return_value = False
        operation.paginate.return_value.build_full_result.return_value = {
            'foo': 'paginate'}
        operation.call.return_value = (mock.Mock(), {'foo': 'bar'})
        self.operation = operation
        service.operations = [list_objects]
        service.cli_name = 's3'
        service.get_operation.return_value = operation
        return service

    def user_agent(self):
        return 'user_agent'


class TestCliDriver(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()

    def test_session_can_be_passed_in(self):
        driver = CLIDriver(session=self.session)
        self.assertEqual(driver.session, self.session)

    def test_call(self):
        driver = CLIDriver(session=self.session)
        rc = driver.main('s3 list-objects --bucket foo'.split())
        self.assertEqual(rc, 0)


class TestCliDriverHooks(unittest.TestCase):
    # These tests verify the proper hooks are emitted in clidriver.
    def setUp(self):
        self.session = FakeSession()
        self.emitter = mock.Mock()
        self.emitter.emit.return_value = []
        self.stdout = six.StringIO()
        self.stderr = six.StringIO()
        self.stdout_patch = mock.patch('sys.stdout', self.stdout)
        self.stdout_patch.start()
        self.stderr_patch = mock.patch('sys.stderr', self.stderr)
        self.stderr_patch.start()

    def tearDown(self):
        self.stdout_patch.stop()
        self.stderr_patch.stop()

    def assert_events_fired_in_order(self, events):
        args = self.emitter.emit.call_args_list
        actual_events = [arg[0][0] for arg in args]
        self.assertEqual(actual_events, events)

    def serialize_param(self, param, value, **kwargs):
        if param.py_name == 'bucket':
            return value + '-altered!'

    def test_expected_events_are_emitted_in_order(self):
        self.emitter.emit.return_value = []
        self.session.emitter = self.emitter
        driver = CLIDriver(session=self.session)
        driver.main('s3 list-objects --bucket foo'.split())
        self.assert_events_fired_in_order([
            # Events fired while parser is being created.
            'parser-created.main',
            'parser-created.s3',
            'parser-created.s3-list-objects',
            'process-cli-arg.s3.list-objects',
        ])

    def test_cli_driver_changes_args(self):
        emitter = HierarchicalEmitter(EventHooks())
        emitter.register('process-cli-arg.s3.list-objects', self.serialize_param)
        self.session.emitter = emitter
        driver = CLIDriver(session=self.session)
        driver.main('s3 list-objects --bucket foo'.split())
        self.assertIn(mock.call.paginate(mock.ANY, bucket='foo-altered!'),
                      self.session.operation.method_calls)

    def test_cli_driver_with_no_paginate(self):
        driver = CLIDriver(session=self.session)
        driver.main('s3 list-objects --bucket foo --no-paginate'.split())
        # Because --no-paginate was used, op.call should be used instead of
        # op.paginate.
        self.assertIn(mock.call.call(mock.ANY, bucket='foo'),
                      self.session.operation.method_calls)

    def test_unknown_params_raises_error(self):
        driver = CLIDriver(session=self.session)
        rc = driver.main('s3 list-objects --bucket foo --unknown-arg foo'.split())
        self.assertEqual(rc, 255)
        self.assertIn('Unknown options', self.stderr.getvalue())


if __name__ == '__main__':
    unittest.main()
