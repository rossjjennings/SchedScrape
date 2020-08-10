#!/usr/bin/env python

import os
import sys
import numpy as np
import requests
from bs4 import BeautifulSoup
from astropy.table import vstack, Table
from astropy.io import ascii
from astropy.time import Time
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
    """Observatory schedule class

    This class contains pertinent observatory schedule info,
    such as project/session IDs, start/end times, as well as
    useful methods for manipulating this info. For now, this
    class is AO project-specific (e.g. P2780/P2945).  

    Contents of schedule are stored in various arrays/lists.

    Parameters
    ----------
    table: astropy.table.Table
        Pertinent scheduling information; assumed columns are...
            SortTag (YYYYMMDDHHMM start time integers for easy sorting),
            Proj (project ID; e.g. P2780), 
            Sess (raw session ID; e.g. (a)),
            StartLocal (observatory's local start time),
            EndLocal (local end time),
            DayWrap (boolean marker for sessions that cross a day boundary).
    """

    def __init__(self, table):

        self.nRows = len(table)
        self.Tags = table["SortTag"]
        self.ProjID = table["Proj"]
        self.RawSessID = table["Sess"]
        self.StartLoc = table["StartLocal"]
        self.EndLoc = table["EndLocal"]
        self.Wraps = table["DayWrap"]
        self.SessID = None
        self.StartUTC = None
        self.EndUTC = None
        self.WikiLines = None

        self.TranslateSess()
        self.ObsTimesUTC()
        self.GetWikiLines()
        self.SortArrays()

    def SortArrays(self):
        """
        By default sort by Tags. Maybe add more functionality later.
        THERE MUST BE A BETTER WAY TO DO THIS OMG.
        """

        SortInds = np.argsort(self.Tags)

        self.Tags = self.Tags[SortInds]
        self.ProjID = self.ProjID[SortInds]
        self.RawSessID = self.RawSessID[SortInds]
        self.StartLoc = self.StartLoc[SortInds]
        self.EndLoc = self.EndLoc[SortInds]
        self.Wraps = self.Wraps[SortInds]
        self.SessID = np.array(self.SessID)[SortInds]
        self.StartUTC = self.StartUTC[SortInds]
        self.EndUTC = self.EndUTC[SortInds]
        self.WikiLines = np.array(self.WikiLines)[SortInds]

    # Not sure this is necessary...
    def GetObservatories(self):
        """
        Use project codes to determine corresponding observatory.
        """
        pass

    def TranslateSess(self):
        """
        Converts raw session IDs (observatory convention) to NANOGrav session IDs 
        (e.g. (a) -> A) using project-specific dictionaries.
        """

        self.SessID = []
        for pid,rsid in zip(self.ProjID,self.RawSessID):
        
            if "2780" in pid:
                self.SessID.append(aoDictP2780[rsid])
            elif "2945" in pid:
                self.SessID.append(aoDictP2945[rsid])
            else:
                try:
                    self.SessID.append(aoDictP2780[rsid])
                except KeyError:
                    print('Could not match session key, %s.' % (rsid))
                except:
                    print('Something else happened.') 

    def ObsTimesUTC(self):
        """
        Convert session start/end times -> UTC.
        """

        UTC = pytz.utc

        self.StartUTC = np.array([sl.astimezone(UTC) for sl in self.StartLoc])
        self.EndUTC = np.array([el.astimezone(UTC) for el in self.EndLoc])

    def GetWikiLines(self):
        """For example:
        2020 Jul 12: 21:15 - Jul 13: 06:30: P2780 (Session C): <br>
        2020 Jul 12: 04:30 - 06:30: P2945 (2317,0030): <br>
        2020 Jul 12: 02:00 - 03:00: P2945 (2043): <br>
        2020 Jul 11: 08:45 - 15:30: P2780 (Session D): <br>
        """

        self.WikiLines = []
        for r, (st, et) in enumerate(zip(self.StartLoc, self.EndLoc)):
            WikiStart = datetime.strftime(st, "%Y %b %d: %H:%M")

            # Check for session spanning multiple columns (days)
            # if datetime.strftime(st,'%d') == datetime.strftime(et,'%d'):
            if not self.Wraps[r]:
                WikiEnd = datetime.strftime(et, "%H:%M")
            else:
                WikiEnd = datetime.strftime(et, "%b %d: %H:%M")

            WikiLine = "%s - %s: %s (%s): <br>" % (
                WikiStart,
                WikiEnd,
                self.ProjID[r],
                self.SessID[r],
            )
            self.WikiLines.append(WikiLine)

    def PrintWikiLines(self,all=False,reverse=True):
        """
        Prints schedule lines to copy directly to the wiki. By default, only future
        sessions are printed (all=False) with the latest date on top (reverse=True).
        """

        if not all:
            # Find UTC start times after Time.now()
            TimeNow = Time.now() 
            FutureInds = np.where(self.StartUTC > TimeNow)
            OutLines = self.WikiLines[FutureInds]
            
        else:
            OutLines = self.WikiLines

        if reverse:
            [print(wl) for wl in np.flip(OutLines)]
        else:
            [print(wl) for wl in OutLines]

    def PrintHenriLines(self):
        """
        Prints schedule lines to copy directly to the wiki. By default, all sessions
        are printed with the latest date on top (reverse=True).
        """
        OutMJD = ["(MJD %.2f)" % (Time(ut).mjd) for ut in np.flip(self.StartUTC)]
        [print(om) for om in OutMJD]

def ValidProjID(ProjID):
    """
    Check input project ID, determine validity, raise exception if necessary.
    Until default behavior for www.naic.edu/~arun/cgi-bin/schedrawd.cgi is
    updated, 'validity' of input ProjID will rely on whether or not it's supported.
    """
    SupportedProjIDs = np.array(
        [
            'P2780',
            'P2945',
            'P2030',
            'P3436',
            'GBT18B_226',
            'GBT20A_998',
            'GBT20B_307',
            'GBT20B_997'
        ]
    )

    return (ProjID in SupportedProjIDs)

def DetermineTelescope(ProjID):
    """
    Determine telescope associated with input project ID.
    """
    if 'GBT' in ProjID:
        telescope = 'GBT'
    elif ('P' in ProjID) or ('X' in ProjID):
        telescope = 'AO'
    else:
        print('No telescope associated with project: %s' % (ProjID))
        sys.exit()

    return telescope

def ScrapeSchedAO(project, year):

    proj = project.lower()
    PROJ = project.upper()
    yr = year[-2:]

    # For some reason, if 'proj' is nothing/anything default page is P2780 in 2020.
    # Should take this up with Arun.
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

    SortTag = np.array([int(datetime.strftime(st,'%Y%m%d%H%M')) for st in StartAO])
    SchedTable['SortTag'] = SortTag

    # Sort the table by SortTag, then remove this column 
    SchedTable.sort(keys=['SortTag'])

    SchedTable['DayWrap'] = np.zeros(len(SchedTable))
    RemoveRows = []
    for r in range(len(SchedTable)-1):
        
        # Merge sessions continuing over a day boundary
        if (
            (SchedTable['EndLocal'][r] == SchedTable['StartLocal'][r+1]) and
            (SchedTable['Sess'][r] == SchedTable['Sess'][r+1])
        ):
            SchedTable['EndLocal'][r] = SchedTable['EndLocal'][r+1]
            SchedTable['DayWrap'][r] = 1
            RemoveRows.append(r+1)
        
        # Merge adjacent P2945 sessions
        elif (
            (SchedTable['EndLocal'][r] == SchedTable['StartLocal'][r+1]) and
            (SchedTable['Proj'][r] == SchedTable['Proj'][r+1] == 'P2945')
        ):
            pass

        else:
            pass

    SchedTable.remove_rows(RemoveRows)

    return SchedTable


def main():

    parser = argparse.ArgumentParser(
        description="GBO/AO Schedule Scraper",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--projects",
        "-p",
        type=str,
        nargs="+",
        help="Project code(s)",
    )
    parser.add_argument(
        "--year",
        "-y",
        type=str,
        nargs="?",
        default=datetime.now(pytz.utc).strftime("%Y"),
        help="Year",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Print all sessions in the chosen year."
    )
    parser.add_argument(
        "--reverse",
        "-r",
        action="store_true",
        help="Print sessions in reverse order."
    )
    parser.add_argument(
        "--henriradovan",
        "-hr",
        action="store_true",
        help="Print lines with MJDs."
    )

    args = parser.parse_args()
    projects = [str(item) for item in args.projects[0].split(',')]
    
    SchedTables = []
    for p in projects:

        if ValidProjID(p):
            Telescope = DetermineTelescope(p)

            if Telescope == 'GBT':
                SchedTables.append(ScrapeSchedGBT(p, args.year))
            elif Telescope == 'AO':
                SchedTables.append(ScrapeSchedAO(p, args.year))
        else:
            print('Invalid project: %s' % (p))
            sys.exit()

    FullSched = vstack(SchedTables)
    x = Sched(FullSched)

    if args.all:
        if not args.henriradovan:
            x.PrintWikiLines(all=True)
        else:
            x.PrintHenriLines()
    else:
        if not args.henriradovan:
            x.PrintWikiLines()
        else:
            x.PrintHenriLines()

if __name__ == "__main__":
    main()
