# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
"""
This customization allows the user to specify the values "tcp", "udp",
or "icmp" as values for the --protocol parameter.  The actual Protocol
parameter of the operation accepts only integer protocol numbers.
"""

def _fix_args(operation, endpoint, params, **kwargs):
    if 'protocol' in params:
        if params['protocol'] == 'tcp':
            params['protocol'] = '6'
        elif params['protocol'] == 'udp':
            params['protocol'] = '17'
        elif params['protocol'] == 'icmp':
            params['protocol'] = '1'
        elif params['protocol'] == 'all':
            params['protocol'] = '-1'


def register_protocol_args(cli):
    ('before-parameter-build.ec2.RunInstances', _fix_args),
    cli.register('before-parameter-build.ec2.CreateNetworkAclEntry',
                 _fix_args)
    
