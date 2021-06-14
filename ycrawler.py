#!/usr/bin/env python
"""
Async crawler for news site https://news.ycombinator.com that:
    - for each {n} seconds
        - download top {m} news pages (only new ones - previously unread) 
            - with all pages by links in comments per news
        - save downloaded news pages into {dir}/{news-id}
"""
import os
import sys
import logging
import argparse
import json
import time

import asyncio
import aiohttp
import aiofiles
from contextvars import ContextVar  # added for usage testing (some experiments)
import uvloop  # https://github.com/MagicStack/uvloop

from typing import Callable
from functools import wraps, partial
from mimetypes import guess_extension
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

RESTART_INTERVAL = 60.  # in secs
START_PAGE = 'https://news.ycombinator.com'
COMMENTS_PAGE_TEMPLATE = START_PAGE + '/item?id={news_id}'
TOP_NEWS = 4
OUTPUT_DIR = 'news'  # news/{id}/{main_page_name}.{mimetypes.guess_extention()}
MAX_FILE_NAME_LENGTH = 126
# not to hang host with open requests
REQUEST_CHUNKS = 256  # maximum number of concurrently open requests - semaphore (or aiohttp.TCPConnector(limit=...)) 
REQUEST_TIMEOUT = 16.  # in secs
# not to be blocked by providers
REQUEST_LIMIT_PER_HOST = 8
# todo: + REQUEST_DELAY_PER_HOST = 0.42  
_request_headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9", 
    "Accept-Encoding": "gzip, deflate", 
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8", 
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36", 
}  

from collections import defaultdict
news_stats = defaultdict(dict)

# context vars declaration:
cv_news_id: ContextVar[str] = ContextVar('Id of news processed in current context', default = None)
# cv_news_stats: ContextVar[dir] = ContextVar('Current news stats dict', default = None)  # == news_stats[cv_news_id.get()] 

def parse_input_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--loglevel', type=str, 
                        default='debug', choices=['debug', 'info', 'error'], help='Logging level.')
    parser.add_argument('-f', '--logfile', type=str, 
                        default=None, help='Logging to file.')
    parser.add_argument('-r', '--restart', type=float, 
                        default=RESTART_INTERVAL, help='Restart period.')
    parser.add_argument('-n', '--top', type=int,
                        default=TOP_NEWS, help='Top news count.')
    parser.add_argument('-c', '--chunks', type=int,
                        default=REQUEST_CHUNKS, help='Max allowed simultaneous requests.')
    parser.add_argument('-t', '--timeout', type=float,
                        default=REQUEST_TIMEOUT, help='Request timeout.')
    parser.add_argument('-s', '--limitperhost', type=int,
                        default=REQUEST_LIMIT_PER_HOST, help='Open requests limit per host.')
    parser.add_argument('-o', '--output', type=str,
                        default=OUTPUT_DIR, help='Output directory.')
    return parser.parse_args()

def fetch_profile(func):
    # async def afunc(func, *args, **kwargs):
    #     if asyncio.iscoroutinefunction(func):
    #         return await func(*args, **kwargs)
    #     else:
    #         return func(*args, **kwargs)
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if (news_id := cv_news_id.get()) and (stats := news_stats[news_id]):
            stats['fetch_total_count'] = stats.get('fetch_total_count',0) + 1
            start_ts = time.perf_counter()
            result = await func(*args, **kwargs)
            stats['fetch_total_time'] = stats.get('fetch_total_time',0) + time.perf_counter() - start_ts
            stats['fetch_total_size'] = stats.get('fetch_total_size',0) + len(result[0])
            stats['fetch_ok_count'] = stats.get('fetch_ok_count',0) + 1
            return result
        return await func(*args, **kwargs)
    return wrapper

@fetch_profile
async def session_fetch(url: str, session: aiohttp.ClientSession) -> tuple[bytes, str]:
    async with session.get(url) as response:  
        response.raise_for_status()  # if 400 <= self.status ... raise ClientResponseError - for now it's okay
        content = await response.read()
        return content, response.headers['Content-Type']

async def timed_session_fetch(url: str, session: aiohttp.ClientSession, timeout: float):
    #*When a timeout occurs, it cancels the task and raises TimeoutError. 
    # To avoid the task cancellation, wrap it in shield().
    # If the wait is cancelled, the task is also cancelled.
    return await asyncio.wait_for(session_fetch(url, session), timeout=timeout)   

async def sem_timed_session_fetch(url: str, sem: asyncio.Semaphore, timeout: float, session: aiohttp.ClientSession):
    async with sem:
        logging.debug('semaphore passed with value %d', sem._value)
        return await timed_session_fetch(url, session, timeout)

async def save_content(content: bytes, dir_path: Path, url: str, content_type: str, prefix: str = ''):
    logging.debug('Start saving content in [%s] from [%s] with [%s] and length [%d]', dir_path, url, content_type, len(content))
    url_parts = urlparse(url)
    file_name = prefix + '_' +\
                (url_parts.netloc.replace('.', '_') +\
                 url_parts.path.rstrip('/').replace('/', '__'))[-MAX_FILE_NAME_LENGTH + len(prefix):]
    file_name = Path(file_name)
    file_name = dir_path / file_name.with_suffix(guess_extension(content_type.partition(';')[0].strip()))
    logging.debug('-> [%s]', file_name)
    # (file_name if file_name.suffix else file_name.with_suffix(guess_extension(content_type.partition(';')[0].strip())))
    async with aiofiles.open(file_name, mode='wb') as af:  # encoding...
        await af.write(content)
    logging.debug('File [%s] saved - ok', file_name)
    return str(file_name)

async def process_comment(fetch_page: Callable, url: str, output_dir: Path):
    content, content_type = await fetch_page(url)
    return await save_content(content, output_dir, url, content_type, 'comm')

async def process_news(fetch_page: Callable, news_id: str, href: str, output: str):
    cv_news_id.set(news_id)
    stats = news_stats[news_id]
    stats['status'] = 'in process'
 
    output_dir = Path(output).expanduser().resolve() / news_id
    output_dir.mkdir(parents=True, exist_ok=True)
    stats['dir'] = str(output_dir)

    url = urljoin(START_PAGE, href)
    stats['url'] = url

    # news 
    content, content_type = await fetch_page(url)
    stats['status'] = 'news loaded'
    stats['file'] = await save_content(content, output_dir, url, content_type, 'news')
    stats['status'] = 'news saved'

    # comments
    content, content_type = await fetch_page(COMMENTS_PAGE_TEMPLATE.format(news_id=news_id))
    tasks = []
    visited_comments_url = set()
    parser = BeautifulSoup(markup=content, from_encoding=content_type.partition('charset=')[-1], features='html.parser')
    for comment_a_elem in parser.find_all('a', attrs={'rel': 'nofollow'}):
        if (comment_url := urljoin(START_PAGE, comment_a_elem['href'])) not in visited_comments_url:
            logging.info(f'Fetching comments for news id:{news_id} title:"{comment_a_elem.string}" from url:{comment_url}')
            tasks.append(asyncio.create_task(process_comment(fetch_page, comment_url, output_dir)))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    results = list(map(str, results))
    # errors in comments processing will not be handled - see logs
    logging.debug('%s - comments processed with results: %s', news_id, results)
    stats['comms_results'] = results
    stats['status'] = 'ok'
    return news_id

async def async_main(args):
    session_counter = 0
    news_processed = set()
    while True:
        logging.info('Start crawling session № %d', session_counter)
        chunks_semaphore = asyncio.Semaphore(args.chunks)
        tcp_conn = aiohttp.TCPConnector(limit_per_host=REQUEST_LIMIT_PER_HOST)
        jar = aiohttp.DummyCookieJar()
        async with aiohttp.ClientSession(headers=_request_headers, connector=tcp_conn, cookie_jar=jar) as client_session:
            fetch_page = partial(sem_timed_session_fetch, sem = chunks_semaphore, timeout = args.timeout, session = client_session)
            content, content_type = await fetch_page(START_PAGE)
            tasks, news_ids = [], []
            parser = BeautifulSoup(markup=content, from_encoding=content_type.partition('charset=')[-1], features='html.parser')
            for news_tr_elem in parser.find_all('tr', 'athing', limit=args.top):
                if (news_id := news_tr_elem['id']) not in news_processed:
                    news_ids.append(news_id)
                    news_a_elem = news_tr_elem.select_one("a.storylink")
                    news_stats[news_id] = {
                        'title': (news_title := news_a_elem.string),
                        'url': (news_href := news_a_elem["href"]),
                        'status': 'found',
                    }
                    logging.info('Fetching news id:%s title:"%s" from url:%s' % (news_id, news_title, news_href))
                    tasks.append(asyncio.create_task(process_news(fetch_page, news_id, news_href, args.output)))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            logging.debug('Results: %s', results)
            results = list(map(str, results))
            news_stats['results'] = results
            # at the next session, news with errors will be reloaded (probably)
            # this option is good for handling connection errors
            # as for the rest - normal resolutions have not yet been found -> see logs
            news_session_processed = list(filter(lambda elm: type(elm) == str, results))
            news_processed.update(news_session_processed)
            logging.info('+ %d (from %d) fresh news successfully received. ids = %s', len(news_session_processed), len(news_stats), news_session_processed)
        logging.info('Stop crawling session № %d', session_counter)
        with open(f'news_stats_{time.strftime("%Y%m%d%H%M%S")}_{session_counter}.json', 'w') as f:
            json.dump(news_stats, f)
        news_stats.clear()        
        await asyncio.sleep(args.restart)
        session_counter += 1

if __name__ == '__main__':
    args = None
    try:
        assert sys.version_info >= (3, 7), "Python 3.7+ required"
        args = parse_input_args()
        logging.basicConfig(filename=args.logfile,
                            format='[%(asctime)s] %(levelname).1s %(message)s',
                            datefmt='%Y.%m.%d %H:%M:%S',
                            level=args.loglevel.upper())
        logging.info('ycrawler started with args: %s', args)
        uvloop.install()
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        logging.info('ycrawler is stopped by user.')
    except BaseException as err:
        logging.exception(f'ycrawler stopped unexpectedly due to error: %s', err, stack_info=True if not args or args.loglevel.upper() == 'DEBUG' else False)
