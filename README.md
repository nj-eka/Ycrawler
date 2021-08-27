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

## report example:
``` json
{
    "28322971": {
        "title": "Apple agrees to settle potential class action suit by U.S. developers",
        "url": "https://www.axios.com/apple-settles-developer-class-action-c13bb308-daf3-4231-a399-ffd48b6b2c52.html",
        "status": "ok",
        "dir": ".../Ycrawler/news/28322971",
        "fetch_total_count": 16,
        "fetch_total_time": 15.656062635000126,
        "fetch_total_size": 2258463,
        "fetch_ok_count": 16,
        "file": ".../Ycrawler/news/28322971/news_www_axios_com__apple-settles-developer-class-action-c13bb308-daf3-4231-a399-ffd48b6b2c52.html",
        "comms_results": [
            ".../Ycrawler/news/28322971/comm_datatracker_ietf_org__doc__html__rfc7231.html",
            ".../Ycrawler/news/28322971/comm_unicode_org__notes__tn27.html",
            ".../Ycrawler/news/28322971/comm_www_theverge_com__2021__5__4__22418828__apple-app-store-commission-30-percent-phil-schiller-2011-epic-lawsuit.html",
            ".../Ycrawler/news/28322971/comm_web_archive_org__web__20201128030647__https:____developer.apple.html",
            ".../Ycrawler/news/28322971/comm_www_apple_com__newsroom__2021__08__apple-us-developers-agree-to-app-store-updates.html",
            ".../Ycrawler/news/28322971/comm_web_archive_org__web__20210825162013__https:____developer.apple.html",
            ".../Ycrawler/news/28322971/comm_s3_documentcloud_org__documents__21049923__apple_proposed_settlement.pdf",
            ".../Ycrawler/news/28322971/comm_33mail_com__AQwZJR3.html",
            ".../Ycrawler/news/28322971/comm_news_ycombinator_com__item.html",
            ".../Ycrawler/news/28322971/comm_www_gamesindustry_biz__articles__2020-09-30-epic-and-apple-decline-trial-by-jury.html",
            ".../Ycrawler/news/28322971/comm_news_ycombinator_com__item.html",
            ".../Ycrawler/news/28322971/comm_sixcolors_com__post__2021__04__apples-record-second-quarter-in-charts.html",
            ".../Ycrawler/news/28322971/comm_www_marketwatch_com__story__how-profitable-is-apples-app-store-even-a-landmark-antitrust-trial-couldnt-tell-us-11622224506.html",
            ".../Ycrawler/news/28322971/comm_smallappdeveloperassistance_com.html"
        ]
    },
    "28324311": {
        "title": "Illustrated Redirection Tutorial",
        "url": "https://wiki.bash-hackers.org/howto/redirection_tutorial",
        "status": "in process",
        "dir": ".../Ycrawler/news/28324311",
        "fetch_total_count": 1
    },
    "28312632": {
        "title": "Linux in a Pixel Shader \u2013 A RISC-V Emulator for VRChat",
        "url": "https://blog.pimaker.at/texts/rvc1/",
        "status": "ok",
        "dir": ".../Ycrawler/news/28312632",
        "fetch_total_count": 13,
        "fetch_total_time": 5.764430614999583,
        "fetch_total_size": 2684420,
        "fetch_ok_count": 13,
        "file": ".../Ycrawler/news/28312632/news_blog_pimaker_at__texts__rvc1.html",
        "comms_results": [
            ".../Ycrawler/news/28312632/comm_en_wikipedia_org__wiki__Croquet_Project.html",
            ".../Ycrawler/news/28312632/comm_www_youtube_com__watch.html",
            ".../Ycrawler/news/28312632/comm_www_youtube_com__watch.html",
            ".../Ycrawler/news/28312632/comm_www_youtube_com__watch.html",
            ".../Ycrawler/news/28312632/comm_news_ycombinator_com__item.html",
            ".../Ycrawler/news/28312632/comm_www_youtube_com__watch.html",
            ".../Ycrawler/news/28312632/comm_twitter_com___g1fan___status__1427073177142939648.html",
            ".../Ycrawler/news/28312632/comm_twitter_com__fuopy__status__1427051048032620544.html",
            ".../Ycrawler/news/28312632/comm_twitter_com__whitequark.html",
            ".../Ycrawler/news/28312632/comm_dolphin-emu_org__blog__2017__07__30__ubershaders.html",
            ".../Ycrawler/news/28312632/comm_twitter_com__theprincessxena__status__1431042936045715457.html"
        ]
    },
    "28319624": {
        "title": "Yt-dlp \u2013 A YouTube-dl fork with additional features and fixes",
        "url": "https://github.com/yt-dlp/yt-dlp",
        "status": "news saved",
        "dir": ".../Ycrawler/news/28319624",
        "fetch_total_count": 2,
        "fetch_total_time": 0.7834664649999468,
        "fetch_total_size": 479093,
        "fetch_ok_count": 1,
        "file": ".../Ycrawler/news/28319624/news_github_com__yt-dlp__yt-dlp.html"
    },
    "results": [
        "28322971",
        "Cannot connect to host wiki.bash-hackers.org:443 ssl:True [SSLCertVerificationError: (1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1129)')]",
        "28312632",
        "Connection timeout to host https://news.ycombinator.com/item?id=28319624"
    ]
}
```


