# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import re
import os
import random
import time
import json

import pytest

from awscli.testutils import aws

INTEG_TESTS_DIR = os.path.dirname(os.path.join(os.path.abspath(__file__)))

with open(os.path.join(INTEG_TESTS_DIR, "smoke-test.json"), "r") as definitions_file:
    SMOKE_TESTS = json.load(definitions_file)
    COMMANDS = [" ".join(SMOKE_TESTS["Commands"][i]) for i in range(len(SMOKE_TESTS["Commands"]))]
    ERROR_COMMANDS = [" ".join(SMOKE_TESTS["ErrorCommands"][i]) for i in range(len(SMOKE_TESTS["ErrorCommands"]))]
REGION_OVERRIDES = SMOKE_TESTS.get("RegionOverrides", {})


def _aws(command_string, max_attempts=1, delay=5, target_rc=0):
    service = command_string.split()[0]
    env = None
    if service in REGION_OVERRIDES:
        env = os.environ.copy()
        env['AWS_DEFAULT_REGION'] = REGION_OVERRIDES[service]

    for _ in range(max_attempts - 1):
        result = aws(command_string, env_vars=env)
        if result.rc == target_rc:
            return result
        time.sleep(delay)
    return aws(command_string, env_vars=env)


@pytest.mark.parametrize(
    "cmd",
    COMMANDS
)
def test_can_make_success_request(cmd):
    result = _aws(cmd, max_attempts=5, delay=5, target_rc=0)
    assert result.rc == 0
    assert result.stderr == ''


ERROR_MESSAGE_RE = re.compile(
    r'An error occurred \(.+\) when calling the \w+ operation: \w+'
)


@pytest.mark.parametrize(
    "cmd",
    ERROR_COMMANDS
)
def test_display_error_message(cmd):
    result = _aws(cmd, target_rc=255)
    assert result.rc == 255

    match = ERROR_MESSAGE_RE.search(result.stderr)
    assert match is not None, (
        f'Error message was not displayed for command "{cmd}": {result.stderr}'
    )
