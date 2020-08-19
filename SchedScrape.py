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
        self.StartMJD = None
        self.EndMJD = None

        self.CSVLines = None
        self.WikiLines = None

        self.TranslateSess()
        self.ConvertObsTimes()
        # Not by default: self.GetWikiLines()
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
        #self.WikiLines = np.array(self.WikiLines)[SortInds]

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
        for pid, rsid in zip(self.ProjID, self.RawSessID):

            if "2780" in pid:
                self.SessID.append(aoDictP2780[rsid])
            elif "2945" in pid:
                self.SessID.append(aoDictP2945[rsid])
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

    def ConvertObsTimes(self):
        """
        Convert session start/end times -> UTC, MJD.
        """

        UTC = pytz.utc

        self.StartUTC = np.array([sl.astimezone(UTC) for sl in self.StartLoc])
        self.EndUTC = np.array([el.astimezone(UTC) for el in self.EndLoc])

        self.StartMJD = np.array([Time(ut).mjd for ut in self.StartUTC])
        self.EndMJD = np.array([Time(ut).mjd for ut in self.EndUTC])

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

    def PrintWikiLines(self, all=False, reverse=True):
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

    def PrintInfoDefault(self, all=False, reverse=True):
        """
        Prints relevant scheduling info as CSV.
            [ProjID], [SessID], [Start MJD], [StartLoc], [EndLoc]
        By default, only future sessions are printed (all=False) with the latest date
        on top (reverse=True).
        """
        # if not all:
        #    # Find UTC start times after Time.now()
        #    TimeNow = Time.now()
        #    FutureInds = np.where(self.StartUTC > TimeNow)
        #    OutLines = self.WikiLines[FutureInds]

        for i in range(self.nRows):
            print(
                "%s, %s, %.2f, %s, %s"
                % (
                    self.ProjID[i],
                    self.SessID[i],
                    self.StartMJD[i],
                    self.StartLoc[i],
                    self.EndLoc[i],
                )
            )


def get_session(id):
    sess_str = obscode_dict[str(int(id) % 11)]
    return sess_str


def ValidProjID(ProjID):
    """
    Check input project ID, determine validity, raise exception if necessary.
    Until default behavior for www.naic.edu/~arun/cgi-bin/schedrawd.cgi is
    updated, 'validity' of input ProjID will rely on whether or not it's supported.

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


def ScrapeSchedGBO(project, year):

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
        names=("Proj", "Sess", "StartLocal", "EndLocal", "DayWrap"),
    )

    # Sort table, eventually this tag shouldn't be needed. Cludge fix for now.
    SortTag = np.array([int(datetime.strftime(st, "%Y%m%d%H%M")) for st in StartList])
    SchedTable["SortTag"] = SortTag
    SchedTable.sort(keys=["SortTag"])

    return SchedTable


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

    SchedTable["StartLocal"] = StartAO
    SchedTable["EndLocal"] = EndAO

    SortTag = np.array([int(datetime.strftime(st, "%Y%m%d%H%M")) for st in StartAO])
    SchedTable["SortTag"] = SortTag

    # Sort the table by SortTag, ...do I still need this column?
    SchedTable.sort(keys=["SortTag"])

    SchedTable["DayWrap"] = np.zeros(len(SchedTable))
    RemoveRows = []
    for r in range(len(SchedTable) - 1):

        # Merge sessions continuing over a day boundary
        if (SchedTable["EndLocal"][r] == SchedTable["StartLocal"][r + 1]) and (
            SchedTable["Sess"][r] == SchedTable["Sess"][r + 1]
        ):
            SchedTable["EndLocal"][r] = SchedTable["EndLocal"][r + 1]
            SchedTable["DayWrap"][r] = 1
            RemoveRows.append(r + 1)

        # Merge adjacent P2945 sessions
        elif (SchedTable["EndLocal"][r] == SchedTable["StartLocal"][r + 1]) and (
            SchedTable["Proj"][r] == SchedTable["Proj"][r + 1] == "P2945"
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

        if ValidProjID(p):
            Telescope = DetermineTelescope(p)

            if Telescope == "GBT":
                SchedTables.append(ScrapeSchedGBO(p, args.year))
            elif Telescope == "AO":
                SchedTables.append(ScrapeSchedAO(p, args.year))
        else:
            print("Invalid project: %s" % (p))
            print(
                "Try fiddling with case or -/_; automatic fixes for these coming soon..."
            )
            sys.exit()

    FullSched = vstack(SchedTables)
    x = Sched(FullSched)

    if args.all:
        x.PrintInfoDefault()
    else:
        x.PrintInfoDefault()


if __name__ == "__main__":
    main()
