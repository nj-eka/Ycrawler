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

import asyncio
import aiohttp
import aiofiles
import uvloop  # https://github.com/MagicStack/uvloop


from typing import Callable
from functools import partial
from mimetypes import guess_extension
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

RESTART_INTERVAL = 60.  # in secs
START_PAGE = 'https://news.ycombinator.com'
COMMENTS_PAGE_TEMPLATE = START_PAGE + '/item?id={news_id}'
TOP_NEWS = 10
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

async def _fetch(url: str, session: aiohttp.ClientSession) -> tuple[bytes, str]:
    async with session.get(url) as response:  
        # todo: adding latency for requests per host can help mimic user behavior
        #       for this, one more level of wrapping (fifth here)) is required which will start tasks grouped by hosts 
        response.raise_for_status()  # if 400 <= self.status ... raise ClientResponseError - for now it's okay
        content = await response.read()
        return content, response.headers['Content-Type']

async def _fetch_timed(url: str, session: aiohttp.ClientSession, timeout: float):
    #*When a timeout occurs, it cancels the task and raises TimeoutError. 
    # To avoid the task cancellation, wrap it in shield().
    # If the wait is cancelled, the task is also cancelled.
    return await asyncio.wait_for(_fetch(url, session), timeout=timeout)   

async def fetch(url: str, session: aiohttp.ClientSession, sem: asyncio.Semaphore, timeout: float):
    async with sem:
        logging.debug('semaphore passed with value %d', sem._value)
        return await _fetch_timed(url, session, timeout)

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
    return file_name

async def process_comment(fetch_page: Callable, url: str, output_dir: Path):
    content, content_type = await fetch_page(url)
    return await save_content(content, output_dir, url, content_type, 'comm')

async def process_news(fetch_page: Callable, news_id: str, href: str, output: str):
    current_news_id_ctx.set(news_id)
    output_dir = Path(output) / news_id
    output_dir.mkdir(parents=True, exist_ok=True)
    url = urljoin(START_PAGE, href)
    content, content_type = await fetch_page(url)
    await save_content(content, output_dir, url, content_type, 'news')
    content, content_type = await fetch_page(COMMENTS_PAGE_TEMPLATE.format(news_id=news_id))
    tasks = []
    visited_comments_url = set()
    parser = BeautifulSoup(markup=content, from_encoding=content_type.partition('charset=')[-1], features='html.parser')
    for comment_a_elem in parser.find_all('a', attrs={'rel': 'nofollow'}):
        if (comment_url := urljoin(START_PAGE, comment_a_elem['href'])) not in visited_comments_url:
            logging.info(f'Fetching comments for news id:{news_id} title:"{comment_a_elem.string}" from url:{comment_url}')
            tasks.append(asyncio.create_task(process_comment(fetch_page, comment_url, output_dir)))
    # errors in comments processing will not be handled - see logs
    await asyncio.gather(*tasks, return_exceptions=True)
    return news_id

async def async_main(args):
    session_counter = 0
    visited_news = set()
    while True:
        logging.info('Start crawling session № %d', session_counter) 
        chunks_semaphore = asyncio.Semaphore(args.chunks)
        tcp_conn = aiohttp.TCPConnector(limit_per_host=REQUEST_LIMIT_PER_HOST)
        jar = aiohttp.DummyCookieJar()
        async with aiohttp.ClientSession(headers=_request_headers, connector=tcp_conn, cookie_jar=jar) as client_session:
            fetch_page = partial(fetch, session = client_session, sem = chunks_semaphore, timeout = args.timeout)
            content, content_type = await fetch_page(START_PAGE)
            tasks = []
            parser = BeautifulSoup(markup=content, from_encoding=content_type.partition('charset=')[-1], features='html.parser')
            for news_tr_elem in parser.find_all('tr', 'athing', limit=args.top):
                if (news_id := news_tr_elem['id']) not in visited_news:
                    news_a_elem = news_tr_elem.select_one("a.storylink")
                    logging.info('Fetching news id:%s title:"%s" from url:%s' % (news_id, news_a_elem.string, news_a_elem["href"]))
                    tasks.append(asyncio.create_task(process_news(fetch_page, news_id, news_a_elem["href"], args.output)))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # at the next restart, news with errors will be reloaded
            # this option is good for handling connection errors
            # as for the rest... normal resolutions have not yet been found - just see logs.
            session_news = list(filter(lambda elm: type(elm) == str, results))
            visited_news.update(session_news)
            logging.info('+ %d fresh news successfully received. ids = %s', len(session_news), session_news)
        logging.info('Stop crawling session № %d', session_counter)
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
