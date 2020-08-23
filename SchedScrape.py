#!/usr/bin/env python

import sys
import numpy as np
import requests
from bs4 import BeautifulSoup
from astropy.table import vstack, Table
from astropy.io import ascii
from astropy.time import Time, TimeDelta
from astropy import units as u
from astropy import log
import pytz
from datetime import datetime, timedelta
import argparse

aoDictP2780 = {
    "(a)": "Session A",
    "(b)": "Session B",
    "(c)": "Session C",
    "(d)": "Session D",
}

aoDictP2945 = {
    "(a)": "0030",
    "(b)": "1640",
    "(c)": "1713",
    "(d)": "2043",
    "(e)": "2317",
    "(b)+(c)": "1640,1713",
    "(e)+(a)": "2317,0030",
}

obscode_dict = {
    "0": "F-1400",
    "1": "A-1400",
    "2": "A-820",
    "3": "B-1400",
    "4": "B-820",
    "5": "C-1400",
    "6": "C-820",
    "7": "D-1400",
    "8": "D-820",
    "9": "E-1400",
    "10": "E-820",
}

def GetSession(sid):
    sess_str = obscode_dict[str(int(sid) % 11)]
    return SessStr

def FixProj(pid):
    """
    Make code more robust to handling ProjIDs with capitalization or delimiter issues.
    """
    TempPid = pid
    pid = pid.upper()
    if pid != TempPid:
        log.warning('Capitalizing ProjID...')

    if '_' in pid: 
        pid = pid.replace('_','-')
        log.warning('Replacing underscore with hyphen...')

    return pid


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

        self.Table = table
        self.nRows = len(table)
        self.Tags = table["Tags"]
        self.ProjID = table["ProjID"]
        self.RawSessID = table["RawSessID"]
        self.StartLoc = table["StartLoc"]
        self.EndLoc = table["EndLoc"]
        self.Wraps = table["Wraps"]
        self.SessID = None
        self.StartUTC = None
        self.EndUTC = None
        self.StartMJD = None
        self.EndMJD = None
        self.Duration = None

        self.DefLines = None
        self.WikiLines = None
        self.GBNCCLines = None

        self.TranslateSess()
        self.ConvertObsTimes()
        # MERGE HERE!...

        # Sort merged Sched.Table rows
        self.Table.sort(keys=['StartMJD'])

    # Not sure this is necessary...
    def GetObservatories(self):
        """
        Use project codes to determine corresponding observatory.
        """
        pass

    def MergeAdjacent(self):
        """
        Merge sched lines that are obviously consecutive, same session.
        """
        pass

    def TranslateSess(self):
        """
        Converts raw session IDs (observatory convention) to NANOGrav session IDs 
        (e.g. (a) -> A) using project-specific dictionaries.
        """

        self.SessID = []
        for pid, rsid in zip(self.Table['ProjID'],self.Table['RawSessID']):

            if "2780" in pid:
                self.SessID.append(aoDictP2780[rsid])
            elif "2945" in pid:
                self.SessID.append(aoDictP2945[rsid])
            elif "20B-307" in pid:
                pass
            else:
                try:
                    self.SessID.append(aoDictP2780[rsid])
                except KeyError:
                    print(
                        "Could not match session key, %s. Adding empty string..."
                        % (rsid)
                    )
                    self.SessID.append("")
                except:
                    print("Blurgh. Something else happened.")

        self.SessID = np.array(self.SessID)
        self.Table['SessID'] = self.SessID

    def ConvertObsTimes(self):
        """
        Convert session start/end times -> UTC, MJD.
        """

        UTC = pytz.utc

        # UTC
        self.StartUTC = np.array([sl.astimezone(UTC) for sl in self.StartLoc])
        self.Table['StartUTC'] = self.StartUTC
        self.EndUTC = np.array([el.astimezone(UTC) for el in self.EndLoc])
        self.Table['EndUTC'] = self.EndUTC

        # MJD
        self.StartMJD = np.array([Time(ut).mjd for ut in self.StartUTC])
        self.Table['StartMJD'] = self.StartMJD
        self.EndMJD = np.array([Time(ut).mjd for ut in self.EndUTC])
        self.Table['EndMJD'] = self.EndMJD

        # LST?
        # Later...

        # Calculate durations
        dt = self.EndUTC - self.StartUTC
        self.Duration = np.array([TimeDelta(t).to(u.hour).value for t in dt])
        self.Table['Duration'] = self.Duration

    def GetWikiLines(self):
        """For example:
        2020 Jul 12: 21:15 - Jul 13: 06:30: P2780 (Session C): <br>
        2020 Jul 12: 04:30 - 06:30: P2945 (2317,0030): <br>
        2020 Jul 12: 02:00 - 03:00: P2945 (2043): <br>
        2020 Jul 11: 08:45 - 15:30: P2780 (Session D): <br>
        """

        self.WikiLines = []
        for i, (st, et) in enumerate(zip(self.Table['StartLoc'],self.Table['EndLoc'])):
            WikiStart = datetime.strftime(st, "%Y %b %d: %H:%M")

            # Check for session spanning multiple columns (days)
            # if datetime.strftime(st,'%d') == datetime.strftime(et,'%d'):
            # FIX! Do not need "Wraps" info for this.
            if not self.Table['Wraps'][i]:
                WikiEnd = datetime.strftime(et, "%H:%M")
            else:
                WikiEnd = datetime.strftime(et, "%b %d: %H:%M")

            WikiLine = "%s - %s: %s (%s): <br>" % (
                WikiStart,
                WikiEnd,
                self.Table['ProjID'][i],
                self.Table['SessID'][i],
            )
            self.WikiLines.append(WikiLine)

        self.WikiLines = np.array(self.WikiLines)
        self.Table['OutText'] = self.WikiLines

    def GetDefLines(self):
        """For example:
        P2945 | 1713 | 59050.05 | 2020-07-19 21:15:00-04:00 | 2020-07-19 22:15:00-04:00
        P2945 | 2043 | 59052.21 | 2020-07-22 01:00:00-04:00 | 2020-07-22 02:00:00-04:00
        P2945 | 2317,0030 | 59056.29 | 2020-07-26 03:00:00-04:00 | 2020-07-26 04:45:00-04:00
        P2945 | 1640 | 59056.98 | 2020-07-26 19:30:00-04:00 | 2020-07-26 20:30:00-04:00
        """

        self.DefLines = []
        for i in range(self.nRows):
            DefLine = "%s | %s | %.2f | %s | %s" % (
                self.Table['ProjID'][i],
                self.Table['SessID'][i],
                self.Table['StartMJD'][i],
                self.Table['StartLoc'][i],
                self.Table['EndLoc'][i],
            )
            self.DefLines.append(DefLine)

        self.DefLines = np.array(self.DefLines)
        self.Table['OutText'] = self.DefLines

    def GetGBNCCLines(self):
        """For example:
        2020 Aug 23: 15:15 (4.00h) -- ??
        2020 Aug 23: 22:15 (1.00h) -- ??
        2020 Aug 23: 23:15 (4.00h) -- ??
        2020 Aug 24: 13:00 (2.00h) -- ??
        """

        # Should re-write these as list comprehensions
        self.GBNCCLines = []
        for i in range(self.nRows):
            GBNCCLine = "%s (%.2fh) -- ??" % (
                datetime.strftime(self.Table['StartLoc'][i], "%Y %b %d: %H:%M"),
                self.Table['Duration'][i],
            )
            self.GBNCCLines.append(GBNCCLine)

        self.GBNCCLines = np.array(self.GBNCCLines)
        self.Table['OutText'] = self.GBNCCLines

    def PrintText(self, LineType, all=False, reverse=True):
        """
        Print desired sched lines with desired formatting/sorting applied.

        default, e.g.:
            P2945 | 2317,0030 | 59056.29 | 2020-07-26 03:00:00-04:00 | 2020-07-26 04:45:00-04:00

        wiki, e.g.:
            2020 Jul 26: 03:00 - 04:45: P2945 (2317,0030): <br>

        gbncc, e.g.:
            2020 Aug 23: 23:15 (4.00h) -- ?? 
        """

        if LineType == 'default':
            self.GetDefLines()
        elif LineType == 'wiki':
            self.GetWikiLines()
        elif LineType == 'gbncc':
            self.GetGBNCCLines()
        else:
            log.error('LineType %s not recognized.' % (LineType))
            sys.exit()

        if not all:
            FutureInds = np.where(self.Table['StartUTC'] > Time.now())
            OutLines = self.Table['OutText'][FutureInds]
        else:
            OutLines = self.Table['OutText'] 

        if reverse:
            [print(cl) for cl in np.flip(OutLines)]
        else:
            [print(wl) for wl in OutLines]


def ValidProjID(ProjID):
    """
    Check input project ID, determine validity, raise exception if necessary.
    List of supported projects now contained in SupportedProjIDs.list.
    """
    SupportedProjIDs = np.loadtxt("SupportedProjIDs.list", dtype="str")
    return ProjID in SupportedProjIDs


def DetermineTelescope(ProjID):
    """
    Determine telescope associated with input project ID.
    """
    if "GBT" in ProjID:
        telescope = "GBT"
    elif ("P" in ProjID) or ("X" in ProjID):
        telescope = "AO"
    else:
        print("No telescope associated with project: %s" % (ProjID))
        sys.exit()

    return telescope


def ScrapeGBO(project, year):
    """
    [docstring]
    """
    page = requests.get("https://dss.gb.nrao.edu/schedule/public")
    soup = BeautifulSoup(page.content, "html.parser")
    table = soup.findChildren("table")[1]

    # Calculate local AO start/end times from SchedTable
    GBO = pytz.timezone("US/Eastern")

    ProjList = []
    SessList = []
    StartList = []
    EndList = []
    WrapList = []
    for rr in table.findChildren("tr"):
        if not rr.a:
            date_str = rr.contents[1].text.split()[0]
        else:
            proj_str = rr.a["title"]

            if project in proj_str:
                wrap = 0
                proj_id = proj_str.split(" - ")[0].strip()
                sess_id = proj_str.split(" - ")[1].strip()

                obs_elems = rr.findChildren("td")
                time_window = obs_elems[0].text.strip()
                start_et_str = time_window.split(" - ")[0].strip()  # .replace('+','')
                end_et_str = time_window.split(" - ")[1].strip()  # .replace('+','')

                if "+" in end_et_str:
                    start = "%s %s" % (date_str, start_et_str.replace("+", ""))
                else:
                    if "+" in start_et_str:
                        end = "%s %s" % (date_str, end_et_str.replace("+", ""))
                        wrap = 1
                    else:
                        start = "%s %s" % (date_str, start_et_str)
                        end = "%s %s" % (date_str, end_et_str)

                    t0 = GBO.localize(datetime.strptime(start, "%Y-%m-%d %H:%M"))
                    t1 = GBO.localize(datetime.strptime(end, "%Y-%m-%d %H:%M"))
                    ProjList.append(proj_id)
                    SessList.append(sess_id)
                    StartList.append(t0)
                    EndList.append(t1)
                    WrapList.append(wrap)

    SchedTable = Table(
        [ProjList, SessList, StartList, EndList, WrapList],
        names=("ProjID", "RawSessID", "StartLoc", "EndLoc", "Wraps"),
    )

    # Sort table, eventually this tag shouldn't be needed. Cludge fix for now.
    SortTag = np.array([int(datetime.strftime(st, "%Y%m%d%H%M")) for st in StartList])
    SchedTable["Tags"] = SortTag
    SchedTable.sort(keys=["Tags"])

    return SchedTable


def ScrapeAO(project, year):
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
    SchedTable.rename_column("col2", "ProjID")
    SchedTable.rename_column("col6", "RawSessID")
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
        [AO.localize(datetime.strptime(ds, "%b_%d_%y")) for ds in SchedTable["DateStr"]]
    )
    StartAO = np.array(
        [
            bd + timedelta(days=1.0 * c, minutes=15.0 * r)
            for bd, c, r in zip(BlockDates, SchedTable["BegCol"], SchedTable["BegRow"])
        ]
    )
    EndAO = np.array(
        [
            bd + timedelta(days=1.0 * c, minutes=15.0 * r)
            for bd, c, r in zip(BlockDates, SchedTable["EndCol"], SchedTable["EndRow"])
        ]
    )

    # Clean up the table to remove extraneous info, add datetimes
    SchedTable.remove_columns(
        [
            "DateStr",
            "StartLST",
            "EndLST",
            "TimeSys",
            "BegCol",
            "EndCol",
            "BegRow",
            "EndRow",
            "Hours",
        ]
    )

    SchedTable["StartLoc"] = StartAO
    SchedTable["EndLoc"] = EndAO

    SortTag = np.array([int(datetime.strftime(st, "%Y%m%d%H%M")) for st in StartAO])
    SchedTable["Tags"] = SortTag

    # Sort the table by SortTag, ...do I still need this column?
    SchedTable.sort(keys=["Tags"])

    SchedTable["Wraps"] = np.zeros(len(SchedTable))
    RemoveRows = []
    for r in range(len(SchedTable) - 1):

        # Merge sessions continuing over a day boundary
        if (SchedTable["EndLoc"][r] == SchedTable["StartLoc"][r + 1]) and (
            SchedTable["RawSessID"][r] == SchedTable["RawSessID"][r + 1]
        ):
            SchedTable["EndLoc"][r] = SchedTable["EndLoc"][r + 1]
            SchedTable["Wraps"][r] = 1
            RemoveRows.append(r + 1)

        # Merge adjacent P2945 sessions
        elif (SchedTable["EndLoc"][r] == SchedTable["StartLoc"][r + 1]) and (
            SchedTable["ProjID"][r] == SchedTable["ProjID"][r + 1] == "P2945"
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
        "--projects", "-p", type=str, nargs="+", required=True, help="Project code(s)",
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
        help="Print all sessions in the chosen year.",
    )
    parser.add_argument(
        "--reverse", "-r", action="store_true", help="Print sessions in reverse order."
    )
    parser.add_argument(
        "--printformat",
        "-pf",
        choices=["wiki", "none", "gbncc", "default"],
        nargs="?",
        default="default",
        help="Format of schedule info printed.",
    )

    # To print usage if no arguments are provided.
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit()

    args = parser.parse_args()
    projects = [str(item) for item in args.projects[0].split(",")]

    SchedTables = []
    for p in projects:

        p = FixProj(p)
        if ValidProjID(p):
            Telescope = DetermineTelescope(p)

            if Telescope == "GBT":
                SchedTables.append(ScrapeGBO(p, args.year))
            elif Telescope == "AO":
                SchedTables.append(ScrapeAO(p, args.year))
        else:
            print("Invalid project: %s" % (p))
            print(
                "Try fiddling with case or -/_; automatic fixes for these coming soon..."
            )
            sys.exit()

    FullSched = vstack(SchedTables)
    x = Sched(FullSched)
    x.PrintText(args.printformat,all=args.all,reverse=args.reverse)


if __name__ == "__main__":
    main()
