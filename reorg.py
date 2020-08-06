#!/usr/bin/env python

import os
import sys
import numpy as np
import requests
from bs4 import BeautifulSoup
from astropy.table import Table
from astropy.io import ascii
import pytz
from datetime import datetime, timedelta
import argparse

aoDictP2780 = {"(a)": "Session A", "(b)": "Session B", "(c)": "Session C", "(d)": "Session D"}

aoDictP2945 = {
    "(a)": "0030",
    "(b)": "1640",
    "(c)": "1713",
    "(d)": "2043",
    "(e)": "2317",
    "(b)+(c)": "1640,1713",
    "(e)+(a)": "2317,0030",
}


class Sched:
    """AO Schedule class

    This class contains a schedule of Arecibo Observatory
    sessions, as well as several useful methods for manipulating
    and accessing related scheduling information. For now, this
    class is project-specific (e.g. P2780/P2945).  

    Contents of schedule are stored in an `astropy.table.Table`.

    Parameters
    ----------
    table: astropy.table.Table
        Pertinent information for all the AO observations is stored
        here. More info coming soon...
    other?
    """

    def __init__(self, table):

        self.Table = table
        self.nRows = len(self.Table)

        self.ProjID = self.Table["Proj"][0]
        self.TranslateSess()
        self.ObsTimesTZ()
        self.GetWikiLines()

    def TranslateSess(self):
        """
        Translates self.Table['Sess'] to descriptive session identifiers
        according to aoDictP2780 and aoDictP2945.
        """

        if "2780" in self.ProjID:
            self.SessID = np.array([aoDictP2780[ss] for ss in self.Table["Sess"]])
        elif "2945" in self.ProjID:
            self.SessID = np.array([aoDictP2945[ss] for ss in self.Table["Sess"]])
        else:
            try:
                self.SessID = np.array([aoDictP2780[ss] for ss in self.Table["Sess"]])
            except KeyError:
                print('Could not match session key, %s.' % (ss))
            except:
                print('Something else happened.') 

    def ObsTimesTZ(self):
        """
        Calculate session start/end times by timezone, UTC and APR (America/Puerto Rico)
        """

        APR = pytz.timezone("America/Puerto_Rico")
        UTC = pytz.utc

        BlockDates = np.array(
            [
                APR.localize(datetime.strptime(ds, "%b_%d_%y"))
                for ds in self.Table["DateStr"]
            ]
        )
        self.StartAPR = np.array(
            [
                bd + timedelta(days=1.0 * c, minutes=15.0 * r)
                for bd, c, r in zip(
                    BlockDates, self.Table["BegCol"], self.Table["BegRow"]
                )
            ]
        )
        self.EndAPR = np.array(
            [
                bd + timedelta(days=1.0 * c, minutes=15.0 * r)
                for bd, c, r in zip(
                    BlockDates, self.Table["EndCol"], self.Table["EndRow"]
                )
            ]
        )

        self.StartUTC = np.array([sa.astimezone(UTC) for sa in self.StartAPR])
        self.EndUTC = np.array([ea.astimezone(UTC) for ea in self.EndAPR])

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

    def GetWikiLines(self):
        self.WikiLines = []
        for r, (ast, aet) in enumerate(zip(self.StartAPR, self.EndAPR)):
            WikiStart = datetime.strftime(ast, "%Y %b %d: %H:%M")

            # Check for session spanning multiple columns (days)
            if self.Table["BegCol"][r] == self.Table["EndCol"][r]:
                WikiEnd = datetime.strftime(aet, "%H:%M")
            else:
                WikiEnd = datetime.strftime(aet, "%b %d: %H:%M")

            WikiLine = "%s - %s: %s (%s): <br>" % (
                WikiStart,
                WikiEnd,
                self.ProjID,
                self.SessID[r],
            )
            self.WikiLines.append(WikiLine)

    def PrintWikiLines(self):
        for wl in self.WikiLines:
            print(wl)


def ScrapeSchedAO(project, year):

    proj = project.lower()
    PROJ = project.upper()
    yr = year[-2:]

    link = "http://www.naic.edu/~arun/cgi-bin/schedrawd.cgi?year=%s&proj=%s" % (
        yr,
        proj,
    )
    page = requests.get(link)
    soup = BeautifulSoup(page.content, "html.parser")

    SoupTextLines = soup.get_text().split("\n")

    SchedTable = ascii.read(SoupTextLines)[
        "col1",
        "col2",
        "col6",
        "col9",
        "col10",
        "col12",
        "col13",
        "col14",
        "col15",
        "col16",
        "col17",
    ]

    # Fix SchedTable column names (more descriptive)
    SchedTable.rename_column("col1", "DateStr")
    SchedTable.rename_column("col2", "Proj")
    SchedTable.rename_column("col6", "Sess")
    SchedTable.rename_column("col9", "StartLST")
    SchedTable.rename_column("col10", "EndLST")
    SchedTable.rename_column("col12", "TimeSys")
    SchedTable.rename_column("col13", "BegCol")
    SchedTable.rename_column("col14", "EndCol")
    SchedTable.rename_column("col15", "BegRow")
    SchedTable.rename_column("col16", "EndRow")
    SchedTable.rename_column("col17", "Hours")

    # Calculate local AO start/end times from SchedTable
    AO = pytz.timezone("America/Puerto_Rico")

    BlockDates = np.array(
        [
            AO.localize(datetime.strptime(ds, "%b_%d_%y"))
            for ds in SchedTable["DateStr"]
        ]
    )
    StartAO = np.array(
        [
            bd + timedelta(days=1.0 * c, minutes=15.0 * r)
            for bd, c, r in zip(
                BlockDates, SchedTable["BegCol"], SchedTable["BegRow"]
            )
        ]
    )
    EndAO = np.array(
        [
            bd + timedelta(days=1.0 * c, minutes=15.0 * r)
            for bd, c, r in zip(
                BlockDates, SchedTable["EndCol"], SchedTable["EndRow"]
            )
        ]
    )

    # Clean up the table to remove extraneous info, add datetimes
    SchedTable.remove_columns([
        'DateStr','StartLST','EndLST','TimeSys',
        'BegCol','EndCol','BegRow','EndRow','Hours'
    ])

    SchedTable['StartLocal'] = StartAO
    SchedTable['EndLocal'] = EndAO

    print(SchedTable)
    #so = Sched(SchedTable)
    #return so


def main():

    parser = argparse.ArgumentParser(
        description="Arecibo Schedule Scraper",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--projects",
        "-p",
        type=str,
        #choices=['P2780','P2945','P3436'],
        nargs="+",
        help="Project code(s), e.g. P2780,P2945",
    )
    parser.add_argument(
        "--year",
        "-y",
        type=str,
        nargs="?",
        default=datetime.now(pytz.utc).strftime("%Y"),
        help="Year",
    )

    args = parser.parse_args()
    projects = [str(item) for item in args.projects[0].split(',')]

    for p in projects:
        x = ScrapeSchedAO(p, args.year)
        #x.PrintWikiLines()


if __name__ == "__main__":
    main()
