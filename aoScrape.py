import os
import sys
import numpy as np
#from aosched_functions import get_month
#from astropy.time import Time
import requests
from bs4 import BeautifulSoup
#import re
from astropy.table import Table
from astropy.io import ascii
import logging
import pytz
from datetime import datetime,timedelta

#date_line_pattern = re.compile(r"(?P<month>[a-zA-Z]{3})_(?P<day>\d{2})_(?P<year>\d{2})") 

class obs_block:
    """AO Schedule class

    This is a class for representing ~15-day blocks of time on
    the Arecibo Observatory schedule and contains corresponding
    project-specific sessions falling into those blocks of time.

    Contents of schedule are stored in an `astropy.table.Table`.

    Parameters
    ----------
    datestr: str
        Date string of the form 'Mar_11_20' marking the start of
        a 15-day observation block.
    """

    def __init__(
        self,
        datestr
    ):

        # UTC/AO tzinfo
        utc = pytz.utc
        ao_tz = pytz.timezone("America/Puerto_Rico")
        self.block_start_aot = ao_tz.localize(datetime.strptime(datestr,'%b_%d_%y'))
        self.block_start_utc = self.block_start_aot.astimezone(utc)

        # Contain scheduled sessions in astropy table
        self.sess_table = Table()
        self.sessions_fixed = False

    def compose(self):
        fix_colnames(self.sess_table)
        self.projid = self.sess_table['proj'][0]
        if self.projid == 'P2780':
            self.fix_p2780_sess()
        self.obs_times_arecibo()
        self.get_wiki_lines()        

    def fix_p2780_sess(self):

        if not self.sessions_fixed:
            for i,id in enumerate(self.sess_table['sess']):
                fixed = id.upper().replace('(','').replace(')','')
                self.sess_table['sess'][i] = fixed
            self.sessions_fixed = True
        else:
            pass

    def obs_times_arecibo(self):
        self.arecibo_start_times = [self.block_start_aot + 
            timedelta(days=1.0*c,minutes=15.0*r)
            for c,r in zip(self.sess_table['begcol'],self.sess_table['begrow'])]  
        self.arecibo_end_times = [self.block_start_aot + 
            timedelta(days=1.0*c,minutes=15.0*r)
            for c,r in zip(self.sess_table['endcol'],self.sess_table['endrow'])]

    # Look for consecutive sessions with the same id and merge them
    def merge_sessions(self):
        pass

    # Print lines that can be copied directly to the wiki schedule
    # Maybe it should be a separate function if I'm going to intersperse P2780/P2945
    """For example:
    2020 Jul 12: 21:15 - Jul 13: 06:30: P2780 (Session C): <br> 
    2020 Jul 12: 04:30 - 06:30: P2945 (2317,0030): <br> 
    2020 Jul 12: 02:00 - 03:00: P2945 (2043): <br> 
    2020 Jul 11: 08:45 - 15:30: P2780 (Session D): <br> 
    """
    def get_wiki_lines(self):
        self.wiki_lines = []
        for r,(ast,aet) in enumerate(zip(self.arecibo_start_times,
                             self.arecibo_end_times)):
            wiki_start = datetime.strftime(ast,'%Y %b %d: %H:%M')

            # Check for session spanning multiple columns (days)
            if self.sess_table['begcol'][r] == self.sess_table['endcol'][r]:
                wiki_end = datetime.strftime(aet,'%H:%M')
            else:
                wiki_end = datetime.strftime(aet,'%b %d: %H:%M')

            wiki_line = '%s - %s: %s (Session %s): <br>' % (
                wiki_start,wiki_end,self.sess_table['proj'][r],
                self.sess_table['sess'][r]
                )
            self.wiki_lines.append(wiki_line)

    def print_wiki_lines(self):
        for wl in self.wiki_lines:
            print(wl)


def fix_colnames(table):
    table.rename_column('col1','proj')
    table.rename_column('col5','sess')
    table.rename_column('col8','startlst')
    table.rename_column('col9','endlst')
    table.rename_column('col11','timesys')
    table.rename_column('col12','begcol')
    table.rename_column('col13','endcol')
    table.rename_column('col14','begrow')
    table.rename_column('col15','endrow')
    table.rename_column('col16','hours')

def scrape_ao_sched(project,year,log_level=logging.INFO):

    proj = project.lower()
    PROJ = project.upper()
    yr = year[-2:]

    # create logger with 'ao_obs_parser'
    logging.basicConfig(handlers=[logging.StreamHandler(sys.stdout)])
    logger = logging.getLogger("ao_obs_parser")
    logger.setLevel(log_level)

    #link = 'http://www.naic.edu/~arun/cgi-bin/schedrawd.cgi?year=%s&proj=%s' % (yr,proj)
    link = 'http://www.naic.edu/~arun/cgi-bin/schedraw.cgi?year=%s&proj=%s' % (yr,proj)
    page = requests.get(link)
    soup = BeautifulSoup(page.content,'html.parser')

    logger.info('Parsing %s...' % (link))
    souptextlines = soup.get_text().split('\n')

    ob_instantiated = False
    obsblocks = []
    logger.debug("Parsing souptextlines")
    #"""
    for lnum,l in enumerate(souptextlines):
        if not l:
            logger.debug("empty line: %s" % (lnum))
            pass
        #elif date_line_pattern.match(l):
        elif '_' in l:
            logger.debug("Found date line: %s" % (lnum))
            if not ob_instantiated:
                logger.debug("...instantiating obs_block")
                ob = obs_block(l.strip())
                ob_instantiated = True
            else:
                logger.debug("...finishing & appending; instantiating next")
                if ob.sess_table:
                    ob.compose()
                    obsblocks.append(ob)
                else:
                    logger.info(" Ignoring empty block ")
                ob = obs_block(l.strip())
        elif l.startswith(PROJ):
            logger.debug("Found project line: %s" % (lnum))
            table_row = ascii.read([l],delimiter='|')[
                'col1','col5','col8','col9','col11','col12',
                'col13','col14','col15','col16'
                ]
            if not ob.sess_table:
                current_sess_dtype = table_row['col5'].dtype
                ob.sess_table = table_row
            else:
                ob.sess_table.add_row(table_row[0]) 
        else:
            logger.warning("Unrecognized line: %s --> %s" % (lnum,l))
    #"""


    ob.compose()
    obsblocks.append(ob)
    return obsblocks


if __name__ == "__main__":

    x = scrape_ao_sched('P2945','2020',logging.INFO)
