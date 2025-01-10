#
# Copyright (C) 2007-2011 Edgewall Software, 2013-2024 the Babel team
# All rights reserved.
#
# This software is licensed as described in the file LICENSE, which
# you should have received as part of this distribution. The terms
# are also available at http://babel.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://babel.edgewall.org/log/.

import unittest
from datetime import datetime
from io import BytesIO, StringIO

import pytest

from babel.core import Locale
from babel.messages import pofile
from babel.messages.catalog import Catalog, Message
from babel.messages.pofile import _enclose_filename_if_necessary, _extract_locations
from babel.util import FixedOffsetTimezone


class ReadPoTestCase(unittest.TestCase):

    def test_preserve_locale(self):
        buf = StringIO(r'''msgid "foo"
msgstr "Voh"''')
        catalog = pofile.read_po(buf, locale='en_US')
        assert Locale('en', 'US') == catalog.locale

    def test_locale_gets_overridden_by_file(self):
        buf = StringIO(r'''
msgid ""
msgstr ""
"Language: en_US\n"''')
        catalog = pofile.read_po(buf, locale='de')
        assert Locale('en', 'US') == catalog.locale
        buf = StringIO(r'''
msgid ""
msgstr ""
"Language: ko-KR\n"''')
        catalog = pofile.read_po(buf, locale='de')
        assert Locale('ko', 'KR') == catalog.locale

    def test_preserve_domain(self):
        buf = StringIO(r'''msgid "foo"
msgstr "Voh"''')
        catalog = pofile.read_po(buf, domain='mydomain')
        assert catalog.domain == 'mydomain'

    def test_applies_specified_encoding_during_read(self):
        buf = BytesIO('''
msgid ""
msgstr ""
"Project-Id-Version:  3.15\\n"
"Report-Msgid-Bugs-To: Fliegender Zirkus <fliegender@zirkus.de>\\n"
"POT-Creation-Date: 2007-09-27 11:19+0700\\n"
"PO-Revision-Date: 2007-09-27 21:42-0700\\n"
"Last-Translator: John <cleese@bavaria.de>\\n"
"Language-Team: German Lang <de@babel.org>\\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=iso-8859-1\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Generated-By: Babel 1.0dev-r313\\n"

msgid "foo"
msgstr "bär"'''.encode('iso-8859-1'))
        catalog = pofile.read_po(buf, locale='de_DE')
        assert catalog.get('foo').string == 'bär'

    def test_encoding_header_read(self):
        buf = BytesIO(b'msgid ""\nmsgstr ""\n"Content-Type: text/plain; charset=mac_roman\\n"\n')
        catalog = pofile.read_po(buf, locale='xx_XX')
        assert catalog.charset == 'mac_roman'

    def test_plural_forms_header_parsed(self):
        buf = BytesIO(b'msgid ""\nmsgstr ""\n"Plural-Forms: nplurals=42; plural=(n % 11);\\n"\n')
        catalog = pofile.read_po(buf, locale='xx_XX')
        assert catalog.plural_expr == '(n % 11)'
        assert catalog.num_plurals == 42

    def test_read_multiline(self):
        buf = StringIO(r'''msgid ""
"Here's some text that\n"
"includesareallylongwordthatmightbutshouldnt"
" throw us into an infinite "
"loop\n"
msgstr ""''')
        catalog = pofile.read_po(buf)
        assert len(catalog) == 1
        message = list(catalog)[1]
        assert message.id == (
            "Here's some text that\nincludesareallylongwordthat"
            "mightbutshouldnt throw us into an infinite loop\n"
        )

    def test_fuzzy_header(self):
        buf = StringIO(r'''
# Translations template for AReallyReallyLongNameForAProject.
# Copyright (C) 2007 ORGANIZATION
# This file is distributed under the same license as the
# AReallyReallyLongNameForAProject project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
#, fuzzy
''')
        catalog = pofile.read_po(buf)
        assert len(list(catalog)) == 1
        assert list(catalog)[0].fuzzy

    def test_not_fuzzy_header(self):
        buf = StringIO(r'''
# Translations template for AReallyReallyLongNameForAProject.
# Copyright (C) 2007 ORGANIZATION
# This file is distributed under the same license as the
# AReallyReallyLongNameForAProject project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
''')
        catalog = pofile.read_po(buf)
        assert len(list(catalog)) == 1
        assert not list(catalog)[0].fuzzy

    def test_header_entry(self):
        buf = StringIO(r'''
# SOME DESCRIPTIVE TITLE.
# Copyright (C) 2007 THE PACKAGE'S COPYRIGHT HOLDER
# This file is distributed under the same license as the PACKAGE package.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version:  3.15\n"
"Report-Msgid-Bugs-To: Fliegender Zirkus <fliegender@zirkus.de>\n"
"POT-Creation-Date: 2007-09-27 11:19+0700\n"
"PO-Revision-Date: 2007-09-27 21:42-0700\n"
"Last-Translator: John <cleese@bavaria.de>\n"
"Language: de\n"
"Language-Team: German Lang <de@babel.org>\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=iso-8859-2\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel 1.0dev-r313\n"
''')
        catalog = pofile.read_po(buf)
        assert len(list(catalog)) == 1
        assert catalog.version == '3.15'
        assert catalog.msgid_bugs_address == 'Fliegender Zirkus <fliegender@zirkus.de>'
        assert datetime(2007, 9, 27, 11, 19, tzinfo=FixedOffsetTimezone(7 * 60)) == catalog.creation_date
        assert catalog.last_translator == 'John <cleese@bavaria.de>'
        assert Locale('de') == catalog.locale
        assert catalog.language_team == 'German Lang <de@babel.org>'
        assert catalog.charset == 'iso-8859-2'
        assert list(catalog)[0].fuzzy

    def test_obsolete_message(self):
        buf = StringIO(r'''# This is an obsolete message
#~ msgid "foo"
#~ msgstr "Voh"

# This message is not obsolete
#: main.py:1
msgid "bar"
msgstr "Bahr"
''')
        catalog = pofile.read_po(buf)
        assert len(catalog) == 1
        assert len(catalog.obsolete) == 1
        message = catalog.obsolete['foo']
        assert message.id == 'foo'
        assert message.string == 'Voh'
        assert message.user_comments == ['This is an obsolete message']

    def test_obsolete_message_ignored(self):
        buf = StringIO(r'''# This is an obsolete message
#~ msgid "foo"
#~ msgstr "Voh"

# This message is not obsolete
#: main.py:1
msgid "bar"
msgstr "Bahr"
''')
        catalog = pofile.read_po(buf, ignore_obsolete=True)
        assert len(catalog) == 1
        assert len(catalog.obsolete) == 0

    def test_multi_line_obsolete_message(self):
        buf = StringIO(r'''# This is an obsolete message
#~ msgid ""
#~ "foo"
#~ "foo"
#~ msgstr ""
#~ "Voh"
#~ "Vooooh"

# This message is not obsolete
#: main.py:1
msgid "bar"
msgstr "Bahr"
''')
        catalog = pofile.read_po(buf)
        assert len(catalog.obsolete) == 1
        message = catalog.obsolete['foofoo']
        assert message.id == 'foofoo'
        assert message.string == 'VohVooooh'
        assert message.user_comments == ['This is an obsolete message']

    def test_unit_following_multi_line_obsolete_message(self):
        buf = StringIO(r'''# This is an obsolete message
#~ msgid ""
#~ "foo"
#~ "fooooooo"
#~ msgstr ""
#~ "Voh"
#~ "Vooooh"

# This message is not obsolete
#: main.py:1
msgid "bar"
msgstr "Bahr"
''')
        catalog = pofile.read_po(buf)
        assert len(catalog) == 1
        message = catalog['bar']
        assert message.id == 'bar'
        assert message.string == 'Bahr'
        assert message.user_comments == ['This message is not obsolete']

    def test_unit_before_obsolete_is_not_obsoleted(self):
        buf = StringIO(r'''
# This message is not obsolete
#: main.py:1
msgid "bar"
msgstr "Bahr"

# This is an obsolete message
#~ msgid ""
#~ "foo"
#~ "fooooooo"
#~ msgstr ""
#~ "Voh"
#~ "Vooooh"
''')
        catalog = pofile.read_po(buf)
        assert len(catalog) == 1
        message = catalog['bar']
        assert message.id == 'bar'
        assert message.string == 'Bahr'
        assert message.user_comments == ['This message is not obsolete']

    def test_with_context(self):
        buf = BytesIO(b'''# Some string in the menu
#: main.py:1
msgctxt "Menu"
msgid "foo"
msgstr "Voh"

# Another string in the menu
#: main.py:2
msgctxt "Menu"
msgid "bar"
msgstr "Bahr"
''')
        catalog = pofile.read_po(buf, ignore_obsolete=True)
        assert len(catalog) == 2
        message = catalog.get('foo', context='Menu')
        assert message.context == 'Menu'
        message = catalog.get('bar', context='Menu')
        assert message.context == 'Menu'

        # And verify it pass through write_po
        out_buf = BytesIO()
        pofile.write_po(out_buf, catalog, omit_header=True)
        assert out_buf.getvalue().strip() == buf.getvalue().strip()

    def test_obsolete_message_with_context(self):
        buf = StringIO('''
# This message is not obsolete
msgid "baz"
msgstr "Bazczch"

# This is an obsolete message
#~ msgctxt "other"
#~ msgid "foo"
#~ msgstr "Voh"

# This message is not obsolete
#: main.py:1
msgid "bar"
msgstr "Bahr"
''')
        catalog = pofile.read_po(buf)
        assert len(catalog) == 2
        assert len(catalog.obsolete) == 1
        message = catalog.obsolete[("foo", "other")]
        assert message.context == 'other'
        assert message.string == 'Voh'

    def test_obsolete_messages_with_context(self):
        buf = StringIO('''
# This is an obsolete message
#~ msgctxt "apple"
#~ msgid "foo"
#~ msgstr "Foo"

# This is an obsolete message with the same id but different context
#~ msgctxt "orange"
#~ msgid "foo"
#~ msgstr "Bar"
''')
        catalog = pofile.read_po(buf)
        assert len(catalog) == 0
        assert len(catalog.obsolete) == 2
        assert 'foo' not in catalog.obsolete

        apple_msg = catalog.obsolete[('foo', 'apple')]
        assert apple_msg.id == 'foo'
        assert apple_msg.string == 'Foo'
        assert apple_msg.user_comments == ['This is an obsolete message']

        orange_msg = catalog.obsolete[('foo', 'orange')]
        assert orange_msg.id == 'foo'
        assert orange_msg.string == 'Bar'
        assert orange_msg.user_comments == ['This is an obsolete message with the same id but different context']

    def test_obsolete_messages_roundtrip(self):
        buf = StringIO('''\
# This message is not obsolete
#: main.py:1
msgid "bar"
msgstr "Bahr"

# This is an obsolete message
#~ msgid "foo"
#~ msgstr "Voh"

# This is an obsolete message
#~ msgctxt "apple"
#~ msgid "foo"
#~ msgstr "Foo"

# This is an obsolete message with the same id but different context
#~ msgctxt "orange"
#~ msgid "foo"
#~ msgstr "Bar"

''')
        generated_po_file = ''.join(pofile.generate_po(pofile.read_po(buf), omit_header=True))
        assert buf.getvalue() == generated_po_file

    def test_multiline_context(self):
        buf = StringIO('''
msgctxt "a really long "
"message context "
"why?"
msgid "mid"
msgstr "mst"
        ''')
        catalog = pofile.read_po(buf)
        assert len(catalog) == 1
        message = catalog.get('mid', context="a really long message context why?")
        assert message is not None
        assert message.context == 'a really long message context why?'

    def test_with_context_two(self):
        buf = BytesIO(b'''msgctxt "Menu"
msgid "foo"
msgstr "Voh"

msgctxt "Mannu"
msgid "bar"
msgstr "Bahr"
''')
        catalog = pofile.read_po(buf, ignore_obsolete=True)
        assert len(catalog) == 2
        message = catalog.get('foo', context='Menu')
        assert message.context == 'Menu'
        message = catalog.get('bar', context='Mannu')
        assert message.context == 'Mannu'

        # And verify it pass through write_po
        out_buf = BytesIO()
        pofile.write_po(out_buf, catalog, omit_header=True)
        assert out_buf.getvalue().strip() == buf.getvalue().strip(), out_buf.getvalue()

    def test_single_plural_form(self):
        buf = StringIO(r'''msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"''')
        catalog = pofile.read_po(buf, locale='ja_JP')
        assert len(catalog) == 1
        assert catalog.num_plurals == 1
        message = catalog['foo']
        assert len(message.string) == 1

    def test_singular_plural_form(self):
        buf = StringIO(r'''msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"
msgstr[1] "Vohs"''')
        catalog = pofile.read_po(buf, locale='nl_NL')
        assert len(catalog) == 1
        assert catalog.num_plurals == 2
        message = catalog['foo']
        assert len(message.string) == 2

    def test_more_than_two_plural_forms(self):
        buf = StringIO(r'''msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"
msgstr[1] "Vohs"
msgstr[2] "Vohss"''')
        catalog = pofile.read_po(buf, locale='lv_LV')
        assert len(catalog) == 1
        assert catalog.num_plurals == 3
        message = catalog['foo']
        assert len(message.string) == 3
        assert message.string[2] == 'Vohss'

    def test_plural_with_square_brackets(self):
        buf = StringIO(r'''msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh [text]"
msgstr[1] "Vohs [text]"''')
        catalog = pofile.read_po(buf, locale='nb_NO')
        assert len(catalog) == 1
        assert catalog.num_plurals == 2
        message = catalog['foo']
        assert len(message.string) == 2

    def test_obsolete_plural_with_square_brackets(self):
        buf = StringIO('''\
#~ msgid "foo"
#~ msgid_plural "foos"
#~ msgstr[0] "Voh [text]"
#~ msgstr[1] "Vohs [text]"
''')
        catalog = pofile.read_po(buf, locale='nb_NO')
        assert len(catalog) == 0
        assert len(catalog.obsolete) == 1
        assert catalog.num_plurals == 2
        message = catalog.obsolete['foo']
        assert len(message.string) == 2
        assert message.string[0] == 'Voh [text]'
        assert message.string[1] == 'Vohs [text]'

    def test_missing_plural(self):
        buf = StringIO('''\
msgid ""
msgstr ""
"Plural-Forms: nplurals=3; plural=(n < 2) ? n : 2;\n"

msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh [text]"
msgstr[1] "Vohs [text]"
''')
        catalog = pofile.read_po(buf, locale='nb_NO')
        assert len(catalog) == 1
        assert catalog.num_plurals == 3
        message = catalog['foo']
        assert len(message.string) == 3
        assert message.string[0] == 'Voh [text]'
        assert message.string[1] == 'Vohs [text]'
        assert message.string[2] == ''

    def test_missing_plural_in_the_middle(self):
        buf = StringIO('''\
msgid ""
msgstr ""
"Plural-Forms: nplurals=3; plural=(n < 2) ? n : 2;\n"

msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh [text]"
msgstr[2] "Vohs [text]"
''')
        catalog = pofile.read_po(buf, locale='nb_NO')
        assert len(catalog) == 1
        assert catalog.num_plurals == 3
        message = catalog['foo']
        assert len(message.string) == 3
        assert message.string[0] == 'Voh [text]'
        assert message.string[1] == ''
        assert message.string[2] == 'Vohs [text]'

    def test_with_location(self):
        buf = StringIO('''\
#: main.py:1 \u2068filename with whitespace.py\u2069:123
msgid "foo"
msgstr "bar"
''')
        catalog = pofile.read_po(buf, locale='de_DE')
        assert len(catalog) == 1
        message = catalog['foo']
        assert message.string == 'bar'
        assert message.locations == [("main.py", 1), ("filename with whitespace.py", 123)]


    def test_abort_invalid_po_file(self):
        # right double quote missing on msgstr, continuation missing both double quotes
        invalid_po = '''
            msgctxt ""
            "{\"checksum\": 2148532640, \"cxt\": \"collector_thankyou\", \"id\": "
            "270005359}"
            msgid ""
            "Thank you very much for your time.\n"
            "If you have any questions regarding this survey, please contact Fulano "
            "at nadie@blah.com"
            msgstr "Merci de prendre le temps de remplir le sondage.
            Pour toute question, veuillez communiquer avec Fulano  à nadie@blah.com
            "
        '''
        # as above, but contains ascii-only characters
        invalid_po_2 = '''
            msgctxt ""
            "{\"checksum\": 2148532640, \"cxt\": \"collector_thankyou\", \"id\": "
            "270005359}"
            msgid ""
            "Thank you very much for your time.\n"
            "If you have any questions regarding this survey, please contact Fulano "
            "at fulano@blah.com."
            msgstr "Merci de prendre le temps de remplir le sondage.
            Pour toute question, veuillez communiquer avec Fulano a fulano@blah.com
            "
            '''
        # left double quote missing in msgid
        invalid_po_3 = '''
            msgid *A"
            msgstr "B"
        '''
        # right double quote missing in msgstr
        invalid_po_4 = '''
            msgid "A"
            msgstr "B*
        '''
        # right double quote missing in msgstr continuation
        invalid_po_5 = '''
            msgid "A"
            msgstr ""
            "*
        '''
        for incorrectly_delimited_po_string in (invalid_po, invalid_po_2, invalid_po_3, invalid_po_4, invalid_po_5):
            buf = StringIO(incorrectly_delimited_po_string)
            with pytest.raises(pofile.PoFileError):
                pofile.read_po(buf, locale='fr', abort_invalid=True)
            buf.seek(0)
            output = pofile.read_po(buf, locale='fr', abort_invalid=False)
            assert isinstance(output, Catalog)

    def test_invalid_msgstr_plural(self):
        # msgstr plural broken
        invalid_1 = '''
        msgid "A"
        msgstr[
        '''
        invalid_2 = '''
        msgid "A"
        msgstr[] "no index"
        '''
        invalid_3 = '''
        msgid "A"
        msgstr[bah] "index is not a number"
        '''
        # no content
        invalid_4 = '''
        msgid "A"
        msgstr[0]
        '''
        # not correctly delimited
        invalid_5 = '''
        msgid "A"
        msgstr[0] not delimited
        '''
        for incorrectly_plural in (invalid_1, invalid_2, invalid_3, invalid_4, invalid_5):
            buf = StringIO(incorrectly_plural)
            with pytest.raises(pofile.PoFileError):
                pofile.read_po(buf, locale='fr', abort_invalid=True)
            buf.seek(0)
            output = pofile.read_po(buf, locale='fr', abort_invalid=False)
            assert isinstance(output, Catalog)


    def test_invalid_pofile_with_abort_flag(self):
        parser = pofile.PoFileParser(None, abort_invalid=True)
        lineno = 10
        line = 'Algo esta mal'
        msg = 'invalid file'
        with pytest.raises(pofile.PoFileError):
            parser._invalid_pofile(line, lineno, msg)


class WritePoTestCase(unittest.TestCase):

    def test_join_locations(self):
        catalog = Catalog()
        catalog.add('foo', locations=[('main.py', 1)])
        catalog.add('foo', locations=[('utils.py', 3)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        assert buf.getvalue().strip() == b'''#: main.py:1 utils.py:3
msgid "foo"
msgstr ""'''

    def test_write_po_file_with_specified_charset(self):
        catalog = Catalog(charset='iso-8859-1')
        catalog.add('foo', 'äöü', locations=[('main.py', 1)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=False)
        po_file = buf.getvalue().strip()
        assert b'"Content-Type: text/plain; charset=iso-8859-1\\n"' in po_file
        assert 'msgstr "äöü"'.encode('iso-8859-1') in po_file

    def test_duplicate_comments(self):
        catalog = Catalog()
        catalog.add('foo', auto_comments=['A comment'])
        catalog.add('foo', auto_comments=['A comment'])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        assert buf.getvalue().strip() == b'''#. A comment
msgid "foo"
msgstr ""'''

    def test_wrap_long_lines(self):
        text = """Here's some text where
white space and line breaks matter, and should

not be removed

"""
        catalog = Catalog()
        catalog.add(text, locations=[('main.py', 1)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, no_location=True, omit_header=True,
                        width=42)
        assert buf.getvalue().strip() == b'''msgid ""
"Here's some text where\\n"
"white space and line breaks matter, and"
" should\\n"
"\\n"
"not be removed\\n"
"\\n"
msgstr ""'''

    def test_wrap_long_lines_with_long_word(self):
        text = """Here's some text that
includesareallylongwordthatmightbutshouldnt throw us into an infinite loop
"""
        catalog = Catalog()
        catalog.add(text, locations=[('main.py', 1)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, no_location=True, omit_header=True,
                        width=32)
        assert buf.getvalue().strip() == b'''msgid ""
"Here's some text that\\n"
"includesareallylongwordthatmightbutshouldnt"
" throw us into an infinite "
"loop\\n"
msgstr ""'''

    def test_wrap_long_lines_in_header(self):
        """
        Verify that long lines in the header comment are wrapped correctly.
        """
        catalog = Catalog(project='AReallyReallyLongNameForAProject',
                          revision_date=datetime(2007, 4, 1))
        buf = BytesIO()
        pofile.write_po(buf, catalog)
        assert b'\n'.join(buf.getvalue().splitlines()[:7]) == b'''\
# Translations template for AReallyReallyLongNameForAProject.
# Copyright (C) 2007 ORGANIZATION
# This file is distributed under the same license as the
# AReallyReallyLongNameForAProject project.
# FIRST AUTHOR <EMAIL@ADDRESS>, 2007.
#
#, fuzzy'''

    def test_wrap_locations_with_hyphens(self):
        catalog = Catalog()
        catalog.add('foo', locations=[
            ('doupy/templates/base/navmenu.inc.html.py', 60),
        ])
        catalog.add('foo', locations=[
            ('doupy/templates/job-offers/helpers.html', 22),
        ])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        assert buf.getvalue().strip() == b'''#: doupy/templates/base/navmenu.inc.html.py:60
#: doupy/templates/job-offers/helpers.html:22
msgid "foo"
msgstr ""'''

    def test_no_wrap_and_width_behaviour_on_comments(self):
        catalog = Catalog()
        catalog.add("Pretty dam long message id, which must really be big "
                    "to test this wrap behaviour, if not it won't work.",
                    locations=[("fake.py", n) for n in range(1, 30)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, width=None, omit_header=True)
        assert buf.getvalue().lower() == b"""\
#: fake.py:1 fake.py:2 fake.py:3 fake.py:4 fake.py:5 fake.py:6 fake.py:7
#: fake.py:8 fake.py:9 fake.py:10 fake.py:11 fake.py:12 fake.py:13 fake.py:14
#: fake.py:15 fake.py:16 fake.py:17 fake.py:18 fake.py:19 fake.py:20 fake.py:21
#: fake.py:22 fake.py:23 fake.py:24 fake.py:25 fake.py:26 fake.py:27 fake.py:28
#: fake.py:29
msgid "pretty dam long message id, which must really be big to test this wrap behaviour, if not it won't work."
msgstr ""

"""
        buf = BytesIO()
        pofile.write_po(buf, catalog, width=100, omit_header=True)
        assert buf.getvalue().lower() == b"""\
#: fake.py:1 fake.py:2 fake.py:3 fake.py:4 fake.py:5 fake.py:6 fake.py:7 fake.py:8 fake.py:9 fake.py:10
#: fake.py:11 fake.py:12 fake.py:13 fake.py:14 fake.py:15 fake.py:16 fake.py:17 fake.py:18 fake.py:19
#: fake.py:20 fake.py:21 fake.py:22 fake.py:23 fake.py:24 fake.py:25 fake.py:26 fake.py:27 fake.py:28
#: fake.py:29
msgid ""
"pretty dam long message id, which must really be big to test this wrap behaviour, if not it won't"
" work."
msgstr ""

"""

    def test_pot_with_translator_comments(self):
        catalog = Catalog()
        catalog.add('foo', locations=[('main.py', 1)],
                    auto_comments=['Comment About `foo`'])
        catalog.add('bar', locations=[('utils.py', 3)],
                    user_comments=['Comment About `bar` with',
                                   'multiple lines.'])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        assert buf.getvalue().strip() == b'''#. Comment About `foo`
#: main.py:1
msgid "foo"
msgstr ""

# Comment About `bar` with
# multiple lines.
#: utils.py:3
msgid "bar"
msgstr ""'''

    def test_po_with_obsolete_message(self):
        catalog = Catalog()
        catalog.add('foo', 'Voh', locations=[('main.py', 1)])
        catalog.obsolete['bar'] = Message('bar', 'Bahr',
                                          locations=[('utils.py', 3)],
                                          user_comments=['User comment'])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        assert buf.getvalue().strip() == b'''#: main.py:1
msgid "foo"
msgstr "Voh"

# User comment
#~ msgid "bar"
#~ msgstr "Bahr"'''

    def test_po_with_multiline_obsolete_message(self):
        catalog = Catalog()
        catalog.add('foo', 'Voh', locations=[('main.py', 1)])
        msgid = r"""Here's a message that covers
multiple lines, and should still be handled
correctly.
"""
        msgstr = r"""Here's a message that covers
multiple lines, and should still be handled
correctly.
"""
        catalog.obsolete[msgid] = Message(msgid, msgstr,
                                          locations=[('utils.py', 3)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True)
        assert buf.getvalue().strip() == b'''#: main.py:1
msgid "foo"
msgstr "Voh"

#~ msgid ""
#~ "Here's a message that covers\\n"
#~ "multiple lines, and should still be handled\\n"
#~ "correctly.\\n"
#~ msgstr ""
#~ "Here's a message that covers\\n"
#~ "multiple lines, and should still be handled\\n"
#~ "correctly.\\n"'''

    def test_po_with_obsolete_message_ignored(self):
        catalog = Catalog()
        catalog.add('foo', 'Voh', locations=[('main.py', 1)])
        catalog.obsolete['bar'] = Message('bar', 'Bahr',
                                          locations=[('utils.py', 3)],
                                          user_comments=['User comment'])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, ignore_obsolete=True)
        assert buf.getvalue().strip() == b'''#: main.py:1
msgid "foo"
msgstr "Voh"'''

    def test_po_with_previous_msgid(self):
        catalog = Catalog()
        catalog.add('foo', 'Voh', locations=[('main.py', 1)],
                    previous_id='fo')
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_previous=True)
        assert buf.getvalue().strip() == b'''#: main.py:1
#| msgid "fo"
msgid "foo"
msgstr "Voh"'''

    def test_po_with_previous_msgid_plural(self):
        catalog = Catalog()
        catalog.add(('foo', 'foos'), ('Voh', 'Voeh'),
                    locations=[('main.py', 1)], previous_id=('fo', 'fos'))
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_previous=True)
        assert buf.getvalue().strip() == b'''#: main.py:1
#| msgid "fo"
#| msgid_plural "fos"
msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"
msgstr[1] "Voeh"'''

    def test_sorted_po(self):
        catalog = Catalog()
        catalog.add('bar', locations=[('utils.py', 3)],
                    user_comments=['Comment About `bar` with',
                                   'multiple lines.'])
        catalog.add(('foo', 'foos'), ('Voh', 'Voeh'),
                    locations=[('main.py', 1)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, sort_output=True)
        value = buf.getvalue().strip()
        assert b'''\
# Comment About `bar` with
# multiple lines.
#: utils.py:3
msgid "bar"
msgstr ""

#: main.py:1
msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"
msgstr[1] "Voeh"''' in value
        assert value.find(b'msgid ""') < value.find(b'msgid "bar"') < value.find(b'msgid "foo"')

    def test_sorted_po_context(self):
        catalog = Catalog()
        catalog.add(('foo', 'foos'), ('Voh', 'Voeh'),
                    locations=[('main.py', 1)],
                    context='there')
        catalog.add(('foo', 'foos'), ('Voh', 'Voeh'),
                    locations=[('main.py', 1)])
        catalog.add(('foo', 'foos'), ('Voh', 'Voeh'),
                    locations=[('main.py', 1)],
                    context='here')
        buf = BytesIO()
        pofile.write_po(buf, catalog, sort_output=True)
        value = buf.getvalue().strip()
        # We expect the foo without ctx, followed by "here" foo and "there" foo
        assert b'''\
#: main.py:1
msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"
msgstr[1] "Voeh"

#: main.py:1
msgctxt "here"
msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"
msgstr[1] "Voeh"

#: main.py:1
msgctxt "there"
msgid "foo"
msgid_plural "foos"
msgstr[0] "Voh"
msgstr[1] "Voeh"''' in value

    def test_file_sorted_po(self):
        catalog = Catalog()
        catalog.add('bar', locations=[('utils.py', 3)])
        catalog.add(('foo', 'foos'), ('Voh', 'Voeh'), locations=[('main.py', 1)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, sort_by_file=True)
        value = buf.getvalue().strip()
        assert value.find(b'main.py') < value.find(b'utils.py')

    def test_file_with_no_lineno(self):
        catalog = Catalog()
        catalog.add('bar', locations=[('utils.py', None)],
                    user_comments=['Comment About `bar` with',
                                   'multiple lines.'])
        buf = BytesIO()
        pofile.write_po(buf, catalog, sort_output=True)
        value = buf.getvalue().strip()
        assert b'''\
# Comment About `bar` with
# multiple lines.
#: utils.py
msgid "bar"
msgstr ""''' in value

    def test_silent_location_fallback(self):
        buf = BytesIO(b'''\
#: broken_file.py
msgid "missing line number"
msgstr ""

#: broken_file.py:broken_line_number
msgid "broken line number"
msgstr ""''')
        catalog = pofile.read_po(buf)
        assert catalog['missing line number'].locations == [('broken_file.py', None)]
        assert catalog['broken line number'].locations == []

    def test_include_lineno(self):
        catalog = Catalog()
        catalog.add('foo', locations=[('main.py', 1)])
        catalog.add('foo', locations=[('utils.py', 3)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_lineno=True)
        assert buf.getvalue().strip() == b'''#: main.py:1 utils.py:3
msgid "foo"
msgstr ""'''

    def test_no_include_lineno(self):
        catalog = Catalog()
        catalog.add('foo', locations=[('main.py', 1)])
        catalog.add('foo', locations=[('main.py', 2)])
        catalog.add('foo', locations=[('utils.py', 3)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_lineno=False)
        assert buf.getvalue().strip() == b'''#: main.py utils.py
msgid "foo"
msgstr ""'''

    def test_white_space_in_location(self):
        catalog = Catalog()
        catalog.add('foo', locations=[('main.py', 1)])
        catalog.add('foo', locations=[('utils b.py', 3)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_lineno=True)
        assert buf.getvalue().strip() == b'''#: main.py:1 \xe2\x81\xa8utils b.py\xe2\x81\xa9:3
msgid "foo"
msgstr ""'''

    def test_white_space_in_location_already_enclosed(self):
        catalog = Catalog()
        catalog.add('foo', locations=[('main.py', 1)])
        catalog.add('foo', locations=[('\u2068utils b.py\u2069', 3)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_lineno=True)
        assert buf.getvalue().strip() == b'''#: main.py:1 \xe2\x81\xa8utils b.py\xe2\x81\xa9:3
msgid "foo"
msgstr ""'''

    def test_tab_in_location(self):
        catalog = Catalog()
        catalog.add('foo', locations=[('main.py', 1)])
        catalog.add('foo', locations=[('utils\tb.py', 3)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_lineno=True)
        assert buf.getvalue().strip() == b'''#: main.py:1 \xe2\x81\xa8utils        b.py\xe2\x81\xa9:3
msgid "foo"
msgstr ""'''

    def test_tab_in_location_already_enclosed(self):
        catalog = Catalog()
        catalog.add('foo', locations=[('main.py', 1)])
        catalog.add('foo', locations=[('\u2068utils\tb.py\u2069', 3)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_lineno=True)
        assert buf.getvalue().strip() == b'''#: main.py:1 \xe2\x81\xa8utils        b.py\xe2\x81\xa9:3
msgid "foo"
msgstr ""'''


    def test_wrap_with_enclosed_file_locations(self):
        # Ensure that file names containing white space are not wrapped regardless of the --width parameter
        catalog = Catalog()
        catalog.add('foo', locations=[('\u2068test utils.py\u2069', 1)])
        catalog.add('foo', locations=[('\u2068test utils.py\u2069', 3)])
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_lineno=True, width=1)
        assert buf.getvalue().strip() == b'''#: \xe2\x81\xa8test utils.py\xe2\x81\xa9:1
#: \xe2\x81\xa8test utils.py\xe2\x81\xa9:3
msgid "foo"
msgstr ""'''


class RoundtripPoTestCase(unittest.TestCase):

    def test_enclosed_filenames_in_location_comment(self):
        catalog = Catalog()
        catalog.add("foo", lineno=2, locations=[("main 1.py", 1)], string="")
        catalog.add("bar", lineno=6, locations=[("other.py", 2)], string="")
        catalog.add("baz", lineno=10, locations=[("main 1.py", 3), ("other.py", 4)], string="")
        buf = BytesIO()
        pofile.write_po(buf, catalog, omit_header=True, include_lineno=True)
        buf.seek(0)
        catalog2 = pofile.read_po(buf)
        assert True is catalog.is_identical(catalog2)

class PofileFunctionsTestCase(unittest.TestCase):

    def test_unescape(self):
        escaped = '"Say:\\n  \\"hello, world!\\"\\n"'
        unescaped = 'Say:\n  "hello, world!"\n'
        assert unescaped != escaped
        assert unescaped == pofile.unescape(escaped)

    def test_unescape_of_quoted_newline(self):
        # regression test for #198
        assert pofile.unescape(r'"\\n"') == '\\n'

    def test_denormalize_on_msgstr_without_empty_first_line(self):
        # handle irregular multi-line msgstr (no "" as first line)
        # gracefully (#171)
        msgstr = '"multi-line\\n"\n" translation"'
        expected_denormalized = 'multi-line\n translation'

        assert expected_denormalized == pofile.denormalize(msgstr)
        assert expected_denormalized == pofile.denormalize(f'""\n{msgstr}')


@pytest.mark.parametrize(("line", "locations"), [
    ("\u2068file1.po\u2069", ["file1.po"]),
    ("file1.po \u2068file 2.po\u2069 file3.po", ["file1.po", "file 2.po", "file3.po"]),
    ("file1.po:1 \u2068file 2.po\u2069:2 file3.po:3", ["file1.po:1", "file 2.po:2", "file3.po:3"]),
    ("\u2068file1.po\u2069:1 \u2068file\t2.po\u2069:2 file3.po:3",
     ["file1.po:1", "file\t2.po:2", "file3.po:3"]),
    ("file1.po  file2.po", ["file1.po", "file2.po"]),
    ("file1.po \u2068\u2069 file2.po", ["file1.po", "file2.po"]),
])
def test_extract_locations_valid_location_comment(line, locations):
    assert locations == _extract_locations(line)


@pytest.mark.parametrize(("line",), [
    ("\u2068file 1.po",),
    ("file 1.po\u2069",),
    ("\u2069file 1.po\u2068",),
    ("\u2068file 1.po:1 \u2068file 2.po\u2069:2",),
    ("\u2068file 1.po\u2069:1 file 2.po\u2069:2",),
])
def test_extract_locations_invalid_location_comment(line):
    with pytest.raises(ValueError):
        _extract_locations(line)


@pytest.mark.parametrize(("filename",), [
    ("file.po",),
    ("file_a.po",),
    ("file-a.po",),
    ("file\n.po",),
    ("\u2068file.po\u2069",),
    ("\u2068file a.po\u2069",),
])
def test_enclose_filename_if_necessary_no_change(filename):
    assert filename == _enclose_filename_if_necessary(filename)


@pytest.mark.parametrize(("filename",), [
    ("file a.po",),
    ("file\ta.po",),
])
def test_enclose_filename_if_necessary_enclosed(filename):
    assert "\u2068" + filename + "\u2069" == _enclose_filename_if_necessary(filename)


def test_unknown_language_roundtrip():
    buf = StringIO(r'''
msgid ""
msgstr ""
"Language: sr_SP\n"''')
    catalog = pofile.read_po(buf)
    assert catalog.locale_identifier == 'sr_SP'
    assert not catalog.locale
    buf = BytesIO()
    pofile.write_po(buf, catalog)
    assert 'sr_SP' in buf.getvalue().decode()


def test_unknown_language_write():
    catalog = Catalog(locale='sr_SP')
    assert catalog.locale_identifier == 'sr_SP'
    assert not catalog.locale
    buf = BytesIO()
    pofile.write_po(buf, catalog)
    assert 'sr_SP' in buf.getvalue().decode()


def test_iterable_of_strings():
    """
    Test we can parse from an iterable of strings.
    """
    catalog = pofile.read_po(['msgid "foo"', b'msgstr "Voh"'], locale="en_US")
    assert catalog.locale == Locale("en", "US")
    assert catalog.get("foo").string == "Voh"


def test_issue_1087():
    buf = StringIO(r'''
msgid ""
msgstr ""
"Language: \n"
''')
    assert pofile.read_po(buf).locale is None


@pytest.mark.parametrize("case", ['msgid "foo"', 'msgid "foo"\nmsgid_plural "foos"'])
@pytest.mark.parametrize("abort_invalid", [False, True])
def test_issue_1134(case: str, abort_invalid: bool):
    buf = StringIO(case)

    if abort_invalid:
        # Catalog not created, aborted with PoFileError
        with pytest.raises(pofile.PoFileError, match="missing msgstr for msgid 'foo' on 0"):
            pofile.read_po(buf, abort_invalid=True)
    else:
        # Catalog is created with warning, no abort
        output = pofile.read_po(buf)
        assert len(output) == 1
        assert output["foo"].string in ((''), ('', ''))
