# SchedScrape 

# Usage
No setup.py (yet), so I made an executable with `chmod +x aoScrape.py`. Then,

```
./aoScrape.py -h
usage: aoScrape.py [-h] [--year [YEAR]] project [project ...]

Arecibo Schedule Scraper

positional arguments:
  project               Project code, e.g. P2780

optional arguments:
  -h, --help            show this help message and exit
  --year [YEAR], -y [YEAR]
                        Year (default: 2020)
```

```
./aoScrape.py 'P2780'
...
2020 Jul 25: 15:45 - 00:00: P2780 (Session A): <br>
2020 Jul 26: 00:00 - 03:00: P2780 (Session A): <br>
2020 Jul 26: 07:45 - 11:30: P2780 (Session D): <br>
2020 Jul 25: 11:15 - 14:00: P2780 (Session D): <br>
2020 Jul 20: 19:45 - 00:00: P2780 (Session B): <br>
2020 Jul 21: 00:00 - 06:15: P2780 (Session B): <br>
2020 Aug 10: 18:30 - 00:00: P2780 (Session B): <br>
2020 Aug 11: 00:00 - 05:00: P2780 (Session B): <br>
2020 Aug 02: 20:00 - 00:00: P2780 (Session C): <br>
2020 Aug 03: 00:00 - 05:15: P2780 (Session C): <br>
```

Output above has been truncated. Prints well-formated lines to be copied to the wiki.
Does other stuff too.

### Dependencies

Before you can use SensitivityMap, make sure you have access to:

```
astropy
...and some other things...
```

### Get SchedScrape 

To grab a copy of SchedScrape, do:

```
git clone git://github.com/swiggumj/SchedScrape.git
```
