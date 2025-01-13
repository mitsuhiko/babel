import subprocess
import sys

from setuptools import Command, setup

try:
    from babel import __version__
except SyntaxError as exc:
    sys.stderr.write(f"Unable to import Babel ({exc}). Are you running a supported version of Python?\n")
    sys.exit(1)


class import_cldr(Command):
    description = 'imports and converts the CLDR data'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        subprocess.check_call([sys.executable, 'scripts/download_import_cldr.py'])


setup(
    name='babel',
    version=__version__,
    description='Internationalization utilities',
    long_description='A collection of tools for internationalizing Python applications.',
    author='Armin Ronacher',
    author_email='armin.ronacher@active-4.com',
    maintainer='Aarni Koskela',
    maintainer_email='akx@iki.fi',
    license='BSD-3-Clause',
    url='https://babel.pocoo.org/',
    project_urls={
        'Source': 'https://github.com/python-babel/babel',
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.8',
    packages=['babel', 'babel.messages', 'babel.localtime'],
    package_data={"babel": ["py.typed"]},
    include_package_data=True,
    install_requires=[
        # This version identifier is currently necessary as
        # pytz otherwise does not install on pip 1.4 or
        # higher.
        # Python 3.9 and later include zoneinfo which replaces pytz
        'pytz>=2015.7; python_version<"3.9"',
        'more-itertools'
    ],
    extras_require={
        'dev': [
            "tzdata;sys_platform == 'win32'",
            'backports.zoneinfo; python_version<"3.9"',
            'freezegun~=1.0',
            'jinja2>=3.0',
            'pytest-cov',
            'pytest>=6.0',
            'pytz',
            'setuptools',
        ],
    },
    cmdclass={'import_cldr': import_cldr},
    zip_safe=False,
    # Note when adding extractors: builtin extractors we also want to
    # work if packages are not installed to simplify testing.  If you
    # add an extractor here also manually add it to the "extract"
    # function in babel.messages.extract.
    entry_points="""
    [console_scripts]
    pybabel = babel.messages.frontend:main

    [distutils.commands]
    compile_catalog = babel.messages.setuptools_frontend:compile_catalog
    extract_messages = babel.messages.setuptools_frontend:extract_messages
    init_catalog = babel.messages.setuptools_frontend:init_catalog
    update_catalog = babel.messages.setuptools_frontend:update_catalog

    [distutils.setup_keywords]
    message_extractors = babel.messages.setuptools_frontend:check_message_extractors

    [babel.checkers]
    num_plurals = babel.messages.checkers:num_plurals
    python_format = babel.messages.checkers:python_format

    [babel.extractors]
    ignore = babel.messages.extract:extract_nothing
    python = babel.messages.extract:extract_python
    javascript = babel.messages.extract:extract_javascript
    """,
)
