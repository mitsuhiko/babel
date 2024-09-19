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

import codecs
import sys
import unittest
from io import BytesIO, StringIO

import pytest

from babel.messages import extract


class ExtractPythonTestCase(unittest.TestCase):

    def test_nested_calls(self):
        buf = BytesIO(b"""\
msg1 = _(i18n_arg.replace(r'\"', '"'))
msg2 = ungettext(i18n_arg.replace(r'\"', '"'), multi_arg.replace(r'\"', '"'), 2)
msg3 = ungettext("Babel", multi_arg.replace(r'\"', '"'), 2)
msg4 = ungettext(i18n_arg.replace(r'\"', '"'), "Babels", 2)
msg5 = ungettext('bunny', 'bunnies', random.randint(1, 2))
msg6 = ungettext(arg0, 'bunnies', random.randint(1, 2))
msg7 = _(hello.there)
msg8 = gettext('Rabbit')
msg9 = dgettext('wiki', model.addPage())
msg10 = dngettext(getDomain(), 'Page', 'Pages', 3)
""")
        messages = list(extract.extract_python(buf,
                                               extract.DEFAULT_KEYWORDS.keys(),
                                               [], {}))
        assert messages == [
            (1, '_', None, []),
            (2, 'ungettext', (None, None, None), []),
            (3, 'ungettext', ('Babel', None, None), []),
            (4, 'ungettext', (None, 'Babels', None), []),
            (5, 'ungettext', ('bunny', 'bunnies', None), []),
            (6, 'ungettext', (None, 'bunnies', None), []),
            (7, '_', None, []),
            (8, 'gettext', 'Rabbit', []),
            (9, 'dgettext', ('wiki', None), []),
            (10, 'dngettext', (None, 'Page', 'Pages', None), []),
        ]

    def test_extract_default_encoding_ascii(self):
        buf = BytesIO(b'_("a")')
        messages = list(extract.extract_python(
            buf, list(extract.DEFAULT_KEYWORDS), [], {},
        ))
        # Should work great in both py2 and py3
        assert messages == [(1, '_', 'a', [])]

    def test_extract_default_encoding_utf8(self):
        buf = BytesIO('_("☃")'.encode('UTF-8'))
        messages = list(extract.extract_python(
            buf, list(extract.DEFAULT_KEYWORDS), [], {},
        ))
        assert messages == [(1, '_', '☃', [])]

    def test_nested_comments(self):
        buf = BytesIO(b"""\
msg = ngettext('pylon',  # TRANSLATORS: shouldn't be
               'pylons', # TRANSLATORS: seeing this
               count)
""")
        messages = list(extract.extract_python(buf, ('ngettext',),
                                               ['TRANSLATORS:'], {}))
        assert messages == [(1, 'ngettext', ('pylon', 'pylons', None), [])]

    def test_comments_with_calls_that_spawn_multiple_lines(self):
        buf = BytesIO(b"""\
# NOTE: This Comment SHOULD Be Extracted
add_notice(req, ngettext("Catalog deleted.",
                         "Catalogs deleted.", len(selected)))

# NOTE: This Comment SHOULD Be Extracted
add_notice(req, _("Locale deleted."))


# NOTE: This Comment SHOULD Be Extracted
add_notice(req, ngettext("Foo deleted.", "Foos deleted.", len(selected)))

# NOTE: This Comment SHOULD Be Extracted
# NOTE: And This One Too
add_notice(req, ngettext("Bar deleted.",
                         "Bars deleted.", len(selected)))
""")
        messages = list(extract.extract_python(buf, ('ngettext', '_'), ['NOTE:'],

                                               {'strip_comment_tags': False}))
        assert messages[0] == (2, 'ngettext', ('Catalog deleted.', 'Catalogs deleted.', None), ['NOTE: This Comment SHOULD Be Extracted'])
        assert messages[1] == (6, '_', 'Locale deleted.', ['NOTE: This Comment SHOULD Be Extracted'])
        assert messages[2] == (10, 'ngettext', ('Foo deleted.', 'Foos deleted.', None), ['NOTE: This Comment SHOULD Be Extracted'])
        assert messages[3] == (14, 'ngettext', ('Bar deleted.', 'Bars deleted.', None), ['NOTE: This Comment SHOULD Be Extracted', 'NOTE: And This One Too'])

    def test_declarations(self):
        buf = BytesIO(b"""\
class gettext(object):
    pass
def render_body(context,x,y=_('Page arg 1'),z=_('Page arg 2'),**pageargs):
    pass
def ngettext(y='arg 1',z='arg 2',**pageargs):
    pass
class Meta:
    verbose_name = _('log entry')
""")
        messages = list(extract.extract_python(buf,
                                               extract.DEFAULT_KEYWORDS.keys(),
                                               [], {}))
        assert messages == [
            (3, '_', 'Page arg 1', []),
            (3, '_', 'Page arg 2', []),
            (8, '_', 'log entry', []),
        ]

    def test_multiline(self):
        buf = BytesIO(b"""\
msg1 = ngettext('pylon',
                'pylons', count)
msg2 = ngettext('elvis',
                'elvises',
                 count)
""")
        messages = list(extract.extract_python(buf, ('ngettext',), [], {}))
        assert messages == [
            (1, 'ngettext', ('pylon', 'pylons', None), []),
            (3, 'ngettext', ('elvis', 'elvises', None), []),
        ]

    def test_npgettext(self):
        buf = BytesIO(b"""\
msg1 = npgettext('Strings','pylon',
                'pylons', count)
msg2 = npgettext('Strings','elvis',
                'elvises',
                 count)
""")
        messages = list(extract.extract_python(buf, ('npgettext',), [], {}))
        assert messages == [
            (1, 'npgettext', ('Strings', 'pylon', 'pylons', None), []),
            (3, 'npgettext', ('Strings', 'elvis', 'elvises', None), []),
        ]
        buf = BytesIO(b"""\
msg = npgettext('Strings', 'pylon',  # TRANSLATORS: shouldn't be
                'pylons', # TRANSLATORS: seeing this
                count)
""")
        messages = list(extract.extract_python(buf, ('npgettext',),
                                               ['TRANSLATORS:'], {}))
        assert messages == [
            (1, 'npgettext', ('Strings', 'pylon', 'pylons', None), []),
        ]

    def test_triple_quoted_strings(self):
        buf = BytesIO(b"""\
msg1 = _('''pylons''')
msg2 = ngettext(r'''elvis''', \"\"\"elvises\"\"\", count)
msg2 = ngettext(\"\"\"elvis\"\"\", 'elvises', count)
""")
        messages = list(extract.extract_python(buf,
                                               extract.DEFAULT_KEYWORDS.keys(),
                                               [], {}))
        assert messages == [
            (1, '_', 'pylons', []),
            (2, 'ngettext', ('elvis', 'elvises', None), []),
            (3, 'ngettext', ('elvis', 'elvises', None), []),
        ]

    def test_multiline_strings(self):
        buf = BytesIO(b"""\
_('''This module provides internationalization and localization
support for your Python programs by providing an interface to the GNU
gettext message catalog library.''')
""")
        messages = list(extract.extract_python(buf,
                                               extract.DEFAULT_KEYWORDS.keys(),
                                               [], {}))
        assert messages == [
            (1, '_',
            'This module provides internationalization and localization\n'
            'support for your Python programs by providing an interface to '
            'the GNU\ngettext message catalog library.', []),
        ]

    def test_concatenated_strings(self):
        buf = BytesIO(b"""\
foobar = _('foo' 'bar')
""")
        messages = list(extract.extract_python(buf,
                                               extract.DEFAULT_KEYWORDS.keys(),
                                               [], {}))
        assert messages[0][2] == 'foobar'

    def test_unicode_string_arg(self):
        buf = BytesIO(b"msg = _(u'Foo Bar')")
        messages = list(extract.extract_python(buf, ('_',), [], {}))
        assert messages[0][2] == 'Foo Bar'

    def test_comment_tag(self):
        buf = BytesIO(b"""
# NOTE: A translation comment
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Foo Bar'
        assert messages[0][3] == ['NOTE: A translation comment']

    def test_comment_tag_multiline(self):
        buf = BytesIO(b"""
# NOTE: A translation comment
# with a second line
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Foo Bar'
        assert messages[0][3] == ['NOTE: A translation comment', 'with a second line']

    def test_translator_comments_with_previous_non_translator_comments(self):
        buf = BytesIO(b"""
# This shouldn't be in the output
# because it didn't start with a comment tag
# NOTE: A translation comment
# with a second line
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Foo Bar'
        assert messages[0][3] == ['NOTE: A translation comment', 'with a second line']

    def test_comment_tags_not_on_start_of_comment(self):
        buf = BytesIO(b"""
# This shouldn't be in the output
# because it didn't start with a comment tag
# do NOTE: this will not be a translation comment
# NOTE: This one will be
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Foo Bar'
        assert messages[0][3] == ['NOTE: This one will be']

    def test_multiple_comment_tags(self):
        buf = BytesIO(b"""
# NOTE1: A translation comment for tag1
# with a second line
msg = _(u'Foo Bar1')

# NOTE2: A translation comment for tag2
msg = _(u'Foo Bar2')
""")
        messages = list(extract.extract_python(buf, ('_',),
                                               ['NOTE1:', 'NOTE2:'], {}))
        assert messages[0][2] == 'Foo Bar1'
        assert messages[0][3] == ['NOTE1: A translation comment for tag1', 'with a second line']
        assert messages[1][2] == 'Foo Bar2'
        assert messages[1][3] == ['NOTE2: A translation comment for tag2']

    def test_two_succeeding_comments(self):
        buf = BytesIO(b"""
# NOTE: one
# NOTE: two
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Foo Bar'
        assert messages[0][3] == ['NOTE: one', 'NOTE: two']

    def test_invalid_translator_comments(self):
        buf = BytesIO(b"""
# NOTE: this shouldn't apply to any messages
hello = 'there'

msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Foo Bar'
        assert messages[0][3] == []

    def test_invalid_translator_comments2(self):
        buf = BytesIO(b"""
# NOTE: Hi!
hithere = _('Hi there!')

# NOTE: you should not be seeing this in the .po
rows = [[v for v in range(0,10)] for row in range(0,10)]

# this (NOTE:) should not show up either
hello = _('Hello')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Hi there!'
        assert messages[0][3] == ['NOTE: Hi!']
        assert messages[1][2] == 'Hello'
        assert messages[1][3] == []

    def test_invalid_translator_comments3(self):
        buf = BytesIO(b"""
# NOTE: Hi,

# there!
hithere = _('Hi there!')
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Hi there!'
        assert messages[0][3] == []

    def test_comment_tag_with_leading_space(self):
        buf = BytesIO(b"""
  #: A translation comment
  #: with leading spaces
msg = _(u'Foo Bar')
""")
        messages = list(extract.extract_python(buf, ('_',), [':'], {}))
        assert messages[0][2] == 'Foo Bar'
        assert messages[0][3] == [': A translation comment', ': with leading spaces']

    def test_different_signatures(self):
        buf = BytesIO(b"""
foo = _('foo', 'bar')
n = ngettext('hello', 'there', n=3)
n = ngettext(n=3, 'hello', 'there')
n = ngettext(n=3, *messages)
n = ngettext()
n = ngettext('foo')
""")
        messages = list(extract.extract_python(buf, ('_', 'ngettext'), [], {}))
        assert messages[0][2] == ('foo', 'bar')
        assert messages[1][2] == ('hello', 'there', None)
        assert messages[2][2] == (None, 'hello', 'there')
        assert messages[3][2] == (None, None)
        assert messages[4][2] is None
        assert messages[5][2] == 'foo'

    def test_utf8_message(self):
        buf = BytesIO("""
# NOTE: hello
msg = _('Bonjour à tous')
""".encode('utf-8'))
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'],
                                               {'encoding': 'utf-8'}))
        assert messages[0][2] == 'Bonjour à tous'
        assert messages[0][3] == ['NOTE: hello']

    def test_utf8_message_with_magic_comment(self):
        buf = BytesIO("""# -*- coding: utf-8 -*-
# NOTE: hello
msg = _('Bonjour à tous')
""".encode('utf-8'))
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Bonjour à tous'
        assert messages[0][3] == ['NOTE: hello']

    def test_utf8_message_with_utf8_bom(self):
        buf = BytesIO(codecs.BOM_UTF8 + """
# NOTE: hello
msg = _('Bonjour à tous')
""".encode('utf-8'))
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Bonjour à tous'
        assert messages[0][3] == ['NOTE: hello']

    def test_utf8_message_with_utf8_bom_and_magic_comment(self):
        buf = BytesIO(codecs.BOM_UTF8 + """# -*- coding: utf-8 -*-
# NOTE: hello
msg = _('Bonjour à tous')
""".encode('utf-8'))
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Bonjour à tous'
        assert messages[0][3] == ['NOTE: hello']

    def test_utf8_bom_with_latin_magic_comment_fails(self):
        buf = BytesIO(codecs.BOM_UTF8 + """# -*- coding: latin-1 -*-
# NOTE: hello
msg = _('Bonjour à tous')
""".encode('utf-8'))
        with pytest.raises(SyntaxError):
            list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))

    def test_utf8_raw_strings_match_unicode_strings(self):
        buf = BytesIO(codecs.BOM_UTF8 + """
msg = _('Bonjour à tous')
msgu = _(u'Bonjour à tous')
""".encode('utf-8'))
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Bonjour à tous'
        assert messages[0][2] == messages[1][2]

    def test_extract_strip_comment_tags(self):
        buf = BytesIO(b"""\
#: This is a comment with a very simple
#: prefix specified
_('Servus')

# NOTE: This is a multiline comment with
# a prefix too
_('Babatschi')""")
        messages = list(extract.extract('python', buf, comment_tags=['NOTE:', ':'],
                                        strip_comment_tags=True))
        assert messages[0][1] == 'Servus'
        assert messages[0][2] == ['This is a comment with a very simple', 'prefix specified']
        assert messages[1][1] == 'Babatschi'
        assert messages[1][2] == ['This is a multiline comment with', 'a prefix too']

    def test_nested_messages(self):
        buf = BytesIO(b"""
# NOTE: First
_(u'Hello, {name}!', name=_(u'Foo Bar'))

# NOTE: Second
_(u'Hello, {name1} and {name2}!', name1=_(u'Heungsub'),
  name2=_(u'Armin'))

# NOTE: Third
_(u'Hello, {0} and {1}!', _(u'Heungsub'),
  _(u'Armin'))

# NOTE: Fourth
_("Hello %(person)", person=random_function(_("Person")))

# NOTE: Fifth
_("Hello %(people)",
    person=random_function(
        ", ".join([_("Person 1"), _("Person 2")])
    )
)
""")
        messages = list(extract.extract_python(buf, ('_',), ['NOTE:'], {}))
        assert messages[0][2] == 'Foo Bar'
        assert messages[0][3] == ['NOTE: First']
        assert messages[1][2] == ('Hello, {name}!', None)
        assert messages[1][3] == ['NOTE: First']
        assert messages[2][2] == 'Heungsub'
        assert messages[2][3] == ['NOTE: Second']
        assert messages[3][2] == 'Armin'
        assert messages[3][3] == []
        assert messages[4][2] == ('Hello, {name1} and {name2}!', None, None)
        assert messages[4][3] == ['NOTE: Second']
        assert messages[5][2] == 'Heungsub'
        assert messages[5][3] == ['NOTE: Third']
        assert messages[6][2] == 'Armin'
        assert messages[6][3] == []
        assert messages[7][2] == ('Hello, {0} and {1}!', None, None)
        assert messages[7][3] == ['NOTE: Third']
        assert messages[8][2] == 'Person'
        assert messages[8][3] == ['NOTE: Fourth']
        assert messages[9][2] == ('Hello %(person)', None)
        assert messages[9][3] == ['NOTE: Fourth']
        assert messages[10][2] == 'Person 1'
        assert messages[10][3] == []
        assert messages[11][2] == 'Person 2'
        assert messages[11][3] == []
        assert messages[12][2] == ('Hello %(people)', None)
        assert messages[12][3] == ['NOTE: Fifth']


class ExtractTestCase(unittest.TestCase):

    def test_invalid_filter(self):
        buf = BytesIO(b"""\
msg1 = _(i18n_arg.replace(r'\"', '"'))
msg2 = ungettext(i18n_arg.replace(r'\"', '"'), multi_arg.replace(r'\"', '"'), 2)
msg3 = ungettext("Babel", multi_arg.replace(r'\"', '"'), 2)
msg4 = ungettext(i18n_arg.replace(r'\"', '"'), "Babels", 2)
msg5 = ungettext('bunny', 'bunnies', random.randint(1, 2))
msg6 = ungettext(arg0, 'bunnies', random.randint(1, 2))
msg7 = _(hello.there)
msg8 = gettext('Rabbit')
msg9 = dgettext('wiki', model.addPage())
msg10 = dngettext(domain, 'Page', 'Pages', 3)
""")
        messages = \
            list(extract.extract('python', buf, extract.DEFAULT_KEYWORDS, [],
                                 {}))
        assert messages == [
            (5, ('bunny', 'bunnies'), [], None),
            (8, 'Rabbit', [], None),
            (10, ('Page', 'Pages'), [], None),
        ]

    def test_invalid_extract_method(self):
        buf = BytesIO(b'')
        with pytest.raises(ValueError):
            list(extract.extract('spam', buf))

    def test_different_signatures(self):
        buf = BytesIO(b"""
foo = _('foo', 'bar')
n = ngettext('hello', 'there', n=3)
n = ngettext(n=3, 'hello', 'there')
n = ngettext(n=3, *messages)
n = ngettext()
n = ngettext('foo')
""")
        messages = \
            list(extract.extract('python', buf, extract.DEFAULT_KEYWORDS, [],
                                 {}))
        assert len(messages) == 2
        assert messages[0][1] == 'foo'
        assert messages[1][1] == ('hello', 'there')

    def test_empty_string_msgid(self):
        buf = BytesIO(b"""\
msg = _('')
""")
        stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            messages = \
                list(extract.extract('python', buf, extract.DEFAULT_KEYWORDS,
                                     [], {}))
            assert messages == []
            assert 'warning: Empty msgid.' in sys.stderr.getvalue()
        finally:
            sys.stderr = stderr

    def test_warn_if_empty_string_msgid_found_in_context_aware_extraction_method(self):
        buf = BytesIO(b"\nmsg = pgettext('ctxt', '')\n")
        stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            messages = extract.extract('python', buf)
            assert list(messages) == []
            assert 'warning: Empty msgid.' in sys.stderr.getvalue()
        finally:
            sys.stderr = stderr

    def test_extract_allows_callable(self):
        def arbitrary_extractor(fileobj, keywords, comment_tags, options):
            return [(1, None, (), ())]
        for x in extract.extract(arbitrary_extractor, BytesIO(b"")):
            assert x[0] == 1

    def test_future(self):
        buf = BytesIO(br"""
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
nbsp = _('\xa0')
""")
        messages = list(extract.extract('python', buf,
                                        extract.DEFAULT_KEYWORDS, [], {}))
        assert messages[0][1] == '\xa0'

    def test_f_strings(self):
        buf = BytesIO(br"""
t1 = _('foobar')
t2 = _(f'spameggs' f'feast')  # should be extracted; constant parts only
t2 = _(f'spameggs' 'kerroshampurilainen')  # should be extracted (mixing f with no f)
t3 = _(f'''whoa! a '''  # should be extracted (continues on following lines)
f'flying shark'
    '... hello'
)
t4 = _(f'spameggs {t1}')  # should not be extracted
""")
        messages = list(extract.extract('python', buf, extract.DEFAULT_KEYWORDS, [], {}))
        assert len(messages) == 4
        assert messages[0][1] == 'foobar'
        assert messages[1][1] == 'spameggsfeast'
        assert messages[2][1] == 'spameggskerroshampurilainen'
        assert messages[3][1] == 'whoa! a flying shark... hello'

    def test_f_strings_non_utf8(self):
        buf = BytesIO(b"""
# -- coding: latin-1 --
t2 = _(f'\xe5\xe4\xf6' f'\xc5\xc4\xd6')
""")
        messages = list(extract.extract('python', buf, extract.DEFAULT_KEYWORDS, [], {}))
        assert len(messages) == 1
        assert messages[0][1] == 'åäöÅÄÖ'
