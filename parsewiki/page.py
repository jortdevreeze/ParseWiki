# -*- coding: utf-8 -*-
"""
@author: jdevreeze
"""

from datetime import datetime, timedelta
from dateutil.parser import parse

import re
import bs4 as bs
import requests
import inspect
  
class Parse:
    """
    This class parses Wikipedia pages and saves its content in a JSON format
    """       
    
    _ignore = True
    _print_errors = True
    
    _prefix = 'https://'
    _suffix = '.wikipedia.org/w/api.php'
    
    _css_selector = 'div.mw-parser-output'
    _css_references = 'ol.references li'
    
    _pageid = None
    _languages = {}
    _content = {}
    
    _log = []
    
    def __init__(self, wiki=None, lang='en', ignore=True):
        """
        Initialize the ParseWiki class.   
        
        Args:
            wiki: The Wiki page identifier, title or a json wiki object (default None).
            lang: The article language which will be used as the default language (default "en").
            ignore: Set to False to raise exeptions, which is helpfull for debugging (default True).

        Raises:
            ValueError: The json object is not valid.
            ValueError: A valid page identifier or previously saved wiki object must be specified.
        """
        if ignore is False:
            self._ignore = False
        
        if wiki is not None:
            
            if type(wiki) is int:
                pageid, languages = self.__extract_metadata(pageid=wiki, title=None, lang=lang)
                self._content = {'id' : str(pageid), 'language' : lang, 'pages' : {}}
            
            elif type(wiki) is str:
                pageid, languages = self.__extract_metadata(pageid=None, title=wiki, lang=lang)
                self._content = {'id' : str(pageid), 'language' : lang, 'pages' : {}}
                
            elif type(wiki) is dict:
                if self.__is_valid(wiki) is True:
                    pageid, languages = self.__extract_metadata(pageid=wiki['id'], title=None, lang=wiki['language'])
                    self._content = wiki
                else:
                    raise ValueError("The json object is not valid.")
            
            else:
                raise ValueError("A valid page identifier or previously saved wiki object must be specified.")
            
            if pageid is False:
                self._content = False
            
            self._pageid = str(pageid)
            self._languages = languages            
                
        else:
            raise ValueError("A valid page identifier or previously saved wiki object must be specified.")
    
    def extract(self, lang=None, lists=True):
        """
        Extract content from the current wikipedia page.
        
        Retrieve content from a Wikipedia pages in a specified language. The content
        is parsed and all html tags are stripped.        
        
        Args:
            lang: The article language (default None).
            lists: Include lists in text (default True).
        
        Returns:
            An instance of the ParseWiki class is returned.
        
        Raises:
            ValueError: The requested page is not available in this language.
        """

        if lang is None:
            lang = list(self._languages['default'].keys())[0] 
            
        else:
            if lang not in self._languages['available']:
                self.__error(self.__line_no(), 'The requested page is not available in this language.', None)
                return False
        
        params = {
            'action' : 'parse',
            'prop' : 'text',
            'format' : 'json',
            'page' : self.get_title(lang).replace(' ', '_')
        } 
        
        try:
            
            compare = self.__extract({
                'action' : 'compare',
                'fromtitle' : self.get_title(lang).replace(' ', '_'),
                'torelative' : 'prev',
                'format' : 'json'               
            }, lang)['compare']
            
        except: 
                   
            self.__error(self.__line_no(), 'The compare key is not found', None)
            compare = ''
            pass
        
        # Check if the page has a previous version
        
        prev = 0 if 'fromrevid' not in compare else compare['fromrevid']       
        
        self._content['pages'][len(self._content['pages'])] = {
            'language' : lang,
            'date' : datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%S%Z'),
            'title' : self.get_title(lang),
            'sections' :  self.__extract_sections(params, lang, lists),
            'references' :  self.__extract_references(params, lang),
            'externallinks' :  self.__extract_links(lang),
            'previous' : prev     
        }

        return self
    
    def extract_revision(self, lang=None, revid=None, date=None, lists=True, newest=False, empty=False):   
        """
        Extract content from a single wikipedia revision page.
        
        Retrieve content from a Wikipedia revision pages in a specified language. The 
        content is parsed and all html tags are stripped.        
        
        Args:
            lang: The article language (default None).
            revid: The revision identifier (default None).
            date: The revision date in 'Y-m-d' format (default None).
            lists: Include lists in text (default True).
            newest: Search for the newest or the oldest revision for the specified 
                date (default False).
            empty: If set as True it will only extract the metadata (default False).
        
        Returns:
            An instance of the ParseWiki class is returned.
        
        Raises:
            ValueError: A revision id or revision date must be specified.
            ValueError: The argument 'newest' must be a boolean value.
            ValueError: The sepcified date is not valid.
            ValueError: The sepcified date could not be converted to a ISO 8601 timestamp.
        """     
        
        if revid is None and date is None:
            self.__error(self.__line_no(), 'A revision id or revision date must be specified.', None)
            return False
        
        if type(newest) is not bool:
            self.__error(self.__line_no(), 'The \'newest\' argument must be a boolean value.', None)
            return False     
        
        else:            
            
            if lang is None:
                lang = list(self._languages['default'].keys())[0]              
            
            if revid is not None:
                
                params = {
                    'action' : 'query',
                    'prop' : 'revisions',
                    'titles' : self.get_title(lang).replace(' ', '_'),
                    'rvprop' : 'ids|flags|timestamp|user|comment|size',
                    'format' : 'json',
                    'rvstartid' : revid,
                    'rvendid' : revid
                }
                
                # Extract revision date
                
                revid, date, user, comment, size = self.__extract_property(params, lang)
                
            else:
                
                try:
                    
                    date = parse(date)
                    latest = parse(self.get_date(lang))
                    delta = latest - date

                    if delta.days <= 0:
                        self.__error(self.__line_no(), 'The sepcified date is not valid.', None)
                        return False   

                except:
                    self.__error(self.__line_no(), 'The sepcified date could not be converted to a ISO 8601 timestamp.', None)
                    return False
                
                if newest is True:
                    rvdir = 'older'
                else:
                    rvdir = 'newer'
                                
                params = {
                    'action' : 'query',
                    'prop' : 'revisions',
                    'titles' : self.get_title(lang).replace(' ', '_'),
                    'rvprop' : 'ids|flags|timestamp|user|comment|size',
                    'format' : 'json',
                    'rvstart' : date,
                    'rvlimit' : '1',
                    'rvdir' : rvdir
                }            
            
                # Extract revision id
            
                revid, date, user, comment, size = self.__extract_property(params, lang)
            
            params = {
                'action' : 'parse',
                'prop' : 'text',
                'format' : 'json',
                'oldid' : revid
            } 
            
            # Check whether the revision already exists
            
            revision = self.__has_revisions(lang, revid)
      
            if revision is None:  
                
                # Extract the revision
                
                revision = {
                    'oldid' : str(revid),
                    'date' : date,
                    'user' : user,
                    'comment' : comment,
                    'size' : size,
                    'empty' : empty
                }               
             
                if empty is not True:
                    
                    revision['sections'] = self.__extract_sections(params, lang, lists)
                    revision['references'] = self.__extract_references(params, lang)
                    revision['externallinks'] = self.__extract_links(lang, oldid=str(revid))
                    
                    try:
                        
                        compare = self.__extract({
                            'action' : 'compare',
                            'fromrev' : str(revid),
                            'torelative' : 'prev',
                            'format' : 'json'               
                        }, lang)['compare']      
                        
                    except:  
                        
                        self.__error(self.__line_no(), 'The compare key is not found', None)
                        compare = ''
                        pass
                    
                    if 'fromrevid' not in compare:
                        prev = 0
                        diff = { 'original' : '', 'difference' : '' } 
                        
                    else:
                        prev = compare['fromrevid']
                        diff = self.__extract_difference(compare['*'])
    
                    revision['previous'] = prev                
                    revision['differences'] = diff         
                    
                for i in self._content['pages']:
                    if lang in self._content['pages'][i]['language']:                    
                        
                        #save revision by the specified language
                        
                        if 'revisions' in self._content['pages'][i]:
                            self._content['pages'][i]['revisions'][len(self._content['pages'][i]['revisions'])] = revision
                        else:
                            self._content['pages'][i]['revisions'] = {0 : revision}
                
        return self    
    
    def extract_revisions_by_user(self, lang=None, username=None, lists=True, empty=False):   
        """
        Extract all revisions made by a Wikipedia user.
        
        Retrieve all revision made by a single user in a specified language. The 
        content is parsed and all html tags are stripped.        
        
        Args:
            lang: The article language (default None).
            username: The Wiki user to look for (default None).
            lists: Include lists in text (default True).
            empty: If set as True it will only extract the metadata (default False).
        
        Returns:
            An instance of the ParseWiki class is returned.
        
        Raises:
            ValueError: A valid username must be specified.
        """
        
        if username is None or type(username) is not str:
            self.__error(self.__line_no(), 'A valid username must be specified.', None)
            return False
            
        params = {
            'action' : 'query',
            'prop' : 'revisions',
            'titles' : self.get_title(lang).replace(' ', '_'),
            'rvprop' : 'ids|flags|timestamp|user|comment|size',
            'format' : 'json',
            'rvlimit' : '500',
            'rvuser' : username.replace(' ', '_')
        }
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]  
      
        while True:

            data = self.__extract(params, lang)
            
            pageid = list(data['query']['pages'].keys())[0]             
            
            # Extract revisions made by this user
            
            if 'revisions' in data['query']['pages'][pageid]:
                for revision in data['query']['pages'][pageid]['revisions']:               
                    self.extract_revision(lang=lang, revid=revision['revid'], lists=lists, empty=empty)            
            
            if 'continue' not in data:
                break
            
            params['rvcontinue'] = data['continue']['rvcontinue']
    
        return self
    
    def extract_revisions_by_date(self, lang=None, first=None, last=None, lists=True, empty=False):   
        """
        Extract all revisions made within a specified timeframe.
        
        Retrieve all revisions made within a specified timeframe in a specified language. 
        The content is parsed and all html tags are stripped. The specified dates should 
        be in the 'Y-m-d' format.
        
        Args:
            lang: The article language (default None).
            first: The first date to look for (default None).
            last: The last date to look for (default None). If no date is specified it 
                will only look for revisions done on the first date.
            lists: Include lists in text (default True).
            empty: If set as True it will only extract the metadata (default False).
        
        Returns:
            An instance of the ParseWiki class is returned.
        
        Raises:
            ValueError: A valid start date must be specified.
            ValueError: A valid end date must be specified.
            ValueError: The specified dates are are newer than date of the main page.
            ValueError: The sepcified dates could not be converted to a ISO 8601 timestamp.
            ValueError: An unexpected error occured while connecting to Wikipedia.
        """
        
        if first is None or type(first) is not str:
            self.__error(self.__line_no(), 'A valid start date must be specified.', None)
            return False
        
        if last is not None and type(last) is not str:
            self.__error(self.__line_no(), 'A valid end date must be specified.', None)
            return False
        
        if last is None:
            last = first
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]          
        
        try:
            
            first = parse(first)
            last = parse(last) + timedelta(hours=23, minutes=59, seconds=59)
            
            dates = [first, last]            
            latest = parse(self.get_date(lang))
            
            for date in dates:            
       
                delta = latest - date    
                if delta.days <= 0:
                    self.__error(self.__line_no(), 'The specified dates are are newer than the main page.', None)
                    return False
            
        except:
            self.__error(self.__line_no(), 'The specified dates could not be converted to a ISO 8601 timestamp.', None)
            return False
          
        params = {
            'action' : 'query',
            'prop' : 'revisions',
            'titles' : self.get_title(lang).replace(' ', '_'),
            'rvprop' : 'ids|flags|timestamp|user|comment|size',
            'format' : 'json',
            'rvlimit' : '500',
            'rvstart' : last,
            'rvend': first
        }
    
        while True:

            data = self.__extract(params, lang)
            
            pageid = list(data['query']['pages'].keys())[0]             
            
            # Extract revisions within the date range
            
            if 'revisions' in data['query']['pages'][pageid]:
                for revision in data['query']['pages'][pageid]['revisions']:               
                    self.extract_revision(lang=lang, revid=revision['revid'], lists=lists, empty=empty)
                
            if 'continue' not in data:
                break
            
            params['rvcontinue'] = data['continue']['rvcontinue']
            
        return self
    
    def extract_users(self, lang=None):   
        """
        Extract all the users who have contributed to this page in a specified language.      
        
        Args:
            lang: The article language (default None).
        
        Returns:
            An instance of the ParseWiki class is returned.
        """     
         
            
        if lang is None:
            lang = list(self._languages['default'].keys())[0]              
        
        params = {
            'action' : 'query',
            'prop' : 'revisions',
            'titles' : self.get_title(lang).replace(' ', '_'),
            'rvprop' : 'user|userid',
            'format' : 'json',
            'rvlimit': '500'
        }
        
        users = {
            'anonymous' : {},
            'registered' : {}
        }
        
        while True:

            data = self.__extract(params, lang)
            
            pageid = list(data['query']['pages'].keys())[0]           
            
            for user in data['query']['pages'][pageid]['revisions']:
                if 'user' in user:
                    if 'anon' in user:
                        users['anonymous'][user['user']] = users['anonymous'].get(user['user'], 1) + 1
                    else:
                        users['registered'][user['user']] = users['registered'].get(user['user'], 1) + 1
            
            if 'continue' not in data:
                break
            
            params['rvcontinue'] = data['continue']['rvcontinue']
            
        for i in self._content['pages']:
            if lang in self._content['pages'][i]['language']:
                self._content['pages'][i]['users'] = users
                
        return self

    def get_wiki(self):
        """
        Retrieve the saved Wikipedia data in a JSON format.     
        
        Returns:
            A dict with all the saved data is returned.
        """
        
        return self._content
    
    def get_page(self, lang=None, revid=None):
        """
        Retrieve the saved Wikipedia page in a JSON format.
        
        Args:
            lang: The article language (default None).
            revid: The revision identifier (default None).
        
        Returns:
            A dict with all the saved data for the reqested page is returned.
            
        Raises:
            The requested page is not available.
            The requested revision is not available.
        """
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]         
        
        if revid is None:
            
            page = self.__has_page(lang)
            
            if page is not None:
                if 'revisions' in page:
                    del page['revisions']
                if 'users' in page:
                    del page['users']                
                return page
            else:
                self.__error(self.__line_no(), 'The requested page is not available.', None)
                return False
        
        else:
            page = self.__has_revisions(lang, revid)
            
            if page is not None:              
                return page
            else:
                self.__error(self.__line_no(), 'The requested revision is not available.', None)
                return False
    
    def get_pageid(self, lang=None, user=None, first=None, last=None):
        """
        Get the page identifiers from saved Wikipedia revision pages. 
        
        This method returns a list of all page identifiers belonging to a user,
        date or date range.
        
        Args:
            lang: The article language (default None).
            user: An author name to look for (default None).
            first: The first date to look for (default None).
            last: The last date to look for (default None). If no date is specified it 
                will only look for revisions done on the first date.
        
        Returns:
            A list with page identifiers.
        
        Raises:
            ValueError: A valid author name must be specified.
            ValueError: A valid start date must be specified.
            ValueError: A valid end date must be specified.
            ValueError: The specified dates could not be converted to a ISO 8601 timestamp.
            ValueError: The start date is more recent than the last date.
            ValueError: The start date is more recent than the last date.
            ValueError: The requested title is not available in this language.
        """
        
        if user is not None and type(user) is not str:
            self.__error(self.__line_no(), 'A valid author name must be specified.', None)
            return False
        
        if first is not None and type(first) is not str:
            self.__error(self.__line_no(), 'A valid start date must be specified.', None)
            return False
        
        if last is not None and type(last) is not str:
            self.__error(self.__line_no(), 'A valid end date must be specified.', None)
            return False
        
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]         
        
        page = self.__has_page(lang)
        
        if page is not None:
            
            pageid = []            
            
            if first is not None:
                if last is None:
                    last = first
                
                try:
                    
                    first = parse(first)
                    first = first.strftime('%Y-%m-%d')
                    
                    last = parse(last)
                    last = last.strftime('%Y-%m-%d')
                    
                except:                    
                    self.__error(self.__line_no(), 'The specified dates could not be converted to a ISO 8601 timestamp.', None)
                    return False
                
                if first > last:
                   self.__error(self.__line_no(), 'The start date is more recent than the last date.', None)
                   return False
                
                if 'revisions' in page:
                    for i in page['revisions']:
                        revision = page['revisions'][i]
                        date = parse(revision['date'])
                        date = date.strftime('%Y-%m-%d')
                        if first <= date <= last:
                            if user is not None and user == revision['user']:
                                pageid.append(revision['oldid'])
                            else:
                                pageid.append(revision['oldid'])
                else:
                    pageid = []
                            
            else:
                
                if last is not None:
                    self.__error(self.__line_no(), 'A valid start date must be specified.', None)
                    return False
                
                if 'revisions' in page:
                    for i in page['revisions']:
                        revision = page['revisions'][i]
                        if user == revision['user']:
                            pageid.append(revision['oldid'])
                else:
                    pageid = []
            
            return pageid
            
        else:     
            self.__error(self.__line_no(), 'The requested title is not available in this language.', None)
            return False
    
    def get_pageviews(self, lang=None, access='all-access', agents='all-agents', interval='daily', first=None, last=None):
        """
        Get the number of page views for the main Wikipedia page. 
        
        This method relies on the REST v1 API from MediaWiki. This API is different
        from the API used for extracting the other data. The number of pageviews are
        only available from October 2015 until today.
        
        For documentation about this API, see: 
        
            https://wikimedia.org/api/rest_v1/ 
        
        Please note that page views can be extracted using the normal MediaWiki API,
        but it does not allow you to specify specific dates:
        
        For documentation about this option, see: 
        
            https://www.mediawiki.org/wiki/Extension:PageViewInfo
        
        Args:
            lang: The article language (default None).
            access: If you want to filter by access method, use one of desktop, mobile-app or 
                mobile-web. If you are interested in pageviews regardless of access method, 
                use all-access (Default).
            agents: If you want to filter by agent type, use one of user, bot or spider. 
                If you are interested in pageviews regardless of agent type, use 
                all-agents (Default)
            interval: The time unit for the response data. The only supported granularity 
                for this endpoint is daily (Default) and monthly.
            first: The first date to look for (default None).
            last: The last date to look for (default None). If no date is specified it 
                will only look for revisions done on the first date.
        
        Returns:
            A dict with the dates and the amount of page views for each date.
        
        Raises:
            ValueError: A valid access filter should be specified.
            ValueError: A valid agent filter should be specified.
            ValueError: A valid interval should be specified.
            ValueError: A valid start date must be specified.
            ValueError: A valid end date must be specified.
            ValueError: The specified dates could not be converted to a YYYYMMDD format.
            ValueError: The start date is more recent than the last date.
            ValueError: A valid start date must be specified.
            ValueError: An unexpected error occured while connecting to Wikipedia.
            ValueError: The request did not return any information.
            ValueError: The requested page is not saved in this language.
        """   

        if access not in ['all-access', 'desktop', 'mobile-app', 'mobile-web']:
            self.__error(self.__line_no(), 'A valid access filter should be specified.', None)
            return False
        
        if agents not in ['all-agents', 'user', 'bot', 'spider']:
            self.__error(self.__line_no(), 'A valid agent filter should be specified.', None)
            return False
        
        if interval not in ['daily', 'monthly']:
            self.__error(self.__line_no(), 'A valid interval should be specified.', None)
            return False
               
        if first is not None and type(first) is not str:
            self.__error(self.__line_no(), 'A valid start date must be specified.', None)
            return False
        
        if last is not None and type(last) is not str:
            self.__error(self.__line_no(), 'A valid end date must be specified.', None)
            return False
        
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]         
        
        page = self.__has_page(lang)
        
        if page is not None:
        
            if first is not None:
                    if last is None:
                        last = first
                    
                    try:
                        
                        first = parse(first)
                        first = first.strftime('%Y%m%d')
                        
                        last = parse(last)
                        last = last.strftime('%Y%m%d')
                        
                    except:                    
                        self.__error(self.__line_no(), 'The specified dates could not be converted to a YYYYMMDD format.', None)
                        return False
                    
                    if first > last:
                        self.__error(self.__line_no(), 'The start date is more recent than the last date.', None)
                        return False
                          
            else:
                
                if last is not None:
                    self.__error(self.__line_no(), 'A valid start date must be specified.', None)
                    return False
                    
                first = datetime.strftime(datetime.now(), '%Y%m%d')
                last = first
            
            title = self.get_title(lang).replace(' ', '_')
            
            # Define variables for the REST v1 API
            
            base = 'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article'
            wiki = lang + '.wikipedia'  
            
            # Merge the paramters into a valid REST v1 API request
            
            rest = '/'.join((base, wiki, access, agents, title, interval, first, last))
            
            # Request the number of page views
            
            resp = requests.get(rest)
            data = resp.json()

            if resp.status_code != requests.codes.ok:
                    if 'detail' in data:
                        self.__error(self.__line_no(), data['detail'], None)
                        return False
                    else:                        
                        self.__error(self.__line_no(), ' '.join(['An unexpected error occured while connecting to Wikipedia (Status code:', resp.status_code, ').']), None)
                        return False
            
            if 'items' not in data:
                self.__error(self.__line_no(), 'The request did not return any information.', None)
                return False
                
            dates = []
            views = []
            
            for item in data['items']:
                dates.append(item['timestamp'])
                views.append(item['views'])
            
            return {'dates' : dates, 'views' : views}            
                
        else:     
            self.__error(self.__line_no(), 'The requested page is not saved in this language.', None)
            return False

    def get_previous(self, lang, revid=None):
        """
        Get the revid from a previous version of a Wikipedia revision 
        page in a specified language.       
        
        Args:
            lang: The article language (default None).
            revid: The revision identifier (default None). If no revid is specified
                use the main page as a reference
        
        Returns:
            The revision identifier (int).
        
        Raises:
            ValueError: The page is not saved in this language.
            ValueError: The requested revision identifier is not available.
        """
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]              
        
        page = self.__has_page(lang)
        
        if page is None:        
            self.__error(self.__line_no(), 'The page is not saved in this language.', None)
            return False
            
        else:
            if revid is not None:
                revision = self.__has_revisions(lang, revid=revid, date=None)
                if revision is not None:
                    return revision['previous']
                else:
                    self.__error(self.__line_no(), 'The requested revision identifier is not available.', None)
                    return False

            else:
                return page['previous']
            
    def get_title(self, lang=None):
        """
        Get the title from a saved Wikipedia page.     
        
        Args:
            lang: The article language (default None).
        
        Returns:
            A string with the Wikipedia page title in the specified language.
        
        Raises:
            ValueError: The requested title is not available in this language.
        """   
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]          
        
        if lang in self._languages['available']:
            return self._languages['available'][lang]
        else:     
            self.__error(self.__line_no(), 'The requested title is not available in this language.', None)
            return False
            
    def get_text(self, lang=None, revid=None, date=None, start=0, length=None, seq=None, references=True, headers=True):
        """
        Extract the plain text from a saved wikipedia page or revision.
        
        Retrieve plain text from a saved Wikipedia page in a specified language. It can be
        specified whether the plain text should include reference numbers or headers.        
        
        Args:
            lang: The article language (default None).
            revid: The revision identifier (default None).
            date: The revision date (default None).
            start: The returned text will start at the start'th paragraph in the wiki, counting 
                from zero (default 0).
            length: If length is given and is positive, the text returned will contain at most the 
                length of paragraphs beginning from start (default None).
            seq: The returned paragraphs is determined by a list containing a sequence of numbers, 
                counting from one. This variable overwrites the start and length values assigned 
                (default None).
            references: Include reference numbers in text (default True).
            headers: Include headers in text (default True).
        
        Returns:
            A string with the plain text.
        
        Raises:
            ValueError: The requested revision is empty.
            ValueError: The requested revision identifier is not available.
            ValueError: The requested revision date is not available.
            ValueError: The page is not saved in this language.
        """  
        if lang is None:
            lang = list(self._languages['default'].keys())[0]  
            
        page = self.__has_page(lang)
        
        if page is not None:
            
            content = list()
            
            #extract headers for a revision page                    
            if revid is not None:                        
                
                revision = self.__has_revisions(lang, revid=revid, date=None)
                
                if revision['empty'] is True:                    
                    self.__error(self.__line_no(), 'The requested revision is empty.', None)
                    return False
                    
                if revision is not None:
                    content = self.__extract_selection(revision['sections'], start, length, seq, headers)
                else:
                    self.__error(self.__line_no(), 'The requested revision identifier is not available.', None)
                    return False
                    
            if date is not None:             
                
                revision = self.__has_revisions(lang, revid=None, date=date)
                
                if revision['empty'] is True:
                    self.__error(self.__line_no(), 'The requested revision is empty.', None)
                    return False
                    
                if revision is not None:
                    content = self.__extract_selection(revision['sections'], start, length, seq, headers)
                else:
                    raise ValueError("The requested revision identifier is not available.")
                    self.__error(self.__line_no(), 'The requested revision identifier is not available.', None)
                    return False
                    
            #extract headers for the current page
            if revid is None and date is None:
                content = self.__extract_selection(page['sections'], start, length, seq, headers)
                
            content = ''.join(content)
            
            if references is False:                
                content = re.sub('\[(.+?)\]', '', content)
            
            return content
            
        else:     
            self.__error(self.__line_no(), 'The page is not saved in this language.', None)
            return False

    def get_user(self, lang=None, revid=None, date=None):
        """
        Get the user who made the Wikipedia revision.     
        
        Args:
            lang: The article language (default None).
            revid: The revision identifier (default None).
            date: The revision date (default None).
        
        Returns:
            A string with the username.
        
        Raises:
            ValueError: The requested revision id is not available.
            ValueError: Revision identifier or revision date are missing.
            ValueError: The requested date is not saved in this language.
        """   
        if lang is None:
            lang = list(self._languages['default'].keys())[0]  
            
        page = self.__has_page(lang)
        
        if page is not None:
                    
            #extract date for a revision page                    
            if revid is not None:                        
                revision = self.__has_revisions(lang, revid=revid, date=None)
                if revision is not None:
                    return revision['user']                    
                else:
                  self.__error(self.__line_no(), 'The requested revision id is not available.', None)
                  return False
                  
            if date is not None:           
                revision = self.__has_revisions(lang, revid=None, date=date)
                if revision is not None:
                    return revision['user']  
                else:
                    self.__error(self.__line_no(), 'Revision identifier or revision date are missing.', None)
                    return False
                    
        else:     
            self.__error(self.__line_no(), 'The requested page is not saved in this language.', None)
            return False
    
    def get_users(self, lang=None, whom='all'):
        """
        Get the user who made the Wikipedia revision.     
        
        Args:
            lang: The article language (default None).
            whom: Retrieve 'registered', 'anonymous', or 'all' users (default 'all').
        
        Returns:
            A dict with the usernames and the amount of contributions.
        
        Raises:
            ValueError: The users who contributed to this page have not been extracted.
            ValueError: The type of users specified is not valid.
            ValueError: The requested page is not saved in this language.
        """   
        if lang is None:
            lang = list(self._languages['default'].keys())[0]  
            
        page = self.__has_page(lang)
        
        if page is not None:
                    
            #extract all users who contributed to this page
                    
            if 'users' not in page: 
                self.__error(self.__line_no(), 'The users who contributed to this page have not been extracted.', None)
                return False
            
            if whom is 'all':
                return {**page['users']['registered'], **page['users']['anonymous']}
            elif whom is 'registered':
                return page['users']['registered']
            elif whom is 'anonymous':
                return page['users']['anonymous']
            else:
                self.__error(self.__line_no(), 'The type of users specified is not valid.', None)
                return False
          
        else:     
            self.__error(self.__line_no(), 'The requested page is not saved in this language.', None)
            return False
    
    def get_date(self, lang=None, revid=None):
        """
        Get the date from a saved Wikipedia revision.     
        
        Args:
            lang: The article language (default None).
            revid: The revision identifier (default None).
        
        Returns:
            A string with the Wikipedia revision date for the specified language.
        
        Raises:
            ValueError: The requested revision id is not available.
            ValueError: The requested date is not saved in this language.
        """   
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]  
            
        page = self.__has_page(lang)
        
        if page is not None:
                    
            #extract date for a revision page                    
            if revid is not None:
                revision = self.__has_revisions(lang, revid)                        
                if revision is not None:
                    return revision['date']                    
                else:
                  self.__error(self.__line_no(), 'The requested revision id is not available.', None)
                  return False
            else:
                return page['date']
                    
        else:     
            self.__error(self.__line_no(), 'The requested page is not saved in this language.', None)
            return False
    
    def get_metadata(self, lang=None, revid=None):
        """
        Retrieve the metadata from a saved Wikipedia page or revision.
        
        Args:
            lang: The article language (default None).
            revid: The revision identifier (default None).
        
        Returns:
            A dict with all the metadata for the reqested page or revision is returned.
            
        Raises:
            The requested page or revision is not available.
        """
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]         
        
        if revid is None:            
            page = self.__has_page(lang)        
        else:
            page = self.__has_revisions(lang, revid)
            
            
        if page is not None:              
            return {
                'date' : page['date'],
                'user' : page['user'],
                'comment' : page['comment'],
                'size' : page['size']
            }
            
        else:
            self.__error(self.__line_no(), 'The requested page is not saved in this language.', None)
            return False
    
    def get_headers(self, lang=None, revid=None, date=None):
        """
        Extract all the headers from a saved wikipedia page.
        
        Retrieve the headers from a Wikipedia page in a specified language. The 
        headers are returned in a list. Note that some headers are by default not 
        included (notes, references, and external links).
        
        Args:
            lang: The article language (default None).
            revid: The revision identifier (default None).
            date: The revision date (default None).
        
        Returns:
            A list with all the headers used in the article
        
        Raises:
            ValueError: The headers are not saved in this language.
        """
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]
            
        page = self.__has_page(lang)

        if page is not None:
      
            headers = list()
            
            #extract headers for a revision page                    
            if revid is not None:                        
                revision = self.__has_revisions(lang, revid=revid, date=None)
                if revision is not None and revision['empty'] is False:
                    for j in revision['sections']:
                        headers.append(revision['sections'][j]['header'])
            
            if date is not None:             
                revision = self.__has_revisions(lang, revid=None, date=date)
                if revision is not None and revision['empty'] is False:
                    for j in revision['sections']:
                        headers.append(revision['sections'][j]['header'])
            
            #extract headers for the current page
            if revid is None and date is None:
                for j in page['sections']:
                    headers.append(page['sections'][j]['header'])
                    
            return headers
                    
        else:     
            self.__error(self.__line_no(), 'The headers are not saved in this language.', None)
            return False
    
    def get_references(self, lang=None, revid=None, date=None):
        """
        Extract all the references from a saved wikipedia page.
        
        Retrieve the references from a Wikipedia page in a specified language. The 
        references are returned in a list.
        
        Args:
            lang: The article language (default None).
            revid: The revision identifier (default None).
            date: The revision date (default None).
        
        Returns:
            A list with all the references used in the article
        
        Raises:
            ValueError: The references are not saved in this language.
        """
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]  
            
        page = self.__has_page(lang)
        
        if page is not None:
                    
            references = list()
            
            #extract references for a revision page
                   
            if revid is not None :                        
                revision = self.__has_revisions(lang, revid=revid, date=None)
                if revision is not None and revision['empty'] is False:
                    references = revision['references']
            
            if date is not None:             
                revision = self.__has_revisions(lang, revid=None, date=date)
                if revision is not None and revision['empty'] is False:
                    references = revision['references']
            
            #extract references for the current page
            
            if revid is None and date is None:
                references = page['references']
                    
            return references
                    
        else:     
            self.__error(self.__line_no(), 'The references are not saved in this language.', None)
            return False
    
    def get_differences(self, lang=None, revid=None, date=None, compare=False):
        """
        Extract all the differences from a saved wikipedia page compared to its previous version.
        
        Retrieve the differences from a saved wikipedia page compared to its previous version 
        in a specified language. The differences are returned in a list.
        
        Args:
            lang: The article language (default None).
            revid: The revision identifier (default None).
            date: The revision date (default None).
            compare: A flag to specify if the script should only return the difference or also the previous
        
        Returns:
            A list with all the differences used in the requested page, and optional a list with the original
        
        Raises:
            ValueError: Retrieving the differences of the current page are not supported yet.
            ValueError: The differences are not saved in this language.
        """
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]  
            
        page = self.__has_page(lang)
        
        if page is not None:
                    
            differences = list()
            original = list()
            
            #extract differences for a revision page
            if revid is None and date is None:
                self.__error(self.__line_no(), 'Retrieving the differences of the current page are not supported yet.', None)
                return False
                   
            if revid is not None and revision['empty'] is False:                        
                revision = self.__has_revisions(lang, revid=revid, date=None)

            if date is not None and revision['empty'] is False:             
                revision = self.__has_revisions(lang, revid=None, date=date)
                
            if revision is not None and revision['empty'] is False:
                differences = revision['differences']['difference']
                original = revision['differences']['original']
            
            if compare is True:
                return differences, original
                
            return differences
                    
        else:     
            self.__error(self.__line_no(), 'The differences are not saved in this language.', None)
            return False
    
    def has_content(self, lang=None, revid=None, date=None):
        """
       Method which checks whether a page or revision has content.    
        
        Args:
            lang: The article language (default None).
            revid: The revision identifier (default None).
            date: The revision date (default None).
        
        Returns:
            True if a page has content, otherwise false.
        """ 
        
        if lang is None:
            lang = list(self._languages['default'].keys())[0]  
            
        page = self.__has_page(lang)
        
        if page is None:
            return False
        
        else:  
            
            content = list()
               
            if revid is not None:                        
                revision = self.__has_revisions(lang, revid=revid, date=None)                    
            if date is not None:             
                revision = self.__has_revisions(lang, revid=None, date=date)
                
            try:
                content = revision['sections']
            except:
                return False
                    
            #extract headers for the current page
            if revid is None and date is None:
                try:
                    content = page['sections']
                except:
                    return False
                
            if len(content) == 0:
                return False
            
            return True
    
    def __is_valid(self, wiki):
        """
        Internal method which checks if a json object is valid.    
        
        Args:
            wiki: A dict of a previous saved wikipedia page.
        
        Returns:
            True if the json oject is valid. False when the json object is not valid.
        """
        
        if ('id' in wiki 
            and 'language' in wiki 
            and 'pages' in wiki):
            
            # In case an empty wiki object is saved without any extracted pages
            if not wiki['pages']:
                return True
                
            else:
                
                # Check the first page. If this is correct then assume the others are correct as well
                validate = wiki['pages']['0']
                
                if ('date' in validate 
                    and 'title' in validate
                    and 'language' in validate
                    and 'sections' in validate
                    and 'references' in validate):

                    if 'revisions' not in validate:
                        return True
                        
                    else:
                        
                        # Check the revision. If this is correct then assume the others are correct as well
                        revision = validate['revisions']['0']
                        
                        if ('user' in revision 
                            and 'oldid' in revision
                            and 'comment' in revision
                            and 'date' in revision
                            and 'sections' in revision
                            and 'references' in revision):
                            
                            return True
                        
                        else:
                            return False
                
                else:
                    return False
                    
        else:
            return False    
    
    def __has_page(self, lang):
        """
        Internal method which checks whether a page exists.    
        
        Args:
            lang: The article language.
        
        Returns:
            None if the page does not exist; A dict with the page data 
            if the revision exists.
        """ 
        
        if lang in self._languages['available']:
            for i in self._content['pages']:
                if lang in self._content['pages'][i]['language']:
                    return self._content['pages'][i]
        return None
        
    def __has_revisions(self, lang, revid=None, date=None):
        """
        Internal method which checks whether a revision exists.
        
        Args:
            lang: The article language.
            revid: The revision identifier (default None).
            date: The revision date (default None).
        
        Returns:
            None if the revision does not exist; A dict with the revision
            data if the revision exists.
        """

        page = self.__has_page(lang)
        if page is not None:
            if 'revisions' in page:
                if revid is not None:
                    for j in page['revisions']:
                        if str(revid) in page['revisions'][j]['oldid']:
                            return page['revisions'][j]       
                if date is not None:
                    date = parse(date)
                    date = date.strftime('%Y-%m-%d')
                    for j in page['revisions']:
                        revdate = parse(page['revisions'][j]['date'])
                        revdate = revdate.strftime('%Y-%m-%d')
                        if date == revdate:
                            return page['revisions'][j]
        return None
    
    def __extract(self, params, lang):
        """
        Internal method which extracts information from the MediaWiki API.    
        
        Args:
            params: A dict with the WikiMedia API paramaters to extract the previous 
                revision identifier.
            lang: The article language.
        
        Returns:
            A string with the previous revision identifier.
        
        Raises:
            ValueError: An unexpected error occured while connecting to Wikipedia.
        """
        
        url = self._prefix + lang + self._suffix       
        
        resp = requests.get(url, params)
        
        if resp.status_code != requests.codes.ok:
             raise ValueError("An unexpected error occured while connecting to Wikipedia (Status code: ", resp.status_code, ").")
        
        return resp.json()
    
    def __extract_metadata(self, pageid, title, lang):
        """
        Internal method which extracts the wiki metadata to setup this class.    
        
        Args:
            pageid: The Wiki page identifier.
            title: The Wiki page title.
            lang: The article language.
        
        Returns:
            True if the metadata is succesfully extracted and saved
            
        Raises:
            ValueError: The page you specified doesn't exist.
        """
        
        if pageid is None:
            
            params = {
                'action' : 'parse',
                'prop' : 'langlinks',
                'page' : title.replace(' ', '_'),
                'format' : 'json'
            }
            
        else:
            
            params = {
                'action' : 'parse',
                'prop' : 'langlinks',
                'pageid' : pageid,
                'format' : 'json'
            }
        
        data = self.__extract(params, lang)

        if 'error' in data:
            self.__error(self.__line_no(), 'The page you specified doesn\'t exist.', None)
            return False, False
            
        else:
            
            pageid = data['parse']['pageid']            
            
            languages = {
                'default' : {},
                'available' : {}
            }            
            
            languages['default'][lang] = data['parse']['title']
            languages['available'][lang] = data['parse']['title'] 
            
            for i in data['parse']['langlinks']:
                languages['available'][i['lang']] = i['*']
                
            return pageid, languages   
        
    def __extract_property(self, params, lang):
        """
        Internal method which extracts the revision identifier and timestamp.    
        
        Args:
            params: A dict with the WikiMedia API paramaters to extract the revision 
                identifier and timestamp.
            lang: The article language.
        
        Returns:
            A string with the revision identifier, timestamp, user, and user comment.
        """
        
        data = self.__extract(params, lang)
        
        pageid = list(data['query']['pages'].keys())[0]

        root = data['query']['pages'][pageid]['revisions'][0]
        
        # Some revisions do not have the 'comment' argument
        if 'comment' not in root:
            root['comment'] = ''

        return root['revid'], root['timestamp'], root['user'], root['comment'], root['size']
    
    def __extract_selection(self, content, start, length, seq, headers):
        """
        Internal method which extracts a selection of paragraphs from the wikipedia page.  
        
        Args:
            content: All paragraphs and headers in the wikipedia page.
            start: The first paragraph to extract.
            length: The length of the number of paragraphs to extract.
            seq: The returned paragraphs is determined by a list containing a sequence of numbers.
            headers: Include headers in text (default True).
        
        Returns:
            A selections of paragraphs from the wikipedia page.
            
        Raises:
            ValueError: The provided length value is not valid.
            ValueError: Unable to create a valid sequence with the povided start and length values.
            ValueError: The sequence is out of range.
            ValueError: The provided sequence value is not a list.
            ValueError: The provided values in the sequence list contains a non-number.
            ValueError: The largest value in the sequence list is larger than the number of paragraphs in the Wiki.
            ValueError: The smallest value in the sequence list is smaller than 1.
        """
        
        # Create sequence is none is specified
        
        if len(content) == 0:
            self.__error(self.__line_no(), 'The requested wikipedia page is empty.', None)
            return False
        
        if seq is None:
            
            if start is 0 and length is None:
                seq = list(range(len(content)))
                
            elif type(start) is int:

                # redefine the start position of the sequence when a negative value is given                
                if start < 0:
                    start = len(content) - abs(start)
                
                # length needs to be larger or smaller than 0 otherwise an empty string is returned.
                if length is not None:

                    if length > 0:
                        stop = start + length
                    elif length < 0:
                        stop = len(content) - abs(length)
                    else:
                        return ''
      
                else:
                    stop = len(content)
                
                if stop > len(content):
                    stop = len(content)                
                
                if start is stop:
                    seq = [start]
                elif start < stop:
                    seq = list(range(start, stop))
                else:
                    return ''

            else:
                self.__error(self.__line_no(), 'Unable to create a valid sequence with the povided start and length values.', None)
                return False
            
            seq[:] = [x + 1 for x in seq]

            if seq[0] > seq[-1]:
                self.__error(self.__line_no(), 'The sequence is out of range.', None)
                return False
            
        # Run sequence
        
        selection = list()        

        if type(seq) is not list:
            self.__error(self.__line_no(), 'The provided sequence value is not a list.', None)
            return False
        elif not all(isinstance(s, int) for s in seq):
            self.__error(self.__line_no(), 'The provided values in the sequence list contains a non-number.', None)
            return False
        else:
            
            seq.sort()
            seq = list(set(seq))

            if seq[-1] > len(content):
                self.__error(self.__line_no(), 'The largest value in the sequence list is larger than the number of paragraphs in the Wiki.', None)
                return False
            elif seq[0] < 1:
                self.__error(self.__line_no(), 'The smallest value in the sequence list is smaller than 1.', None)
                return False
            else:                
                                
                seq[:] = [x - 1 for x in seq]
                
                for i in seq:  
                    if headers is True:
                        selection.append(content[i]['header'] + '.\n')
                    selection.append(content[i]['content'] + '\n')

        return selection
    
    def __extract_sections(self, params, lang, lists):
        """
        Internal method which extracts the headers and corresponding paragraphs from a 
        Wikipedia page.    
        
        Args:
            params: A dict with the WikiMedia API paramaters to extract the Wikipedia page.
            lang: The article language (default "en").
            lists: Include lists in text.
        
        Returns:
            A dict with all headers and corresponding paragraphs.
        """
        
        sections = {}
        
        data = self.__extract(params, lang)

        soup = bs.BeautifulSoup(data['parse']['text']['*'], 'html.parser')
        
        soup = bs.BeautifulSoup(
            str(soup.select(self._css_selector)), 'html.parser'
        )
        
        # Remove everything except headings and paragraphs
        
        content = str(self.__clear_html(soup, lists))
        
        # Parse headers and paragraphs
        
        content = '\n'.join([ll.rstrip() for ll in content.splitlines() if ll.strip()])
        content = re.sub('<\/[^<]+?>', '', content)
        content = re.sub('\n', '', content)
        content = content.replace('<p>', '<*>').replace('<h2>', '<*>[header]')
        content = re.split('<[^<]+?>', content)        
        
        content[0] = '[header]Summary'
        
        content = content[0:-1]
        
        index = list()
        
        i = 0
        for section in content:        
            if '[header]' in section: 
                index.append(i)
            i += 1
        
        sections = {}
        
        for j in index:
            
            h = content[j].replace('[header]', '')            
            s = j + 1
            
            if len(index) > 1:
                
                e = index[1] - 1

                if s is e:
                    p = [content[s]]
                else:
                    p = ['\n'.join(content[s:e])]
                    
                sections[len(sections)] = {'header': h, 'content' : p}
            
            else:
                
                e = len(content)
                p = ['\n'.join(content[s:e])]
                sections[len(sections)] = {'header': h, 'content' : p} 
                
            index = index[1:]

        content = {}
        for k in sections.keys():
            if '' not in sections[k]['content']:
                content[len(content)] = { 'header' : sections[k]['header'], 'content' : sections[k]['content'][0] }
        
        return content
    
    def __extract_links(self, lang, oldid=None):
        """
        Internal method which extracts all the external links in the Wikipedia page.    
        
        Args:
            lang: The article language.
            oldid: Parse the content of this revision identifier (default None).
        
        Returns:
            A list with all the external links.
        """
        
        params = {
            'action' : 'parse',
            'prop' : 'externallinks',
            'format' : 'json',
        }
        
        if oldid is None:
            params['page'] = self.get_title(lang).replace(' ', '_')
            
        else:
            params['oldid'] = oldid 
            
        data = self.__extract(params, lang)
        
        return data['parse']['externallinks']   
    
    def __extract_references(self, params, lang):
        """
        Internal method which extracts the references from a Wikipedia page.    
        
        Args:
            params: A dict with the WikiMedia API paramaters to extract the Wikipedia page.
            lang: The article language (default "en").
        
        Returns:
            A list with all the references.
        """
        
        references = []
        
        data = self.__extract(params, lang)
        
        soup = bs.BeautifulSoup(data['parse']['text']['*'], 'html.parser')

        soup = bs.BeautifulSoup(
            str(soup.select(self._css_references)), 'html.parser'
        )
        
        # Remove html but keep text
        elements = soup.findAll('sup')
        for element in elements:
            element.replace_with('')
      
        elements = soup.findAll('span', attrs={'class' : 'mw-cite-backlink'})
        for element in elements:
            element.replace_with('')
        
        elements = soup.findAll('span', attrs={'style' : 'font-style:normal'})
        for element in elements:
            element.replaceWithChildren()
            
        elements = soup.findAll('span', attrs={'style' : True})
        for element in elements:
            element.replace_with('')

        for li in soup.findAll('li'):
            reference = li.get_text()
            reference = re.sub('\^\s', '', reference)
            references.append(reference)

        return references
    
    def __extract_difference(self, content):
        """
        Internal method which extracts the changes from a Wikipedia revision page.    
        
        Args:
            content: A string with the extracted html data.
        
        Returns:
            A list with all the changes in the revision and the previous revision.
            
        Raises:
            ValueError: Expecting one column when something new is added or two columns if somthing was changed, but more columns were found.
        """

        soup = bs.BeautifulSoup(content, 'html.parser')

        original = []
        difference = []
        
        table = False
        
        for tr in soup.findAll('tr'):
        
            for td in tr.findAll('td'):
                
                if 'diff-marker' in td.get('class')[0]:
                    
                    if '+' in td.get_text() or '-' in td.get_text():
                        el = td.parent                
                        el = el.findAll('div')
                        
                        # A new piece is added
                        
                        if len(el) < 2:
                            
                            for e in el:                   
                                
                                # Skip tables
                                
                                if '{|' in e.get_text():
                                    table = True
                                if '|}' in e.get_text():
                                    table = False
                                    
                                if table is False:
                                    
                                    content = self.__clear_differences(e.get_text())
                                        
                                    if content is not '':
                                        original.append('')
                                        difference.append(self.__clear_differences(e.get_text()))
                        
                        # Something has changed
                        
                        elif len(el) is 2:
                            
                            flag = False
                            
                            for e in el:                    
                                
                                # Skip tables
                                
                                if '{|' in e.get_text():
                                    table = True
                                if '|}' in e.get_text():
                                    table = False
                                    
                                if table is False:
                                    
                                    if flag is False:
                                        
                                        content = self.__clear_differences(e.get_text())
                                        
                                        if content is not '':
                                            original.append(self.__clear_differences(e.get_text()))
                                        
                                        flag = True
                                        
                                    else:
                                        
                                        content = self.__clear_differences(e.get_text())
                                        
                                        if content is not '':
                                            difference.append(self.__clear_differences(e.get_text()))

                                        flag = False
                                        
                        else:                    
                            self.__error(self.__line_no(), 'Expecting one column when something new is added or two columns if somthing was changed, but more columns were found.', None)
                            return False
        
        return { 'original' : original, 'difference' : difference }
    
    def __clear_differences(self, content):
        """
        Internal method which strips some non-content data from differences string.  
        
        This function strips some (but not all) unrelated html tags and unrelated content.        
        
        Args:
            content: A string with the extracted html data.
        
        Returns:
            A string with the processed data.
        """
        content = re.sub('<ref(.*?)</ref>|<ref(.*?)/>', '', content) 
        content = re.sub('[[]{2}(File:|Category:)(.*?)]{2}', '', content)
        content = re.sub('[{]{2}(.*?)[}]{2}', '', content)
        
        def filter_links(m):
            return re.sub('[[]{2}(.*?)[|]|]]', '', m.group(0))            
        
        content = re.sub('[[]{2}(.*?)[|](.*?)]{2}', filter_links, content)
        content = re.sub('[[]{2}|]{2}', '', content)
        content = re.sub('(=){2,4}(.*?)(=){2,4}', '', content)
        
        def filter_layout(m):
            return re.sub('(\'){2,4}|(\'){2,4}', '', m.group(0)) 
            
        content = re.sub('(\'){2,4}(.*?)(\'){2,4}', filter_layout, content)        
        content = re.sub('([|]})', '', content)
        
        return content
    
    def __clear_html(self, content, lists):
        """
        Internal method which parses a Wikipedia page.  
        
        This function strips all unrelated html tags and unrelated content.        
        Note that this function is subject to change in case the html layout 
        of Wikipedia changes.
        
        Args:
            content: A string with the extracted html data.
            lists: Include lists (ul, ol, or dl tags) in text.
        
        Returns:
            A string with the processed data.
        """

        # Remove first div, but keep all content

        elements = content.find('div').replaceWithChildren()
        
        # Remove remaining div from the page
        
        elements = content.findAll('div')
        for element in elements:
            element.replace_with('')

        # Remove tables from the page

        elements = content.findAll('table')
        for element in elements:
            element.replace_with('')
        
         # Remove scripts from the page
        
        elements = content.findAll('noscript')
        for element in elements:
            element.replace_with('')  
        
        # Remove lists from the page
        
        elements = content.findAll('ul')
        for element in elements:
            if lists is True:
                element.replaceWithChildren()
            else:
                element.replace_with('')
        elements = content.findAll('ol')
        for element in elements:
            if lists is True:
                element.replaceWithChildren()
            else:
                element.replace_with('')
        elements = content.findAll('dl')
        for element in elements:
            if lists is True:
                element.replaceWithChildren()
            else:
                element.replace_with('')

        # Remove additional information

        elements = content.findAll('span', attrs={"id": "coordinates"})
        for element in elements:
            element.replace_with('')
        elements = content.findAll('span', attrs={"class": "mw-editsection"})
        for element in elements:
            element.replace_with('')
        
        # Remove comments
        
        comments = content.findAll(text=lambda text:isinstance(text, bs.Comment))
        [comment.extract() for comment in comments]
        
        # Remove sub headers
        
        elements = content.findAll('h3')
        for element in elements:
            element.replace_with('')                
        
        # Remove html but keep text
        
        elements = content.findAll('a')
        for element in elements:
            element.replaceWithChildren()
        
        elements = content.findAll('b')
        for element in elements:
            element.replaceWithChildren()  
        
        elements = content.findAll('sup')
        for element in elements:
            element.replaceWithChildren()
        
        elements = content.findAll('i')
        for element in elements:
            element.replaceWithChildren()
        
        elements = content.findAll('span')
        for element in elements:
            element.replaceWithChildren()
        
        elements = content.findAll('abbr')
        for element in elements:
            element.replaceWithChildren()
        
        # Remove empty paragraphs
        
        empty = content.findAll(lambda tag: tag.name == 'p' and not tag.contents and (tag.string is None or not tag.string.strip()))
        [empty.extract() for empty in empty]
                
        return content
        
    def __line_no(self):
        """
        Internal method to get the current line number.
        
        Returns:
            An integer with the current line number.
        """
        
        return inspect.currentframe().f_back.f_lineno
        
    def __error(self, line, error, etype):
        """
        Internal method to handle errors.    
        
        Args:
            line: An integer with the current line number
            error: A string with the error message.
            etype: A string with the error type
        """

        if self._print_errors is True:
            print('Line:', line, '-', error)
            
        self._log.append((datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%S%Z'), line, error, etype))
        
        if self._ignore is False:
            raise ValueError(error)

