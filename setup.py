# -*- coding: utf-8 -*-
"""
@author: jdevreeze
"""

from setuptools import setup

setup(
    name='parsewiki',
    version='1.0',
    description='Wikipedia parser for Python',
    long_description='Extract Wikipedia pages, revisions, or users',
    url='https://github.com/jortdevreeze/ParseWiki',
    
    # Author details
    author='Jort de Vreeze',
    author_email='j.devreeze@iwm-tuebingen.de',
    
    license='MIT',
    
    classifiers = [
        'Development Status :: 4 - Beta',
        'Topic :: Software Development :: Libraries',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3'
    ],
    
    keywords = "python wikipedia parser API",
    
    packages=['parsewiki'],

    install_requires=['datetime', 'bs4', 'requests']
)
