# SchedScrape 

# Usage
No setup.py (yet), so I made an executable with `chmod +x SchedScrape.py`. Then,

```
./SchedScrape.py -h
usage: SchedScrape.py [-h] [--projects PROJECTS [PROJECTS ...]]
                      [--year [YEAR]] [--all] [--reverse] [--henriradovan]

GBO/AO Schedule Scraper

optional arguments:
  -h, --help            show this help message and exit
  --projects PROJECTS [PROJECTS ...], -p PROJECTS [PROJECTS ...]
                        Project code(s) (default: None)
  --year [YEAR], -y [YEAR]
                        Year (default: 2020)
  --all, -a             Print all sessions in the chosen year. (default:
                        False)
  --reverse, -r         Print sessions in reverse order. (default: False)
  --henriradovan, -hr   Print lines with MJDs. (default: False)
```

```
./SchedScrape.py -p P2780 --all
2020 Aug 03: 20:00 - Aug 04: 05:00: P2780 (Session C): <br>
2020 Jul 26: 07:45 - 11:30: P2780 (Session D): <br>
2020 Jul 25: 15:45 - Jul 26: 03:00: P2780 (Session A): <br>
2020 Jul 25: 11:15 - 14:00: P2780 (Session D): <br>
2020 Jul 20: 19:45 - Jul 21: 06:15: P2780 (Session B): <br>
2020 Jul 12: 21:15 - Jul 13: 06:30: P2780 (Session C): <br>
2020 Jul 11: 08:45 - 15:30: P2780 (Session D): <br>
...
```

Output above has been truncated. Prints well-formated lines to be copied to the wiki.
Does other stuff too. A current list of project IDs supported (at GBO/AO) can be found
in SupportedProjIDs.list. Default behavior is to print wiki-format lines, but this is
in active development and may change soon. See issues for more info and open one or
several for suggestions, bugs.

### Dependencies

Before you can use SchedScrape, make sure you have access to:

```
astropy
...and some other things...
```

### Get SchedScrape 

To grab a copy of SchedScrape, do:

```
git clone git://github.com/swiggumj/SchedScrape.git
```
