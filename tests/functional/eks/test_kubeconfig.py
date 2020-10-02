# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import os
import shutil
import tempfile
import mock

from botocore.compat import OrderedDict

from awscli.testutils import unittest
from tests.functional.eks.test_util import get_testdata
from awscli.customizations.eks.kubeconfig import (_get_new_kubeconfig_content,
                                                  KubeconfigWriter,
                                                  KubeconfigLoader,
                                                  KubeconfigValidator,
                                                  Kubeconfig,
                                                  KubeconfigInaccessibleError,
                                                  KubeconfigCorruptedError)
class TestKubeconfigWriter(unittest.TestCase):
    def setUp(self):
        self._writer = KubeconfigWriter()

    def test_write_order(self):
        content = OrderedDict([
            ("current-context", "context"),
            ("apiVersion", "v1")
        ])
        tempdir = tempfile.mkdtemp()
        file_to_write = os.path.join(tempdir, 'config')
        original_permissions = 0o0755
        os.close(os.open(file_to_write, os.O_CREAT, original_permissions))
        self.addCleanup(shutil.rmtree, tempdir)

        config = Kubeconfig(file_to_write, content)
        self._writer.write_kubeconfig(config)

        self.assertEqual(self._get_file_permissions(file_to_write), original_permissions)
        with open(file_to_write, 'r') as stream:
            self.assertMultiLineEqual(stream.read(),
                                      "current-context: context\n"
                                      "apiVersion: v1\n")

    def test_write_makedirs(self):
        content = OrderedDict([
            ("current-context", "context"),
            ("apiVersion", "v1")
        ])
        containing_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, containing_dir)
        config_path = os.path.join(containing_dir,
                                   "dir1",
                                   "dir2",
                                   "dir3")

        config = Kubeconfig(config_path, content)
        self._writer.write_kubeconfig(config)

        self.assertEqual(self._get_file_permissions(config_path), 0o600)
        with open(config_path, 'r') as stream:
            self.assertMultiLineEqual(stream.read(),
                                      "current-context: context\n"
                                      "apiVersion: v1\n")

    def test_failure_makedirs(self):
        content = OrderedDict([
            ("current-context", "context"),
            ("apiVersion", "v1")
        ])
        too_long_path = 10000 * 'l' + '/dir/config'

        config = Kubeconfig(too_long_path, content)
        self.assertRaises(KubeconfigInaccessibleError,
                          self._writer.write_kubeconfig,
                          config)


    def test_write_directory(self):
        content = OrderedDict([
            ("current-context", "context"),
            ("apiVersion", "v1")
        ])
        containing_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, containing_dir)

        config = Kubeconfig(containing_dir, content)
        self.assertRaises(KubeconfigInaccessibleError,
                          self._writer.write_kubeconfig,
                          config)

    @staticmethod
    def _get_file_permissions(path):
        # From octal |type|SSS|USR|GRP|OTH| gets value of last 3 octal digits
        # which represents permissions for user, group, other.
        return os.stat(path).st_mode & 0o777

class TestKubeconfigLoader(unittest.TestCase):
    def setUp(self):
        # This mock validator allows all kubeconfigs.
        self._validator = mock.Mock(spec=KubeconfigValidator)
        self._loader = KubeconfigLoader(self._validator)

        self._temp_directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._temp_directory)

    def _clone_config(self, config):
        """
        Copies the testdata named config into the temp directory,
        Returns the new path

        :param config: The name of the testdata to copy
        :type config: str
        """
        old_path = os.path.abspath(get_testdata(config))
        new_path = os.path.join(self._temp_directory, config)
        shutil.copy2(old_path,
                     new_path)
        return new_path

    def test_load_simple(self):
        simple_path = self._clone_config("valid_simple")
        content = OrderedDict([
            ("apiVersion", "v1"),
            ("clusters", [
                OrderedDict([
                    ("cluster", OrderedDict([
                        ("server", "simple")
                    ])),
                    ("name", "simple")
                ])
            ]),
            ("contexts", None),
            ("current-context", "simple"),
            ("kind", "Config"),
            ("preferences", OrderedDict()),
            ("users", None)
        ])
        loaded_config = self._loader.load_kubeconfig(simple_path)
        self.assertEqual(loaded_config.content, content)
        self._validator.validate_config.called_with(Kubeconfig(simple_path,
                                                               content))

    def test_load_noexist(self):
        no_exist_path = os.path.join(self._temp_directory,
                                     "this_does_not_exist")
        loaded_config = self._loader.load_kubeconfig(no_exist_path)
        self.assertEqual(loaded_config.content,
                         _get_new_kubeconfig_content())
        self._validator.validate_config.called_with(
            Kubeconfig(no_exist_path, _get_new_kubeconfig_content()))

    def test_load_empty(self):
        empty_path = self._clone_config("valid_empty_existing")
        loaded_config = self._loader.load_kubeconfig(empty_path)
        self.assertEqual(loaded_config.content,
                         _get_new_kubeconfig_content())
        self._validator.validate_config.called_with(
            Kubeconfig(empty_path,
                       _get_new_kubeconfig_content()))

    def test_load_invalid(self):
        invalid_path = self._clone_config("non_parsable_yaml")
        self.assertRaises(KubeconfigCorruptedError,
                          self._loader.load_kubeconfig,
                          invalid_path)
        self._validator.validate_config.assert_not_called()

    def test_load_directory(self):
        current_directory = self._temp_directory
        self.assertRaises(KubeconfigInaccessibleError,
                          self._loader.load_kubeconfig,
                          current_directory)
        self._validator.validate_config.assert_not_called()
