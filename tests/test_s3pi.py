#!/usr/bin/env python3
"""Tests for the s3pi module"""
import os.path
import random
import string
import tempfile
import unittest

import s3pi


class CreateIndexTest(unittest.TestCase):
    """Test Case for s3pi.create_index()"""

    def setUp(self):
        """Sets up function arguments"""
        self.temporary_directory = tempfile.TemporaryDirectory()

    def tearDown(self):
        """Tears down function arguments"""
        self.temporary_directory.cleanup()

    def test_create_root(self):
        """Tests that an index.html file is created at the directory root"""
        index = s3pi.create_index(self.temporary_directory.name, root=True)

        self.assertEqual(
            os.path.join(self.temporary_directory.name, 'index.html'),
            index,
        )
        self.assertTrue(os.path.exists(index))

    def test_create_package(self):
        """Tests that an index.html file is created at the package root"""
        filename = 'sample-1.0.whl'
        index = s3pi.create_index(
            self.temporary_directory.name,
            filename=filename,
            root=False,
        )

        self.assertEqual(
            os.path.join(self.temporary_directory.name, 'index.html'),
            index,
        )
        self.assertTrue(os.path.exists(index))

    def test_create_nothing(self):
        """Tests that an index.html file is not created without a filename"""
        index = s3pi.create_index(self.temporary_directory.name, root=False)

        self.assertIsNone(index)
        self.assertFalse(os.path.exists(os.path.join(
            self.temporary_directory.name,
            'index.html',
        )))


class EnsureTrailingSlashTest(unittest.TestCase):
    """Test Case for s3pi.ensure_ends_with_slash()"""

    def test_non_trailing_slash(self):
        """Tests that a string without a trailing slash gets one"""
        old_string = ''.join(
            tuple(random.choice(string.ascii_lowercase) for _ in range(18))
        )
        new_string = s3pi.ensure_ends_with_slash(old_string)

        self.assertEqual('{}/'.format(old_string), new_string)

    def test_trailing_slash(self):
        """Tests that a string with a trailing slash stays the same"""
        old_string = '{}/'.format(''.join(
            tuple(random.choice(string.ascii_lowercase) for _ in range(18))
        ))
        new_string = s3pi.ensure_ends_with_slash(old_string)

        self.assertEqual(old_string, new_string)


class LoadSettingsTest(unittest.TestCase):
    """Test Case for s3pi.load_settings()"""

    def setUp(self):
        """Sets up function arguments"""
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.config = os.path.join(self.temporary_directory.name, 'config')

    def tearDown(self):
        """Tears down function arguments"""
        self.temporary_directory.cleanup()

    def test_default_section(self):
        """Tests that a config with the default section loads"""
        with open(self.config, 'w') as config_file:
            config_file.writelines((
                '[default]\n',
                'section.name=default\n',
            ))

        settings = s3pi.load_settings(self.config)

        self.assertEqual('default', settings.get('section.name'))

    def test_other_section(self):
        """Tests that a config without the default section loads"""
        with open(self.config, 'w') as config_file:
            config_file.writelines((
                '[other]\n',
                'section.name=other\n',
            ))

        settings = s3pi.load_settings(self.config)

        self.assertEqual('other', settings.get('section.name'))

    def test_no_config(self):
        """Tests that no config loads instance defaults"""
        settings = s3pi.load_settings(self.config)

        self.assertNotEqual(0, len(settings.keys()))
