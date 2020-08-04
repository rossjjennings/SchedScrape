#!/usr/bin/env python

import numpy as np
from astropy.time import Time
import requests
from bs4 import BeautifulSoup

obscode_dict = {'0':'F-1400',
                '1':'A-1400',
                '2':'A-820',
                '3':'B-1400',
                '4':'B-820',
                '5':'C-1400',
                '6':'C-820',
                '7':'D-1400',
                '8':'D-820',
                '9':'E-1400',
                '10':'E-820'}

def get_session(id):
    sess_str = obscode_dict[str(int(id)%11)]
    return sess_str

page = requests.get('https://dss.gb.nrao.edu/schedule/public')
soup = BeautifulSoup(page.content,'html.parser')
table = soup.findChildren('table')[1]

wiki_lines = []
for rr in table.findChildren('tr'): 
     if not rr.a: 
         date_str = rr.contents[1].text.split()[0]
     else:
         proj_str = rr.a['title'] 

         if ('GBT20B-997' in proj_str) or ('GBT20B-307' in proj_str):
             proj_id = proj_str.split(' - ')[0].strip()
             sess_id = proj_str.split(' - ')[1].strip()

             obs_elems = rr.findChildren('td')
             time_window = obs_elems[0].text.strip()
             start_et_str = time_window.split(' - ')[0].strip().replace('+','')
             end_et_str = time_window.split(' - ')[1].strip().replace('+','')

             # Obs over ET day boundary, get next end time...etc.              
             #if '+' in end_et_str:

             start = '%s %s' % (date_str,start_et_str)
             end = '%s %s' % (date_str,end_et_str)
             t0 = Time.strptime(start, '%Y-%m-%d %H:%M')
             t1 = Time.strptime(end, '%Y-%m-%d %H:%M')
             t0_out = t0.strftime('%Y %b %d %H:%M')
             t1_out = t1.strftime('%H:%M')
             str_out = '%s--%s %s: <br>' % (t0_out, t1_out, get_session(sess_id))
             wiki_lines.append(str_out)
             #print('%s %s %s (%s)' % (date_str,start_et_str,get_session(sess_id),proj_id))

for wl in reversed(wiki_lines):
    print(wl)
