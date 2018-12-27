# -*- coding: utf-8 -*-
"""
    babel.localedata
    ~~~~~~~~~~~~~~~~

    Low-level locale data access.

    :note: The `Locale` class, which uses this module under the hood, provides a
           more convenient interface for accessing the locale data.

    :copyright: (c) 2013-2018 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""

import os
import threading

from babel._compat import pickle, string_types, abc


_dirname = os.path.join(os.path.dirname(__file__), 'locale-data')


class _LocaleData(object):
    def __init__(self):
        self._cache = {}
        self._cache_lock = threading.RLock()
        self._locale_identifiers = None
        self._locale_identifiers_normalization_map = None

    def locale_identifiers_normalization_map(self):
        if self._locale_identifiers_normalization_map is None:
            self._locale_identifiers_normalization_map = {
                s.lower(): s for s in self.locale_identifiers()
            }

        return self._locale_identifiers_normalization_map

    def normalize_locale(self, name):
        """Normalize a locale ID by stripping spaces and apply proper casing.

        Returns the normalized locale ID string or `None` if the ID is not
        recognized.
        """
        if not name or not isinstance(name, string_types):
            return None

        name = name.strip().lower()
        return self.locale_identifiers_normalization_map().get(name)

    def exists(self, name):
        """Check whether locale data is available for the given locale.

        Returns `True` if it exists, `False` otherwise.

        :param name: the locale identifier string
        """
        if not name or not isinstance(name, string_types):
            return False

        if name in self._cache:
            return True

        return self.normalize_locale(name) is not None

    def locale_identifiers(self):
        """Return a list of all locale identifiers for which locale data is
        available.

        .. versionadded:: 0.8.1

        :return: a list of locale identifiers (strings)
        """
        if self._locale_identifiers is None:
            self._locale_identifiers = set()
            for filename in os.listdir(_dirname):
                stem, ext = os.path.splitext(filename)
                if ext == '.dat' and stem != 'root':
                    self._locale_identifiers.add(stem)

        return list(self._locale_identifiers)

    def load(self, name, merge_inherited=True):
        """Load the locale data for the given locale.

        The locale data is a dictionary that contains much of the data defined by
        the Common Locale Data Repository (CLDR). This data is stored as a
        collection of pickle files inside the ``babel`` package.

        >>> d = load('en_US')
        >>> d['languages']['sv']
        u'Swedish'

        Note that the results are cached, and subsequent requests for the same
        locale return the same dictionary:

        >>> d1 = load('en_US')
        >>> d2 = load('en_US')
        >>> d1 is d2
        True

        :param name: the locale identifier string (or "root")
        :param merge_inherited: whether the inherited data should be merged into
                                the data of the requested locale
        :raise `IOError`: if no locale data file is found for the given locale
                          identifier, or one of the locales it inherits from
        """
        self._cache_lock.acquire()
        name = 'root' if name == 'root' else self.normalize_locale(name)
        try:
            data = self._cache.get(name)
            if not data:
                # Load inherited data
                if name == 'root' or not merge_inherited:
                    data = {}
                else:
                    from babel.core import get_global
                    parent = get_global('parent_exceptions').get(name)
                    if not parent:
                        parts = name.split('_')
                        if len(parts) == 1:
                            parent = 'root'
                        else:
                            parent = '_'.join(parts[:-1])
                    data = self.load(parent).copy()
                filename = os.path.join(_dirname, '%s.dat' % name)
                with open(filename, 'rb') as fileobj:
                    if name != 'root' and merge_inherited:
                        merge(data, pickle.load(fileobj))
                    else:
                        data = pickle.load(fileobj)
                self._cache[name] = data

            return data
        finally:
            self._cache_lock.release()


def merge(dict1, dict2):
    """Merge the data from `dict2` into the `dict1` dictionary, making copies
    of nested dictionaries.

    >>> d = {1: 'foo', 3: 'baz'}
    >>> merge(d, {1: 'Foo', 2: 'Bar'})
    >>> sorted(d.items())
    [(1, 'Foo'), (2, 'Bar'), (3, 'baz')]

    :param dict1: the dictionary to merge into
    :param dict2: the dictionary containing the data that should be merged
    """
    for key, val2 in dict2.items():
        if val2 is not None:
            val1 = dict1.get(key)
            if isinstance(val2, dict):
                if val1 is None:
                    val1 = {}
                if isinstance(val1, Alias):
                    val1 = (val1, val2)
                elif isinstance(val1, tuple):
                    alias, others = val1
                    others = others.copy()
                    merge(others, val2)
                    val1 = (alias, others)
                else:
                    val1 = val1.copy()
                    merge(val1, val2)
            else:
                val1 = val2
            dict1[key] = val1


class Alias(object):
    """Representation of an alias in the locale data.

    An alias is a value that refers to some other part of the locale data,
    as specified by the `keys`.
    """

    def __init__(self, keys):
        self.keys = tuple(keys)

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self.keys)

    def resolve(self, data):
        """Resolve the alias based on the given data.

        This is done recursively, so if one alias resolves to a second alias,
        that second alias will also be resolved.

        :param data: the locale data
        :type data: `dict`
        """
        base = data
        for key in self.keys:
            data = data[key]
        if isinstance(data, Alias):
            data = data.resolve(base)
        elif isinstance(data, tuple):
            alias, others = data
            data = alias.resolve(base)
        return data


class LocaleDataDict(abc.MutableMapping):
    """Dictionary wrapper that automatically resolves aliases to the actual
    values.
    """

    def __init__(self, data, base=None):
        self._data = data
        if base is None:
            base = data
        self.base = base

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, key):
        orig = val = self._data[key]
        if isinstance(val, Alias):  # resolve an alias
            val = val.resolve(self.base)
        if isinstance(val, tuple):  # Merge a partial dict with an alias
            alias, others = val
            val = alias.resolve(self.base).copy()
            merge(val, others)
        if type(val) is dict:  # Return a nested alias-resolving dict
            val = LocaleDataDict(val, base=self.base)
        if val is not orig:
            self._data[key] = val
        return val

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def copy(self):
        return LocaleDataDict(self._data.copy(), base=self.base)


_locale_data_instance = _LocaleData()
normalize_locale = _locale_data_instance.normalize_locale
load = _locale_data_instance.load
locale_identifiers = _locale_data_instance.locale_identifiers
exists = _locale_data_instance.exists
