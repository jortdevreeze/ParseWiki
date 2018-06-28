ParseWiki
=========

ParseWiki is a Python library that parses Wikipedia pages and saves the page structure. This library extracts all text, headers, references for a specified Wikipedia page.

I have invested a lot of time and effort in creating this Python script, please cite it when using it in the preparation of a manuscript.


Installation
============

To install ParseWiki, simply run:

::

  $ pip install parsewiki


How it works
============
A new instantiation of the Parser creates an empty container for a specified language (default is English) which allows you to parse a specific page, using a page identifier or title. Moreover, this instantiation allows you to parse this page in all other available languages, or to go back in time and to retrieve all revisions created for this page.

The two examples below imports the wiki library and instantiates the Parse class to use the "Python (Programming Language)" Wiki.

.. code:: python

  >>> from parsewiki import page
 
  >>> page = page.Parse(23862)
  >>> page.extract()

or

.. code:: python

  >>> page = wiki.Parse("Python (Programming Language)")
  >>> page.extract()

The default language is English, but if you want to retrieve the German and French version as well use:

.. code:: python

  >>> page.extract(lang="de")
  >>> page.extract(lang="fr")

To get the respective titles of this Wiki in each language:

.. code:: python

  >> page.get_title()
  # 'Python (programming language)'
  >> page.get_title(lang="de")
  # Python (Programmiersprache)
  >> page.get_title(lang="fr")
  # Python (langage)

To get the plain text from the Wikipedia page:

.. code:: python

  >> page.get_text()
  # 'Summary.\nPython is a widely used high-level programming language for ... '

Or the just the first two paragraphs from the German page, without any headers and references in the text:

.. code:: python

  >> page.get_text(lang="de", seq=[1,2], headers=False, references=False)
  # 'Python ([ˈpaɪθn̩], [ˈpaɪθɑn], auf Deutsch auch [ˈpyːtɔn]), ist eine universelle, üblicherweise ... '

It's also possible to get a list of all the headers in the text, or a list of all the references:

.. code:: python

  >> page.get_headers()
  # ['Summary',
  #  'History',
  #  'Features and philosophy',
  #  'Syntax and semantics',
  #  'Libraries',
  #  ...]

The parser is not restricted to extract the current Wikipedia page, but it also allows you to extract revisions done in the past. Suppose you want to extract all revisions made in a specific date range, or made by a specific user:
    
.. code:: python

  >> page.extract_revisions_by_date(first='2017-09-01', last='2017-09-10')
  >> page.extract_revisions_by_user(username='Username')

To get a list of all authors who contributed to the development of this page:

.. code:: python

  >> page.extract_users()
  >> page.extract_users(lang="de")
  >> page.extract_users(lang="fr")
  
  # Get all authors who contributed in the German page
  >> users_de = page.get_users(lang="de")
  
  # Get only registered authors who contributed in the French page
  >> users_fr = page.get_users(lang="fr", whom='registered')
  
  # Get only anonymous authors who contributed in the English page
  >> users_en = page.get_users(whom='anonymous')

To get a list of which authors contributed (i.e., the number of edits) the most on the French page is easy using the Series data structure from Pandas:

.. code:: python

  >> from pandas import Series
  
  >> df = Series(users_fr)
  >> df.sort_values(ascending=False)

