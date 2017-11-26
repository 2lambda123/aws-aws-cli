# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import argparse
import os

from botocore.session import Session
from botocore.history import HistoryRecorder

from awscli.testutils import unittest, mock, FileCreator
from awscli.customizations.history import attach_history_handler
from awscli.customizations.history import add_history_commands
from awscli.customizations.history import HistoryCommand
from awscli.customizations.history.db import DatabaseHistoryHandler


class TestAttachHistoryHander(unittest.TestCase):
    def setUp(self):
        self.files = FileCreator()

    def tearDown(self):
        self.files.remove_all()

    @mock.patch('awscli.customizations.history.sqlite3')
    @mock.patch('awscli.customizations.history.get_global_history_recorder')
    def test_attach_history_handler(self, mock_get_recorder, mock_sqlite3):
        mock_session = mock.Mock(Session)
        mock_session.get_scoped_config.return_value = {
            'cli_history': 'enabled'
        }

        parsed_args = argparse.Namespace()
        parsed_args.command = 's3'

        mock_recorder = mock.Mock(HistoryRecorder)
        mock_get_recorder.return_value = mock_recorder

        attach_history_handler(session=mock_session, parsed_args=parsed_args)
        self.assertEqual(mock_recorder.add_handler.call_count, 1)
        self.assertIsInstance(
            mock_recorder.add_handler.call_args[0][0], DatabaseHistoryHandler)

    @mock.patch('awscli.customizations.history.sqlite3')
    @mock.patch('awscli.customizations.history.get_global_history_recorder')
    def test_no_attach_history_handler_when_history_not_configured(
            self, mock_get_recorder, mock_sqlite3):
        mock_session = mock.Mock(Session)
        mock_session.get_scoped_config.return_value = {}

        parsed_args = argparse.Namespace()
        parsed_args.command = 's3'

        attach_history_handler(session=mock_session, parsed_args=parsed_args)
        self.assertFalse(mock_get_recorder.called)

    @mock.patch('awscli.customizations.history.sqlite3')
    @mock.patch('awscli.customizations.history.get_global_history_recorder')
    def test_no_attach_history_handler_when_command_is_history(
            self, mock_get_recorder, mock_sqlite3):
        mock_session = mock.Mock(Session)
        mock_session.get_scoped_config.return_value = {
            'cli_history': 'enabled'
        }

        parsed_args = argparse.Namespace()
        parsed_args.command = 'history'

        attach_history_handler(session=mock_session, parsed_args=parsed_args)
        self.assertFalse(mock_get_recorder.called)

    @mock.patch('awscli.customizations.history.sqlite3', None)
    @mock.patch('awscli.customizations.history.get_global_history_recorder')
    def test_no_attach_history_handler_when_no_sqlite3(
            self, mock_get_recorder):
        mock_session = mock.Mock(Session)
        mock_session.get_scoped_config.return_value = {
            'cli_history': 'enabled'
        }

        parsed_args = argparse.Namespace()
        parsed_args.command = 's3'

        attach_history_handler(session=mock_session, parsed_args=parsed_args)
        self.assertFalse(mock_get_recorder.called)

    @mock.patch('awscli.customizations.history.sqlite3')
    @mock.patch('awscli.customizations.history.get_global_history_recorder')
    def test_create_directory_no_exists(self, mock_get_recorder, mock_sqlite3):
        mock_session = mock.Mock(Session)
        mock_session.get_scoped_config.return_value = {
            'cli_history': 'enabled'
        }

        parsed_args = argparse.Namespace()
        parsed_args.command = 's3'

        mock_recorder = mock.Mock(HistoryRecorder)
        mock_get_recorder.return_value = mock_recorder

        directory_to_create = os.path.join(self.files.rootdir, 'create-dir')
        db_filename = os.path.join(directory_to_create, 'name.db')
        with mock.patch('os.environ', {'AWS_CLI_HISTORY_FILE': db_filename}):
            attach_history_handler(
                session=mock_session, parsed_args=parsed_args)
            self.assertEqual(mock_recorder.add_handler.call_count, 1)
            # Is should create any missing parent directories of the
            # file as well.
            self.assertTrue(os.path.exists(directory_to_create))


class TestAddHistoryCommand(unittest.TestCase):
    def test_add_history_command(self):
        command_table = {}
        mock_session = mock.Mock(Session)
        add_history_commands(
            command_table=command_table, session=mock_session)
        self.assertIn('history', command_table)
        self.assertIsInstance(command_table['history'], HistoryCommand)


class TestHistoryCommand(unittest.TestCase):
    def test_requires_subcommand(self):
        mock_session = mock.Mock(Session)
        history_command = HistoryCommand(mock_session)
        parsed_args = argparse.Namespace()
        parsed_args.subcommand = None
        parsed_globals = argparse.Namespace()
        with self.assertRaises(ValueError):
            history_command._run_main(parsed_args, parsed_globals)
