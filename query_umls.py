# -*- coding: utf-8 -*-
"""
Created on Wed Apr 28 13:44:27 2021

*** Search the UMLS Metathesaurus via the REST API ***

You will first need to do the following:
    
- Register for an account https://www.nlm.nih.gov/databases/umls.html
- Log into your account and copy the API key from the 'My Profile' area.
- Copy/paste the API key into the code below or import it via a lib etc.

Usage:
    Search the Metathesaurus for strings.
    Optionally: Specify one or more UMLS vocabs to use
    
    List of available vocabularies and abbreviations: 
        https://www.nlm.nih.gov/research/umls/sourcereleasedocs/index.html

    UMLS search parameters: 
        https://documentation.uts.nlm.nih.gov/rest/search/
        
    UMLS search endpoints:
        https://documentation.uts.nlm.nih.gov/rest/home.html

"""

# Imports ####################################################################
import requests
import json
import pandas as pd
from lxml.html import fromstring

# Personal API key
import umls_api_key


# Globals ####################################################################

uri="https://utslogin.nlm.nih.gov"
auth_endpoint = "/cas/v1/api-key"


# Class defs #################################################################

class Authentication():
    '''
    https://documentation.uts.nlm.nih.gov/rest/authentication.html
    '''
    
    def __init__(self, apikey):
        self.apikey=apikey
        self.service = "http://umlsks.nlm.nih.gov"


    def get_tgt(self):
        '''
        Request a Ticket Granting Ticket (TGT)
        Valid for 8 hours
        '''
        params = {'apikey': self.apikey}
        h = {"Content-type": "application/x-www-form-urlencoded", 
             "Accept": "text/plain", 
             "User-Agent": "python" }
        r = requests.post(uri+auth_endpoint,data=params,headers=h)
        response = fromstring(r.text)
        tgt = response.xpath('//form/@action')[0]
        return tgt
    

    def get_st(self, tgt):
        '''
        Request a Service Ticket
        Expires after single use, or 5 mins after generation if not used.
        '''
        params = {'service': self.service}
        h = {"Content-type": "application/x-www-form-urlencoded", 
             "Accept": "text/plain", 
             "User-Agent":"python" }
        r = requests.post(tgt,data=params,headers=h)
        st = r.text
        return st
        
    
    
class searchUMLS():
    
    def __init__(self, apikey):
        self.apikey = apikey
        self.auth = Authentication(apikey)

    def search_term(self, search_str, vocab=None, id_type='concept', num_results=1e6, as_df=True):
        """
        Args
        ----------
        search_str : str
            Search string
        vocab : str, optional
            Specify vocabs as a comma sep string. 
            The default is None; will return results for all UMLS vocabs
        id_type : str, optional
            . The default is 'concept'. See UMLS search docs for more info.
        num_results : int or float, optional
            Number of results to return. The default is 1e6.

        Returns
        -------
        results : list
            returns a list of json dicts.
        """
        
        n = int(num_results)
       
        results = []
        tgt = self.auth.get_tgt()
        uri = "https://uts-ws.nlm.nih.gov/rest/"
        content_endpoint = "search/current"
        page = 0
        
        
        while True:
            
            service_ticket = self.auth.get_st(tgt) # New st needed per page
            page += 1
            query = {'string':search_str,
                     'ticket':service_ticket, 
                     'pageNumber':page,
                     'sabs': vocab,
                     'returnIdType':id_type}
        
            r = requests.get(uri+content_endpoint, params=query)
            r.encoding = 'utf-8'
            items = json.loads(r.text)
           
            json_data = items['result']
            if isinstance(json_data, dict):
                
                if json_data["results"][0]["ui"] == "NONE":
                    break
                else:
                    results.extend(json_data['results'])
                    res_count = len(results)
                
                if res_count >= n:
                    break
            
            else:
                break

        results = results[0:n]
        
        if as_df:
            results = self.get_df(results)
            
        return results
    
    
    def search_cui(self, cui_lst, as_df=True):
        
        '''
        https://www.nlm.nih.gov/research/umls/META3_current_semantic_types.html
        '''
        
        results = []
        for cui in cui_lst:
            print(cui)
        
            tgt = self.auth.get_tgt()
            uri = "https://uts-ws.nlm.nih.gov/rest/"
            content_endpoint = "content/current"
        
        #print
        #for cui in cui_list:
            
            service_ticket = self.auth.get_st(tgt) # New st needed per page
            query = {'ticket':service_ticket}
            
     
            r = requests.get(uri+content_endpoint+"/CUI/"+cui, params=query)
            r.encoding = 'utf-8'
            items = json.loads(r.text)
            
            if 'error' in items:
                print(f"No results found for {cui}")
                continue
            
            else:
                results.append(items['result'])
                
        if as_df:
            results = self.get_df(results)
            
        return results
            
   
    
    def get_df(self, json_data):
        '''
        Converts list of json dicts to pandas df
        '''
        df = pd.DataFrame(json_data)
        
        # Expand nested semantic types dict
        if 'semanticTypes' in df.columns:
            df[['semantic_type', 'TUI']] = df['semanticTypes'].str[0].apply(pd.Series)
            df.drop('semanticTypes', inplace=True, axis=1)
        else:
            pass
            
        return df
    

    
    
  
#%%

if __name__ == "__main__":
    
    
    # Text search #############################################################
  
    # Specify a search term or code
    search_term = 'kidney stone'
    
    # Load personal API key from file (or copy/paste etc.)
    apikey = umls_api_key.key()

    # Instantiate client
    client = searchUMLS(apikey)
    
    # Get dataframe of search results (include MeSH terms only)
    df1 = client.search_term(search_term, vocab='MSH, MTH', num_results=200)
    display(df1)
    
    # Get dataframe of search results (include all terms)
    df2 = client.search_term(search_term)
    display(df2)
    
    
    # Concept search (including semantic type) ################################
    
    # Specify a list of concept IDs
    concept_ids = ['C0009044','C2097260', 'x']
    
    # Ger dataframe of all valid UMLS concepts
    df3 = client.search_cui(concept_ids)
    display(df3)
    
    
    # Get CUIs from previous term search
    concept_ids = list(df2['ui'].values)
    df4 = client.search_cui(concept_ids)
    display(df4)
       
    print(df4.head(1).T)
    
    # Merge the term and cui search results; dump to csv
    df5 = df4.merge(df2, on='ui')
    df5 = df5[['ui', 'name_x', 'semantic_type', 'rootSource']].copy()
    df5.columns = ['cui', 'name', 'semantic_type', 'vocab']
    df5.to_csv(f'umls_{search_term}.csv')
    
    