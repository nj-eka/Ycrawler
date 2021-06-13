# Ycrawler
Async crawler for news site https://news.ycombinator.com that:
    - for each {n} seconds
        - download top {m} news pages (only new ones - previously unread) 
            - with all pages by links in comments per news
        - save downloaded news pages into {dir}/{news-id}
