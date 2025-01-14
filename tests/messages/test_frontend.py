#
# Copyright (C) 2007-2011 Edgewall Software, 2013-2024 the Babel team
# All rights reserved.
#
# This software is licensed as described in the file LICENSE, which
# you should have received as part of this distribution. The terms
# are also available at https://github.com/python-babel/babel/blob/master/LICENSE.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at https://github.com/python-babel/babel/commits/master/.
import logging
import os
import re
import shlex
import shutil
import sys
import time
import unittest
from datetime import datetime, timedelta
from functools import partial
from io import BytesIO, StringIO
from typing import List

import pytest
from freezegun import freeze_time

from babel import __version__ as VERSION
from babel.dates import format_datetime
from babel.messages import Catalog, extract, frontend, pofile
from babel.messages.frontend import (
    BaseError,
    CommandLineInterface,
    ExtractMessages,
    OptionError,
    UpdateCatalog,
)
from babel.messages.pofile import read_po, write_po
from babel.util import LOCALTZ
from tests.messages.consts import (
    TEST_PROJECT_DISTRIBUTION_DATA,
    data_dir,
    i18n_dir,
    pot_file,
    project_dir,
    this_dir,
)
from tests.messages.utils import CUSTOM_EXTRACTOR_COOKIE


def _po_file(locale):
    return os.path.join(i18n_dir, locale, 'LC_MESSAGES', 'messages.po')


class Distribution:  # subset of distutils.dist.Distribution
    def __init__(self, attrs: dict) -> None:
        self.attrs = attrs

    def get_name(self) -> str:
        return self.attrs['name']

    def get_version(self) -> str:
        return self.attrs['version']

    @property
    def packages(self) -> List[str]:
        return self.attrs['packages']


class CompileCatalogTestCase(unittest.TestCase):

    def setUp(self):
        self.olddir = os.getcwd()
        os.chdir(data_dir)

        self.dist = Distribution(TEST_PROJECT_DISTRIBUTION_DATA)
        self.cmd = frontend.CompileCatalog(self.dist)
        self.cmd.initialize_options()

    def tearDown(self):
        os.chdir(self.olddir)

    def test_no_directory_or_output_file_specified(self):
        self.cmd.locale = 'en_US'
        self.cmd.input_file = 'dummy'
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

    def test_no_directory_or_input_file_specified(self):
        self.cmd.locale = 'en_US'
        self.cmd.output_file = 'dummy'
        with pytest.raises(OptionError):
            self.cmd.finalize_options()


class ExtractMessagesTestCase(unittest.TestCase):

    def setUp(self):
        self.olddir = os.getcwd()
        os.chdir(data_dir)

        self.dist = Distribution(TEST_PROJECT_DISTRIBUTION_DATA)
        self.cmd = frontend.ExtractMessages(self.dist)
        self.cmd.initialize_options()

    def tearDown(self):
        if os.path.isfile(pot_file):
            os.unlink(pot_file)

        os.chdir(self.olddir)

    def assert_pot_file_exists(self):
        assert os.path.isfile(pot_file)

    def test_neither_default_nor_custom_keywords(self):
        self.cmd.output_file = 'dummy'
        self.cmd.no_default_keywords = True
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

    def test_no_output_file_specified(self):
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

    def test_both_sort_output_and_sort_by_file(self):
        self.cmd.output_file = 'dummy'
        self.cmd.sort_output = True
        self.cmd.sort_by_file = True
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

    def test_invalid_file_or_dir_input_path(self):
        self.cmd.input_paths = 'nonexistent_path'
        self.cmd.output_file = 'dummy'
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

    def test_input_paths_is_treated_as_list(self):
        self.cmd.input_paths = data_dir
        self.cmd.output_file = pot_file
        self.cmd.finalize_options()
        self.cmd.run()

        with open(pot_file) as f:
            catalog = read_po(f)
        msg = catalog.get('bar')
        assert len(msg.locations) == 1
        assert ('file1.py' in msg.locations[0][0])

    def test_input_paths_handle_spaces_after_comma(self):
        self.cmd.input_paths = f"{this_dir},  {data_dir}"
        self.cmd.output_file = pot_file
        self.cmd.finalize_options()
        assert self.cmd.input_paths == [this_dir, data_dir]

    def test_input_dirs_is_alias_for_input_paths(self):
        self.cmd.input_dirs = this_dir
        self.cmd.output_file = pot_file
        self.cmd.finalize_options()
        # Gets listified in `finalize_options`:
        assert self.cmd.input_paths == [self.cmd.input_dirs]

    def test_input_dirs_is_mutually_exclusive_with_input_paths(self):
        self.cmd.input_dirs = this_dir
        self.cmd.input_paths = this_dir
        self.cmd.output_file = pot_file
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

    @freeze_time("1994-11-11")
    def test_extraction_with_default_mapping(self):
        self.cmd.copyright_holder = 'FooBar, Inc.'
        self.cmd.msgid_bugs_address = 'bugs.address@email.tld'
        self.cmd.output_file = 'project/i18n/temp.pot'
        self.cmd.add_comments = 'TRANSLATOR:,TRANSLATORS:'

        self.cmd.finalize_options()
        self.cmd.run()

        self.assert_pot_file_exists()

        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# Translations template for TestProject.
# Copyright (C) {time.strftime('%Y')} FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, {time.strftime('%Y')}.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: {date}\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. TRANSLATOR: This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

#: project/ignored/this_wont_normally_be_here.py:11
msgid "FooBar"
msgid_plural "FooBars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(pot_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_extraction_with_mapping_file(self):
        self.cmd.copyright_holder = 'FooBar, Inc.'
        self.cmd.msgid_bugs_address = 'bugs.address@email.tld'
        self.cmd.mapping_file = 'mapping.cfg'
        self.cmd.output_file = 'project/i18n/temp.pot'
        self.cmd.add_comments = 'TRANSLATOR:,TRANSLATORS:'

        self.cmd.finalize_options()
        self.cmd.run()

        self.assert_pot_file_exists()

        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# Translations template for TestProject.
# Copyright (C) {time.strftime('%Y')} FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, {time.strftime('%Y')}.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: {date}\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. TRANSLATOR: This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(pot_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_extraction_with_mapping_dict(self):
        self.dist.message_extractors = {
            'project': [
                ('**/ignored/**.*', 'ignore', None),
                ('**.py', 'python', None),
            ],
        }
        self.cmd.copyright_holder = 'FooBar, Inc.'
        self.cmd.msgid_bugs_address = 'bugs.address@email.tld'
        self.cmd.output_file = 'project/i18n/temp.pot'
        self.cmd.add_comments = 'TRANSLATOR:,TRANSLATORS:'

        self.cmd.finalize_options()
        self.cmd.run()

        self.assert_pot_file_exists()

        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# Translations template for TestProject.
# Copyright (C) {time.strftime('%Y')} FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, {time.strftime('%Y')}.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: {date}\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. TRANSLATOR: This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(pot_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    def test_extraction_add_location_file(self):
        self.dist.message_extractors = {
            'project': [
                ('**/ignored/**.*', 'ignore', None),
                ('**.py', 'python', None),
            ],
        }
        self.cmd.output_file = 'project/i18n/temp.pot'
        self.cmd.add_location = 'file'
        self.cmd.omit_header = True

        self.cmd.finalize_options()
        self.cmd.run()

        self.assert_pot_file_exists()

        expected_content = r"""#: project/file1.py
msgid "bar"
msgstr ""

#: project/file2.py
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(pot_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content


class InitCatalogTestCase(unittest.TestCase):

    def setUp(self):
        self.olddir = os.getcwd()
        os.chdir(data_dir)

        self.dist = Distribution(TEST_PROJECT_DISTRIBUTION_DATA)
        self.cmd = frontend.InitCatalog(self.dist)
        self.cmd.initialize_options()

    def tearDown(self):
        for dirname in ['en_US', 'ja_JP', 'lv_LV']:
            locale_dir = os.path.join(i18n_dir, dirname)
            if os.path.isdir(locale_dir):
                shutil.rmtree(locale_dir)

        os.chdir(self.olddir)

    def test_no_input_file(self):
        self.cmd.locale = 'en_US'
        self.cmd.output_file = 'dummy'
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

    def test_no_locale(self):
        self.cmd.input_file = 'dummy'
        self.cmd.output_file = 'dummy'
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

    @freeze_time("1994-11-11")
    def test_with_output_dir(self):
        self.cmd.input_file = 'project/i18n/messages.pot'
        self.cmd.locale = 'en_US'
        self.cmd.output_dir = 'project/i18n'

        self.cmd.finalize_options()
        self.cmd.run()

        po_file = _po_file('en_US')
        assert os.path.isfile(po_file)

        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# English (United States) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: {date}\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language: en_US\n"
"Language-Team: en_US <LL@li.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(po_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_keeps_catalog_non_fuzzy(self):
        self.cmd.input_file = 'project/i18n/messages_non_fuzzy.pot'
        self.cmd.locale = 'en_US'
        self.cmd.output_dir = 'project/i18n'

        self.cmd.finalize_options()
        self.cmd.run()

        po_file = _po_file('en_US')
        assert os.path.isfile(po_file)

        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# English (United States) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: {date}\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language: en_US\n"
"Language-Team: en_US <LL@li.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(po_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_correct_init_more_than_2_plurals(self):
        self.cmd.input_file = 'project/i18n/messages.pot'
        self.cmd.locale = 'lv_LV'
        self.cmd.output_dir = 'project/i18n'

        self.cmd.finalize_options()
        self.cmd.run()

        po_file = _po_file('lv_LV')
        assert os.path.isfile(po_file)

        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# Latvian (Latvia) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: {date}\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language: lv_LV\n"
"Language-Team: lv_LV <LL@li.org>\n"
"Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 :"
" 2);\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""
msgstr[2] ""

"""
        with open(po_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_correct_init_singular_plural_forms(self):
        self.cmd.input_file = 'project/i18n/messages.pot'
        self.cmd.locale = 'ja_JP'
        self.cmd.output_dir = 'project/i18n'

        self.cmd.finalize_options()
        self.cmd.run()

        po_file = _po_file('ja_JP')
        assert os.path.isfile(po_file)

        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='ja_JP')
        expected_content = fr"""# Japanese (Japan) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: {date}\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language: ja_JP\n"
"Language-Team: ja_JP <LL@li.org>\n"
"Plural-Forms: nplurals=1; plural=0;\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""

"""
        with open(po_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_supports_no_wrap(self):
        self.cmd.input_file = 'project/i18n/long_messages.pot'
        self.cmd.locale = 'en_US'
        self.cmd.output_dir = 'project/i18n'

        long_message = '"' + 'xxxxx ' * 15 + '"'

        with open('project/i18n/messages.pot', 'rb') as f:
            pot_contents = f.read().decode('latin-1')
        pot_with_very_long_line = pot_contents.replace('"bar"', long_message)
        with open(self.cmd.input_file, 'wb') as f:
            f.write(pot_with_very_long_line.encode('latin-1'))
        self.cmd.no_wrap = True

        self.cmd.finalize_options()
        self.cmd.run()

        po_file = _po_file('en_US')
        assert os.path.isfile(po_file)
        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en_US')
        expected_content = fr"""# English (United States) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: {date}\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language: en_US\n"
"Language-Team: en_US <LL@li.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid {long_message}
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(po_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_supports_width(self):
        self.cmd.input_file = 'project/i18n/long_messages.pot'
        self.cmd.locale = 'en_US'
        self.cmd.output_dir = 'project/i18n'

        long_message = '"' + 'xxxxx ' * 15 + '"'

        with open('project/i18n/messages.pot', 'rb') as f:
            pot_contents = f.read().decode('latin-1')
        pot_with_very_long_line = pot_contents.replace('"bar"', long_message)
        with open(self.cmd.input_file, 'wb') as f:
            f.write(pot_with_very_long_line.encode('latin-1'))
        self.cmd.width = 120
        self.cmd.finalize_options()
        self.cmd.run()

        po_file = _po_file('en_US')
        assert os.path.isfile(po_file)
        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en_US')
        expected_content = fr"""# English (United States) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: {date}\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language: en_US\n"
"Language-Team: en_US <LL@li.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid {long_message}
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(po_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content


class ConcatanationCatalogTestCase(unittest.TestCase):

    def setUp(self):
        self.olddir = os.getcwd()
        os.chdir(data_dir)

        self.dist = Distribution(TEST_PROJECT_DISTRIBUTION_DATA)
        self.cmd = frontend.ConcatenationCatalog(self.dist)
        self.cmd.initialize_options()

        self.temp1 = f'{i18n_dir}/msgcat_temp1.po'
        self.temp2 = f'{i18n_dir}/msgcat_temp2.po'
        self.output_file = f'{i18n_dir}/msgcat.po'

        with open(self.temp1, 'wb') as file:
            catalog = Catalog()
            catalog.add('other1', string='Other 1', locations=[('simple.py', 1)], flags=['flag1000'])
            catalog.add('other2', string='Other 2',  locations=[('simple.py', 10)])
            catalog.add('same', string='Same', locations=[('simple.py', 100)], flags=['flag1', 'flag1.2'])
            catalog.add('almost_same', string='Almost same', locations=[('simple.py', 1000)], flags=['flag2'])
            catalog.add(('plural', 'plurals'), string=('Plural', 'Plurals'), locations=[('simple.py', 2000)])
            pofile.write_po(file, catalog)

        with open(self.temp2, 'wb') as file:
            catalog = Catalog()
            catalog.add('other3', string='Other 3', locations=[('hard.py', 1)])
            catalog.add('other4', string='Other 4', locations=[('hard.py', 10)])
            catalog.add('almost_same', string='A bit same',  locations=[('hard.py', 1000)], flags=['flag3'])
            catalog.add('same', string='Same', locations=[('hard.py', 100)], flags=['flag4'])
            catalog.add(('plural', 'plurals'), string=('Plural', 'Plurals other'), locations=[('hard.py', 2000)])
            pofile.write_po(file, catalog)

    def tearDown(self):
        for file in [self.temp1, self.temp2, self.output_file]:
            if os.path.isfile(file):
                    os.unlink(file)

    def _get_expected(self, messages):
        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        return fr"""# Translations template for PROJECT.
# Copyright (C) 1994 ORGANIZATION
# This file is distributed under the same license as the PROJECT project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 1994.
#
msgid ""
msgstr ""
"Project-Id-Version: PROJECT VERSION\n"
"Report-Msgid-Bugs-To: EMAIL@ADDRESS\n"
"POT-Creation-Date: {date}\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

""" + messages

    def test_no_input_files(self):
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

    def test_no_output_file(self):
        self.cmd.input_files = ['project/i18n/messages.pot']
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

    @freeze_time("1994-11-11")
    def test_default(self):
        self.cmd.input_files = [self.temp1, self.temp2]
        self.cmd.output_file = self.output_file

        self.cmd.finalize_options()
        self.cmd.run()

        expected_content = self._get_expected(fr"""#: simple.py:1
#, flag1000
msgid "other1"
msgstr "Other 1"

#: simple.py:10
msgid "other2"
msgstr "Other 2"

#: hard.py:100 simple.py:100
#, flag1, flag1.2, flag4
msgid "same"
msgstr "Same"

#: hard.py:1000 simple.py:1000
#, flag2, flag3
msgid "almost_same"
msgstr "Almost same"

#: hard.py:2000 simple.py:2000
msgid "plural"
msgid_plural "plurals"
msgstr[0] "Plural"
msgstr[1] "Plurals"

#: hard.py:1
msgid "other3"
msgstr "Other 3"

#: hard.py:10
msgid "other4"
msgstr "Other 4"

""")

        with open(self.output_file, 'r') as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_unique(self):
        self.cmd.input_files = [self.temp1, self.temp2]
        self.cmd.output_file = self.output_file
        self.cmd.unique = True

        self.cmd.finalize_options()
        self.cmd.run()

        expected_content = self._get_expected(fr"""#: simple.py:1
#, flag1000
msgid "other1"
msgstr "Other 1"

#: simple.py:10
msgid "other2"
msgstr "Other 2"

#: hard.py:1
msgid "other3"
msgstr "Other 3"

#: hard.py:10
msgid "other4"
msgstr "Other 4"

""")

        with open(self.output_file, 'r') as f:
                actual_content = f.read()
        assert expected_content == actual_content

        self.cmd.less_than = 2
        self.cmd.finalize_options()
        self.cmd.run()

        with open(self.output_file, 'r') as f:
                actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_more_than(self):
        self.cmd.input_files = [self.temp1, self.temp2]
        self.cmd.output_file = self.output_file
        self.cmd.more_than = 1

        self.cmd.finalize_options()
        self.cmd.run()

        expected_content = self._get_expected(fr"""#: hard.py:100 simple.py:100
#, flag1, flag1.2, flag4
msgid "same"
msgstr "Same"

#: hard.py:1000 simple.py:1000
#, flag2, flag3
msgid "almost_same"
msgstr "Almost same"

#: hard.py:2000 simple.py:2000
msgid "plural"
msgid_plural "plurals"
msgstr[0] "Plural"
msgstr[1] "Plurals"

""")

        with open(self.output_file, 'r') as f:
            actual_content = f.read()
        assert expected_content == actual_content


class MergeCatalogTestCase(unittest.TestCase):

    @freeze_time("1994-11-11")
    def setUp(self):
        self.olddir = os.getcwd()
        os.chdir(data_dir)

        self.dist = Distribution(TEST_PROJECT_DISTRIBUTION_DATA)
        self.cmd = frontend.MergeCatalog(self.dist)
        self.cmd.initialize_options()

        self.temp_def = f'{i18n_dir}/msgmerge_def.po'
        self.temp_ref = f'{i18n_dir}/msgmerge_ref.pot'
        self.compendium = f'{i18n_dir}/compenidum.po'
        self.output_file = f'{i18n_dir}/msgmerge.po'

        with open(self.temp_ref, 'wb') as file:
            catalog = Catalog()
            for word in ['word1', 'word2', 'word3', 'word4']:
                catalog.add(word)
            pofile.write_po(file, catalog)

        with open(self.temp_def, 'wb') as file:
            catalog = Catalog()
            catalog.add('word1', string='Word 1')
            catalog.add('word2', string='Word 2')
            catalog.add('word3')
            pofile.write_po(file, catalog)

        with open(self.compendium, 'wb') as file:
            catalog = Catalog()
            catalog.add('word1', string='Comp Word 1')
            catalog.add('word2', string='Comp Word 2')
            catalog.add('word4', string='Word 4')
            catalog.add('word5', string='Word 5')
            pofile.write_po(file, catalog)

    def tearDown(self):
        for file in [
            self.temp_def,
            self.temp_def + '~',
            self.temp_def + '.bac',
            self.temp_ref,
            self.compendium,
            self.output_file
        ]:
            if os.path.exists(file) and os.path.isfile(file):
                    os.unlink(file)

    def _get_expected(self, messages):
        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        return fr"""# Translations template for PROJECT.
# Copyright (C) 1994 ORGANIZATION
# This file is distributed under the same license as the PROJECT project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 1994.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: PROJECT VERSION\n"
"Report-Msgid-Bugs-To: EMAIL@ADDRESS\n"
"POT-Creation-Date: {date}\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

""" + messages

    def test_no_input_files(self):
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

        with pytest.raises(OptionError):
            self.cmd.input_files = ['1']
            self.cmd.finalize_options()

        with pytest.raises(OptionError):
            self.cmd.input_files = ['1', '2', '3']
            self.cmd.finalize_options()

    def test_no_output_file(self):
        self.cmd.input_files = ['1', '2']
        with pytest.raises(OptionError):
            self.cmd.finalize_options()

        self.cmd.output_file = '2'
        self.cmd.finalize_options()

        self.cmd.output_file = None
        self.cmd.update = True
        self.cmd.finalize_options()


    @freeze_time("1994-11-11")
    def test_default(self):
        self.cmd.input_files = [self.temp_def, self.temp_ref]
        self.cmd.output_file = self.output_file
        self.cmd.no_fuzzy_matching = True
        self.cmd.finalize_options()
        self.cmd.run()

        expected_content = self._get_expected(fr"""msgid "word1"
msgstr "Word 1"

msgid "word2"
msgstr "Word 2"

msgid "word3"
msgstr ""

msgid "word4"
msgstr ""

""")

        with open(self.output_file, 'r') as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_compenidum(self):
        self.cmd.input_files = [self.temp_def, self.temp_ref]
        self.cmd.output_file = self.output_file
        self.cmd.compendium = self.compendium
        self.cmd.no_fuzzy_matching = True
        self.cmd.no_compendium_comment = True
        self.cmd.finalize_options()
        self.cmd.run()

        expected_content = self._get_expected(fr"""msgid "word1"
msgstr "Word 1"

msgid "word2"
msgstr "Word 2"

msgid "word3"
msgstr ""

msgid "word4"
msgstr "Word 4"

""")

        with open(self.output_file, 'r') as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_compenidum_overwrite(self):
        self.cmd.input_files = [self.temp_def, self.temp_ref]
        self.cmd.output_file = self.output_file
        self.cmd.compendium = self.compendium
        self.cmd.no_fuzzy_matching = True
        self.cmd.no_compendium_comment = True
        self.cmd.compendium_overwrite = True
        self.cmd.finalize_options()
        self.cmd.run()

        expected_content = self._get_expected(fr"""msgid "word1"
msgstr "Comp Word 1"

msgid "word2"
msgstr "Comp Word 2"

msgid "word3"
msgstr ""

msgid "word4"
msgstr "Word 4"

#~ msgid "word1"
#~ msgstr "Word 1"

#~ msgid "word2"
#~ msgstr "Word 2"

""")

        with open(self.output_file, 'r') as f:
            actual_content = f.read()
        assert expected_content == actual_content

    def test_update(self):
        self.cmd.input_files = [self.temp_def, self.temp_ref]
        self.cmd.update = True
        self.cmd.no_fuzzy_matching = True
        self.cmd.finalize_options()
        self.cmd.run()

        expected_content = self._get_expected(fr"""msgid "word1"
msgstr "Word 1"

msgid "word2"
msgstr "Word 2"

msgid "word3"
msgstr ""

msgid "word4"
msgstr ""

""")

        with open(self.temp_def, 'r') as f:
            actual_content = f.read()
        assert expected_content == actual_content

    def test_update_backup(self):
        with open(self.temp_def, 'r') as f:
            before_content = f.read()

        self.cmd.input_files = [self.temp_def, self.temp_ref]
        self.cmd.update = True
        self.cmd.backup = True
        self.cmd.no_fuzzy_matching = True
        self.cmd.finalize_options()
        self.cmd.run()

        assert os.path.exists(self.temp_def + '~') 
        with open(self.temp_def + '~', 'r') as f:
            actual_content = f.read()
        assert before_content == actual_content

        os.unlink(self.temp_def)
        shutil.move(self.temp_def + '~', self.temp_def)
        self.cmd.suffix = '.bac'
        self.cmd.run()

        assert os.path.exists(self.temp_def + '.bac')
        with open(self.temp_def + '.bac', 'r') as f:
            actual_content = f.read()
        assert before_content == actual_content


class CommandLineInterfaceTestCase(unittest.TestCase):

    def setUp(self):
        data_dir = os.path.join(this_dir, 'data')
        self.orig_working_dir = os.getcwd()
        self.orig_argv = sys.argv
        self.orig_stdout = sys.stdout
        self.orig_stderr = sys.stderr
        sys.argv = ['pybabel']
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        os.chdir(data_dir)

        self._remove_log_handlers()
        self.cli = frontend.CommandLineInterface()

    def tearDown(self):
        os.chdir(self.orig_working_dir)
        sys.argv = self.orig_argv
        sys.stdout = self.orig_stdout
        sys.stderr = self.orig_stderr
        for dirname in ['lv_LV', 'ja_JP']:
            locale_dir = os.path.join(i18n_dir, dirname)
            if os.path.isdir(locale_dir):
                shutil.rmtree(locale_dir)
        self._remove_log_handlers()

    def _remove_log_handlers(self):
        # Logging handlers will be reused if possible (#227). This breaks the
        # implicit assumption that our newly created StringIO for sys.stderr
        # contains the console output. Removing the old handler ensures that a
        # new handler with our new StringIO instance will be used.
        log = logging.getLogger('babel')
        for handler in log.handlers:
            log.removeHandler(handler)

    def test_usage(self):
        try:
            self.cli.run(sys.argv)
            self.fail('Expected SystemExit')
        except SystemExit as e:
            assert e.code == 2
            assert sys.stderr.getvalue().lower() == """\
usage: pybabel command [options] [args]

pybabel: error: no valid command or option passed. try the -h/--help option for more information.
"""

    def test_list_locales(self):
        """
        Test the command with the --list-locales arg.
        """
        result = self.cli.run(sys.argv + ['--list-locales'])
        assert not result
        output = sys.stdout.getvalue()
        assert 'fr_CH' in output
        assert 'French (Switzerland)' in output
        assert "\nb'" not in output  # No bytes repr markers in output

    def _run_init_catalog(self):
        i18n_dir = os.path.join(data_dir, 'project', 'i18n')
        pot_path = os.path.join(data_dir, 'project', 'i18n', 'messages.pot')
        init_argv = sys.argv + ['init', '--locale', 'en_US', '-d', i18n_dir,
                                '-i', pot_path]
        self.cli.run(init_argv)

    def test_no_duplicated_output_for_multiple_runs(self):
        self._run_init_catalog()
        first_output = sys.stderr.getvalue()
        self._run_init_catalog()
        second_output = sys.stderr.getvalue()[len(first_output):]

        # in case the log message is not duplicated we should get the same
        # output as before
        assert first_output == second_output

    def test_frontend_can_log_to_predefined_handler(self):
        custom_stream = StringIO()
        log = logging.getLogger('babel')
        log.addHandler(logging.StreamHandler(custom_stream))

        self._run_init_catalog()
        assert id(sys.stderr) != id(custom_stream)
        assert not sys.stderr.getvalue()
        assert custom_stream.getvalue()

    def test_help(self):
        try:
            self.cli.run(sys.argv + ['--help'])
            self.fail('Expected SystemExit')
        except SystemExit as e:
            assert not e.code
            content = sys.stdout.getvalue().lower()
            assert 'options:' in content
            assert all(command in content for command in ('init', 'update', 'compile', 'extract'))

    def assert_pot_file_exists(self):
        assert os.path.isfile(pot_file)

    @freeze_time("1994-11-11")
    def test_extract_with_default_mapping(self):
        self.cli.run(sys.argv + ['extract',
                                 '--copyright-holder', 'FooBar, Inc.',
                                 '--project', 'TestProject', '--version', '0.1',
                                 '--msgid-bugs-address', 'bugs.address@email.tld',
                                 '-c', 'TRANSLATOR', '-c', 'TRANSLATORS:',
                                 '-o', pot_file, 'project'])
        self.assert_pot_file_exists()
        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# Translations template for TestProject.
# Copyright (C) {time.strftime('%Y')} FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, {time.strftime('%Y')}.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: {date}\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. TRANSLATOR: This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

#: project/ignored/this_wont_normally_be_here.py:11
msgid "FooBar"
msgid_plural "FooBars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(pot_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_extract_with_mapping_file(self):
        self.cli.run(sys.argv + ['extract',
                                 '--copyright-holder', 'FooBar, Inc.',
                                 '--project', 'TestProject', '--version', '0.1',
                                 '--msgid-bugs-address', 'bugs.address@email.tld',
                                 '--mapping', os.path.join(data_dir, 'mapping.cfg'),
                                 '-c', 'TRANSLATOR', '-c', 'TRANSLATORS:',
                                 '-o', pot_file, 'project'])
        self.assert_pot_file_exists()
        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# Translations template for TestProject.
# Copyright (C) {time.strftime('%Y')} FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, {time.strftime('%Y')}.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: {date}\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. TRANSLATOR: This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(pot_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_extract_with_exact_file(self):
        """Tests that we can call extract with a particular file and only
        strings from that file get extracted. (Note the absence of strings from file1.py)
        """
        file_to_extract = os.path.join(data_dir, 'project', 'file2.py')
        self.cli.run(sys.argv + ['extract',
                                 '--copyright-holder', 'FooBar, Inc.',
                                 '--project', 'TestProject', '--version', '0.1',
                                 '--msgid-bugs-address', 'bugs.address@email.tld',
                                 '--mapping', os.path.join(data_dir, 'mapping.cfg'),
                                 '-c', 'TRANSLATOR', '-c', 'TRANSLATORS:',
                                 '-o', pot_file, file_to_extract])
        self.assert_pot_file_exists()
        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# Translations template for TestProject.
# Copyright (C) {time.strftime('%Y')} FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, {time.strftime('%Y')}.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: {date}\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language-Team: LANGUAGE <LL@li.org>\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(pot_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_init_with_output_dir(self):
        po_file = _po_file('en_US')
        self.cli.run(sys.argv + ['init',
                                 '--locale', 'en_US',
                                 '-d', os.path.join(i18n_dir),
                                 '-i', os.path.join(i18n_dir, 'messages.pot')])
        assert os.path.isfile(po_file)
        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# English (United States) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: {date}\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language: en_US\n"
"Language-Team: en_US <LL@li.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""

"""
        with open(po_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_init_singular_plural_forms(self):
        po_file = _po_file('ja_JP')
        self.cli.run(sys.argv + ['init',
                                 '--locale', 'ja_JP',
                                 '-d', os.path.join(i18n_dir),
                                 '-i', os.path.join(i18n_dir, 'messages.pot')])
        assert os.path.isfile(po_file)
        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# Japanese (Japan) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: {date}\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language: ja_JP\n"
"Language-Team: ja_JP <LL@li.org>\n"
"Plural-Forms: nplurals=1; plural=0;\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""

"""
        with open(po_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    @freeze_time("1994-11-11")
    def test_init_more_than_2_plural_forms(self):
        po_file = _po_file('lv_LV')
        self.cli.run(sys.argv + ['init',
                                 '--locale', 'lv_LV',
                                 '-d', i18n_dir,
                                 '-i', os.path.join(i18n_dir, 'messages.pot')])
        assert os.path.isfile(po_file)
        date = format_datetime(datetime(1994, 11, 11, 00, 00), 'yyyy-MM-dd HH:mmZ', tzinfo=LOCALTZ, locale='en')
        expected_content = fr"""# Latvian (Latvia) translations for TestProject.
# Copyright (C) 2007 FooBar, Inc.
# This file is distributed under the same license as the TestProject
# project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
msgid ""
msgstr ""
"Project-Id-Version: TestProject 0.1\n"
"Report-Msgid-Bugs-To: bugs.address@email.tld\n"
"POT-Creation-Date: 2007-04-01 15:30+0200\n"
"PO-Revision-Date: {date}\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\n"
"Language: lv_LV\n"
"Language-Team: lv_LV <LL@li.org>\n"
"Plural-Forms: nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 :"
" 2);\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=utf-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel {VERSION}\n"

#. This will be a translator coment,
#. that will include several lines
#: project/file1.py:8
msgid "bar"
msgstr ""

#: project/file2.py:9
msgid "foobar"
msgid_plural "foobars"
msgstr[0] ""
msgstr[1] ""
msgstr[2] ""

"""
        with open(po_file) as f:
            actual_content = f.read()
        assert expected_content == actual_content

    def test_compile_catalog(self):
        po_file = _po_file('de_DE')
        mo_file = po_file.replace('.po', '.mo')
        self.cli.run(sys.argv + ['compile',
                                 '--locale', 'de_DE',
                                 '-d', i18n_dir])
        assert not os.path.isfile(mo_file), f'Expected no file at {mo_file!r}'
        assert sys.stderr.getvalue() == f'catalog {po_file} is marked as fuzzy, skipping\n'

    def test_compile_fuzzy_catalog(self):
        po_file = _po_file('de_DE')
        mo_file = po_file.replace('.po', '.mo')
        try:
            self.cli.run(sys.argv + ['compile',
                                     '--locale', 'de_DE', '--use-fuzzy',
                                     '-d', i18n_dir])
            assert os.path.isfile(mo_file)
            assert sys.stderr.getvalue() == f'compiling catalog {po_file} to {mo_file}\n'
        finally:
            if os.path.isfile(mo_file):
                os.unlink(mo_file)

    def test_compile_catalog_with_more_than_2_plural_forms(self):
        po_file = _po_file('ru_RU')
        mo_file = po_file.replace('.po', '.mo')
        try:
            self.cli.run(sys.argv + ['compile',
                                     '--locale', 'ru_RU', '--use-fuzzy',
                                     '-d', i18n_dir])
            assert os.path.isfile(mo_file)
            assert sys.stderr.getvalue() == f'compiling catalog {po_file} to {mo_file}\n'
        finally:
            if os.path.isfile(mo_file):
                os.unlink(mo_file)

    def test_compile_catalog_multidomain(self):
        po_foo = os.path.join(i18n_dir, 'de_DE', 'LC_MESSAGES', 'foo.po')
        po_bar = os.path.join(i18n_dir, 'de_DE', 'LC_MESSAGES', 'bar.po')
        mo_foo = po_foo.replace('.po', '.mo')
        mo_bar = po_bar.replace('.po', '.mo')
        try:
            self.cli.run(sys.argv + ['compile',
                                     '--locale', 'de_DE', '--domain', 'foo bar', '--use-fuzzy',
                                     '-d', i18n_dir])
            for mo_file in [mo_foo, mo_bar]:
                assert os.path.isfile(mo_file)
            assert sys.stderr.getvalue() == (
                f'compiling catalog {po_foo} to {mo_foo}\n'
                f'compiling catalog {po_bar} to {mo_bar}\n'
            )

        finally:
            for mo_file in [mo_foo, mo_bar]:
                if os.path.isfile(mo_file):
                    os.unlink(mo_file)

    def test_update(self):
        template = Catalog()
        template.add("1")
        template.add("2")
        template.add("3")
        tmpl_file = os.path.join(i18n_dir, 'temp-template.pot')
        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)
        po_file = os.path.join(i18n_dir, 'temp1.po')
        self.cli.run(sys.argv + ['init',
                                 '-l', 'fi',
                                 '-o', po_file,
                                 '-i', tmpl_file,
                                 ])
        with open(po_file) as infp:
            catalog = read_po(infp)
            assert len(catalog) == 3

        # Add another entry to the template

        template.add("4")

        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)

        self.cli.run(sys.argv + ['update',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file])

        with open(po_file) as infp:
            catalog = read_po(infp)
            assert len(catalog) == 4  # Catalog was updated

    def test_update_pot_creation_date(self):
        template = Catalog()
        template.add("1")
        template.add("2")
        template.add("3")
        tmpl_file = os.path.join(i18n_dir, 'temp-template.pot')
        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)
        po_file = os.path.join(i18n_dir, 'temp1.po')
        self.cli.run(sys.argv + ['init',
                                 '-l', 'fi',
                                 '-o', po_file,
                                 '-i', tmpl_file,
                                 ])
        with open(po_file) as infp:
            catalog = read_po(infp)
            assert len(catalog) == 3
        original_catalog_creation_date = catalog.creation_date

        # Update the template creation date
        template.creation_date -= timedelta(minutes=3)
        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)

        self.cli.run(sys.argv + ['update',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file])

        with open(po_file) as infp:
            catalog = read_po(infp)
            # We didn't ignore the creation date, so expect a diff
            assert catalog.creation_date != original_catalog_creation_date

        # Reset the "original"
        original_catalog_creation_date = catalog.creation_date

        # Update the template creation date again
        # This time, pass the ignore flag and expect the times are different
        template.creation_date -= timedelta(minutes=5)
        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)

        self.cli.run(sys.argv + ['update',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file,
                                 '--ignore-pot-creation-date'])

        with open(po_file) as infp:
            catalog = read_po(infp)
            # We ignored creation date, so it should not have changed
            assert catalog.creation_date == original_catalog_creation_date

    def test_check(self):
        template = Catalog()
        template.add("1")
        template.add("2")
        template.add("3")
        tmpl_file = os.path.join(i18n_dir, 'temp-template.pot')
        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)
        po_file = os.path.join(i18n_dir, 'temp1.po')
        self.cli.run(sys.argv + ['init',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file,
                                 ])

        # Update the catalog file
        self.cli.run(sys.argv + ['update',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file])

        # Run a check without introducing any changes to the template
        self.cli.run(sys.argv + ['update',
                                 '--check',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file])

        # Add a new entry and expect the check to fail
        template.add("4")
        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)

        with pytest.raises(BaseError):
            self.cli.run(sys.argv + ['update',
                                     '--check',
                                     '-l', 'fi_FI',
                                     '-o', po_file,
                                     '-i', tmpl_file])

        # Write the latest changes to the po-file
        self.cli.run(sys.argv + ['update',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file])

        # Update an entry and expect the check to fail
        template.add("4", locations=[("foo.py", 1)])
        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)

        with pytest.raises(BaseError):
            self.cli.run(sys.argv + ['update',
                                     '--check',
                                     '-l', 'fi_FI',
                                     '-o', po_file,
                                     '-i', tmpl_file])

    def test_check_pot_creation_date(self):
        template = Catalog()
        template.add("1")
        template.add("2")
        template.add("3")
        tmpl_file = os.path.join(i18n_dir, 'temp-template.pot')
        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)
        po_file = os.path.join(i18n_dir, 'temp1.po')
        self.cli.run(sys.argv + ['init',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file,
                                 ])

        # Update the catalog file
        self.cli.run(sys.argv + ['update',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file])

        # Run a check without introducing any changes to the template
        self.cli.run(sys.argv + ['update',
                                 '--check',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file])

        # Run a check after changing the template creation date
        template.creation_date = datetime.now() - timedelta(minutes=5)
        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)

        # Should fail without --ignore-pot-creation-date flag
        with pytest.raises(BaseError):
            self.cli.run(sys.argv + ['update',
                                     '--check',
                                     '-l', 'fi_FI',
                                     '-o', po_file,
                                     '-i', tmpl_file])
        # Should pass with --ignore-pot-creation-date flag
        self.cli.run(sys.argv + ['update',
                                 '--check',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file,
                                 '--ignore-pot-creation-date'])

    def test_update_init_missing(self):
        template = Catalog()
        template.add("1")
        template.add("2")
        template.add("3")
        tmpl_file = os.path.join(i18n_dir, 'temp2-template.pot')
        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)
        po_file = os.path.join(i18n_dir, 'temp2.po')

        self.cli.run(sys.argv + ['update',
                                 '--init-missing',
                                 '-l', 'fi',
                                 '-o', po_file,
                                 '-i', tmpl_file])

        with open(po_file) as infp:
            catalog = read_po(infp)
            assert len(catalog) == 3

        # Add another entry to the template

        template.add("4")

        with open(tmpl_file, "wb") as outfp:
            write_po(outfp, template)

        self.cli.run(sys.argv + ['update',
                                 '--init-missing',
                                 '-l', 'fi_FI',
                                 '-o', po_file,
                                 '-i', tmpl_file])

        with open(po_file) as infp:
            catalog = read_po(infp)
            assert len(catalog) == 4  # Catalog was updated


mapping_cfg = """
[extractors]
custom = tests.messages.utils:custom_extractor

# Special extractor for a given Python file
[custom: special.py]
treat = delicious

# Python source files
[python: **.py]

# Genshi templates
[genshi: **/templates/**.html]
include_attrs =

[genshi: **/templates/**.txt]
template_class = genshi.template:TextTemplate
encoding = latin-1

# Some custom extractor
[custom: **/custom/*.*]
"""

mapping_toml = """
[extractors]
custom = "tests.messages.utils:custom_extractor"

# Special extractor for a given Python file
[[mappings]]
method = "custom"
pattern = "special.py"
treat = "delightful"

# Python source files
[[mappings]]
method = "python"
pattern = "**.py"

# Genshi templates
[[mappings]]
method = "genshi"
pattern = "**/templates/**.html"
include_attrs = ""

[[mappings]]
method = "genshi"
pattern = "**/templates/**.txt"
template_class = "genshi.template:TextTemplate"
encoding = "latin-1"

# Some custom extractor
[[mappings]]
method = "custom"
pattern = "**/custom/*.*"
"""


@pytest.mark.parametrize(
    ("data", "parser", "preprocess", "is_toml"),
    [
        (
            mapping_cfg,
            frontend.parse_mapping_cfg,
            None,
            False,
        ),
        (
            mapping_toml,
            frontend._parse_mapping_toml,
            None,
            True,
        ),
        (
            mapping_toml,
            partial(frontend._parse_mapping_toml, style="pyproject.toml"),
            lambda s: re.sub(r"^(\[+)", r"\1tool.babel.", s, flags=re.MULTILINE),
            True,
        ),
    ],
    ids=("cfg", "toml", "pyproject-toml"),
)
def test_parse_mapping(data: str, parser, preprocess, is_toml):
    if preprocess:
        data = preprocess(data)
    if is_toml:
        buf = BytesIO(data.encode())
    else:
        buf = StringIO(data)

    method_map, options_map = parser(buf)
    assert len(method_map) == 5

    assert method_map[1] == ('**.py', 'python')
    assert options_map['**.py'] == {}
    assert method_map[2] == ('**/templates/**.html', 'genshi')
    assert options_map['**/templates/**.html']['include_attrs'] == ''
    assert method_map[3] == ('**/templates/**.txt', 'genshi')
    assert (options_map['**/templates/**.txt']['template_class']
            == 'genshi.template:TextTemplate')
    assert options_map['**/templates/**.txt']['encoding'] == 'latin-1'
    assert method_map[4] == ('**/custom/*.*', 'tests.messages.utils:custom_extractor')
    assert options_map['**/custom/*.*'] == {}


def test_parse_keywords():
    kw = frontend.parse_keywords(['_', 'dgettext:2',
                                  'dngettext:2,3', 'pgettext:1c,2'])
    assert kw == {
        '_': None,
        'dgettext': (2,),
        'dngettext': (2, 3),
        'pgettext': ((1, 'c'), 2),
    }


def test_parse_keywords_with_t():
    kw = frontend.parse_keywords(['_:1', '_:2,2t', '_:2c,3,3t'])

    assert kw == {
        '_': {
            None: (1,),
            2: (2,),
            3: ((2, 'c'), 3),
        },
    }


def test_extract_messages_with_t():
    content = rb"""
_("1 arg, arg 1")
_("2 args, arg 1", "2 args, arg 2")
_("3 args, arg 1", "3 args, arg 2", "3 args, arg 3")
_("4 args, arg 1", "4 args, arg 2", "4 args, arg 3", "4 args, arg 4")
"""
    kw = frontend.parse_keywords(['_:1', '_:2,2t', '_:2c,3,3t'])
    result = list(extract.extract("python", BytesIO(content), kw))
    expected = [(2, '1 arg, arg 1', [], None),
                (3, '2 args, arg 1', [], None),
                (3, '2 args, arg 2', [], None),
                (4, '3 args, arg 1', [], None),
                (4, '3 args, arg 3', [], '3 args, arg 2'),
                (5, '4 args, arg 1', [], None)]
    assert result == expected


def configure_cli_command(cmdline):
    """
    Helper to configure a command class, but not run it just yet.

    :param cmdline: The command line (sans the executable name)
    :return: Command instance
    """
    args = shlex.split(cmdline)
    cli = CommandLineInterface()
    cmdinst = cli._configure_command(cmdname=args[0], argv=args[1:])
    return cmdinst


@pytest.mark.parametrize("split", (False, True))
@pytest.mark.parametrize("arg_name", ("-k", "--keyword", "--keywords"))
def test_extract_keyword_args_384(split, arg_name):
    # This is a regression test for https://github.com/python-babel/babel/issues/384
    # and it also tests that the rest of the forgotten aliases/shorthands implied by
    # https://github.com/python-babel/babel/issues/390 are re-remembered (or rather
    # that the mechanism for remembering them again works).

    kwarg_specs = [
        "gettext_noop",
        "gettext_lazy",
        "ngettext_lazy:1,2",
        "ugettext_noop",
        "ugettext_lazy",
        "ungettext_lazy:1,2",
        "pgettext_lazy:1c,2",
        "npgettext_lazy:1c,2,3",
    ]

    if split:  # Generate a command line with multiple -ks
        kwarg_text = " ".join(f"{arg_name} {kwarg_spec}" for kwarg_spec in kwarg_specs)
    else:  # Generate a single space-separated -k
        specs = ' '.join(kwarg_specs)
        kwarg_text = f'{arg_name} "{specs}"'

    # (Both of those invocation styles should be equivalent, so there is no parametrization from here on out)

    cmdinst = configure_cli_command(
        f"extract -F babel-django.cfg --add-comments Translators: -o django232.pot {kwarg_text} .",
    )
    assert isinstance(cmdinst, ExtractMessages)
    assert set(cmdinst.keywords.keys()) == {'_', 'dgettext', 'dngettext',
                                            'gettext', 'gettext_lazy',
                                            'gettext_noop', 'N_', 'ngettext',
                                            'ngettext_lazy', 'npgettext',
                                            'npgettext_lazy', 'pgettext',
                                            'pgettext_lazy', 'ugettext',
                                            'ugettext_lazy', 'ugettext_noop',
                                            'ungettext', 'ungettext_lazy'}


def test_update_catalog_boolean_args():
    cmdinst = configure_cli_command(
        "update --init-missing --no-wrap -N --ignore-obsolete --previous -i foo -o foo -l en")
    assert isinstance(cmdinst, UpdateCatalog)
    assert cmdinst.init_missing is True
    assert cmdinst.no_wrap is True
    assert cmdinst.no_fuzzy_matching is True
    assert cmdinst.ignore_obsolete is True
    assert cmdinst.previous is False  # Mutually exclusive with no_fuzzy_matching


def test_extract_cli_knows_dash_s():
    # This is a regression test for https://github.com/python-babel/babel/issues/390
    cmdinst = configure_cli_command("extract -s -o foo babel")
    assert isinstance(cmdinst, ExtractMessages)
    assert cmdinst.strip_comments


def test_extract_cli_knows_dash_dash_last_dash_translator():
    cmdinst = configure_cli_command('extract --last-translator "FULL NAME EMAIL@ADDRESS" -o foo babel')
    assert isinstance(cmdinst, ExtractMessages)
    assert cmdinst.last_translator == "FULL NAME EMAIL@ADDRESS"


def test_extract_add_location():
    cmdinst = configure_cli_command("extract -o foo babel --add-location full")
    assert isinstance(cmdinst, ExtractMessages)
    assert cmdinst.add_location == 'full'
    assert not cmdinst.no_location
    assert cmdinst.include_lineno

    cmdinst = configure_cli_command("extract -o foo babel --add-location file")
    assert isinstance(cmdinst, ExtractMessages)
    assert cmdinst.add_location == 'file'
    assert not cmdinst.no_location
    assert not cmdinst.include_lineno

    cmdinst = configure_cli_command("extract -o foo babel --add-location never")
    assert isinstance(cmdinst, ExtractMessages)
    assert cmdinst.add_location == 'never'
    assert cmdinst.no_location


def test_extract_error_code(monkeypatch, capsys):
    monkeypatch.chdir(project_dir)
    cmdinst = configure_cli_command("compile --domain=messages --directory i18n --locale fi_BUGGY")
    assert cmdinst.run() == 1
    out, err = capsys.readouterr()
    if err:
        # replace hack below for py2/py3 compatibility
        assert "unknown named placeholder 'merkki'" in err.replace("u'", "'")


@pytest.mark.parametrize("with_underscore_ignore", (False, True))
def test_extract_ignore_dirs(monkeypatch, capsys, tmp_path, with_underscore_ignore):
    pot_file = tmp_path / 'temp.pot'
    monkeypatch.chdir(project_dir)
    cmd = f"extract . -o '{pot_file}' --ignore-dirs '*ignored* .*' "
    if with_underscore_ignore:
        # This also tests that multiple arguments are supported.
        cmd += "--ignore-dirs '_*'"
    cmdinst = configure_cli_command(cmd)
    assert isinstance(cmdinst, ExtractMessages)
    assert cmdinst.directory_filter
    cmdinst.run()
    pot_content = pot_file.read_text()

    # The `ignored` directory is now actually ignored:
    assert 'this_wont_normally_be_here' not in pot_content

    # Since we manually set a filter, the otherwise `_hidden` directory is walked into,
    # unless we opt in to ignore it again
    assert ('ssshhh....' in pot_content) != with_underscore_ignore
    assert ('_hidden_by_default' in pot_content) != with_underscore_ignore


def test_extract_header_comment(monkeypatch, tmp_path):
    pot_file = tmp_path / 'temp.pot'
    monkeypatch.chdir(project_dir)
    cmdinst = configure_cli_command(f"extract . -o '{pot_file}' --header-comment 'Boing' ")
    cmdinst.run()
    pot_content = pot_file.read_text()
    assert 'Boing' in pot_content


@pytest.mark.parametrize("mapping_format", ("toml", "cfg"))
def test_pr_1121(tmp_path, monkeypatch, caplog, mapping_format):
    """
    Test that extraction uses the first matching method and options,
    instead of the first matching method and last matching options.

    Without the fix in PR #1121, this test would fail,
    since the `custom_extractor` isn't passed a delicious treat via
    the configuration.
    """
    if mapping_format == "cfg":
        mapping_file = (tmp_path / "mapping.cfg")
        mapping_file.write_text(mapping_cfg)
    else:
        mapping_file = (tmp_path / "mapping.toml")
        mapping_file.write_text(mapping_toml)
    (tmp_path / "special.py").write_text("# this file is special")
    pot_path = (tmp_path / "output.pot")
    monkeypatch.chdir(tmp_path)
    cmdinst = configure_cli_command(f"extract . -o {shlex.quote(str(pot_path))} --mapping {shlex.quote(mapping_file.name)}")
    assert isinstance(cmdinst, ExtractMessages)
    cmdinst.run()
    # If the custom extractor didn't run, we wouldn't see the cookie in there.
    assert CUSTOM_EXTRACTOR_COOKIE in pot_path.read_text()
