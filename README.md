# SchedScrape 

# Usage
Make an executable with `chmod +x SchedScrape.py`...

```
./SchedScrape.py -h
usage: SchedScrape.py [-h] --projects PROJECTS [PROJECTS ...] [--year [YEAR]]
                      [--all] [--reverse]
                      [--printformat [{wiki,none,gbncc,default}]]

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
  --printformat [{wiki,none,gbncc,default}], -pf [{wiki,none,gbncc,default}]
                        Format of schedule info printed. (default: default)
```

```
./SchedScrape.py -p P2780 --all
P2780 | Session A | 58854.38 | 2020-01-06 05:00:00-04:00 | 2020-01-06 07:30:00-04:00
P2780 | Session B | 58880.46 | 2020-02-01 07:00:00-04:00 | 2020-02-01 17:30:00-04:00
P2780 | Session D | 58883.96 | 2020-02-04 19:00:00-04:00 | 2020-02-05 01:45:00-04:00
P2780 | Session A | 58886.28 | 2020-02-07 02:45:00-04:00 | 2020-02-07 10:30:00-04:00
P2780 | Session A | 58887.59 | 2020-02-08 10:15:00-04:00 | 2020-02-08 14:00:00-04:00
P2780 | Session C | 58893.46 | 2020-02-14 07:00:00-04:00 | 2020-02-14 16:30:00-04:00
...
```

```
./SchedScrape.py -p P2780,p2945 --all --printformat wiki -r
WARNING: Capitalizing ProjID... [__main__]
...
2020 Aug 06: 03:45 - 04:45: P2945 (0030): <br>
2020 Aug 06: 02:45 - 03:45: P2945 (2317): <br>
2020 Aug 05: 00:00 - 01:00: P2945 (2043): <br>
2020 Aug 03: 20:00 - Aug 04: 05:00: P2780 (Session C): <br>
2020 Aug 03: 19:00 - 20:00: P2945 (1640): <br>
2020 Aug 02: 03:45 - 04:45: P2945 (0030): <br>
...
```

Output above has been truncated. Prints well-formated lines to be copied to the wiki.
Does other stuff too. A current list of project IDs supported (at GBO/AO) can be found
in SupportedProjIDs.list. Default behavior is to print common info delimited by |. See
issues for more info and open one or several for suggestions, bugs.

### Dependencies

```
numpy
astropy
requests
BeautifulSoup
pytz
```

### Get SchedScrape 

```
git clone git://github.com/swiggumj/SchedScrape.git
```
