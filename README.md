# Ycrawler
Async crawler for news site https://news.ycombinator.com that:
- for each {n} seconds
    - download top {m} news pages (only new ones - previously unread) 
        - with all pages by links in comments per news
    - save downloaded news pages into {dir}/{news-id}

## Installation & Usage:
- Depends:
    - OS: Linux
    - Python: 3.9*

```
$ git clone https://github.com/nj-eka/Ycrawler.git
$ cd Ycrawler
$ pip -install -r requiremenets.txt
```

```
usage: ycrawler.py [-h] [-l {debug,info,error}] [-f LOGFILE] [-r RESTART] [-n TOP] [-c CHUNKS] [-t TIMEOUT] [-s LIMITPERHOST] [-o OUTPUT]

optional arguments:
  -h, --help            show this help message and exit
  -l {debug,info,error}, --loglevel {debug,info,error}
                        Logging level.  
                        default='debug'
  -f LOGFILE, --logfile LOGFILE
                        Logging to file. 
                        default=None (==stdout)    
  -r RESTART, --restart RESTART 
                        Restart interval. 
                        default = RESTART_INTERVAL = 60.  # in secs
  -n TOP, --top TOP     Top news count.
  -c CHUNKS, --chunks CHUNKS
                        Max number of concurrently (async) open requests.
                        default = REQUEST_CHUNKS = 256
  -t TIMEOUT, --timeout TIMEOUT
                        Request timeout.
                        default = REQUEST_TIMEOUT = 16.  # in secs
  -s LIMITPERHOST, --limitperhost LIMITPERHOST
                        Max number of open requests per host.
                        REQUEST_LIMIT_PER_HOST = 8
  -o OUTPUT, --output OUTPUT
                        Output directory.
                        default = OUTPUT_DIR = 'news'
```


