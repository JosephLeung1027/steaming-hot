"""
Written by Kanishk Jain.

Once you have games-features.csv generated by games-features.py, you can scrape metacritic scores for these games using
their name in the url, e.g. https://www.metacritic.com/game/pc/counter-strike-condition-zero
"""

import pandas as pd
import time
import numpy as np
from bs4 import BeautifulSoup
from requests_toolbelt import threaded
t_setup = False

# Setup telegram to send updates - scraping takes a lot of time!
# Create a telegram bot if you don't have on https://core.telegram.org/bots#6-botfather
# Install python-telegram-bot  - pip install python-telegram-bot
t_id = '' #put telegram ID
c_id = '' #put telegram bot chat ID
if t_id and c_id:
    import telegram
    bot = telegram.Bot(token=t_id)
    t_setup = True

# Load games-features.csv file.
newdf = pd.read_csv('games-features.csv')
print('Games json has only %i/%i metacritic scores'%((newdf['Metacritic']!=0).sum(),newdf.shape[0]))

# This function initializes the session
def initialize_session(session):
    session.headers[
        'User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'
    return session


def multi_call(gameurls):
    olist = []
    outurls = []
    badnames = []
    responses, errors = threaded.map(
        [{'url': 'http://www.metacritic.com/game/pc/' + gameurl, 'method': 'GET'} for gameurl in gameurls],
        initializer=initialize_session)
    for r in responses:
        soup = BeautifulSoup(r.response.text, 'html.parser')
        try:
            score = int(soup.find('span', {'itemprop': "ratingValue"}).text)
            olist.append(score)
        except:
            score = -1
            olist.append(score)
        outurls.append(r.request_kwargs['url'].split('/')[-1])
        if r.response.status_code == 404:
            badnames.append(r.request_kwargs['url'].split('/')[-1])
    return olist, outurls, badnames


def urlify(url):
    url = url.replace("(r)", '')
    url = url.replace("(tm)", '')

    url = url.replace(" ", "-")
    url = url.replace(":", ' ')
    url = url.replace("(", '')
    url = url.replace(")", '')
    url = url.replace("/", '')

    url = '-'.join([i for i in url.split('-') if i])

    return url.lower()


bs = 100  # Batch size for parallel

rows2get = [] # Maintain a list of games without a metacritic score in original dataset.
names404 = [] # Save games that could not be found on Metacritic.com

total = 0
updated = 0
for row in range(len(newdf)):
    if newdf.Metacritic[row] == 0:
        rows2get.append(row)

    t1 = time.time()
    if len(rows2get) == bs:
        print('Getting %i-%i' % (rows2get[0], rows2get[-1]), end='\r')
        gameurls = {urlify(newdf['ResponseName'][r]): r for r in rows2get}
        olist, outurls, badnames = multi_call(list(gameurls.keys()))

        names404.append(badnames)

        newdf.at[[gameurls[ur] for ur in outurls], ['Metacritic']] = olist

        total += 1

        if (total) * bs % 10000 == 0:
            print("Saving")
            if t_setup:
                bot.sendMessage(chat_id=c_id,
                                text='Metacritic data saving...scraped %i/%i' % (rows2get[-1], newdf.shape[0]))
            newdf.to_csv('games-features-metacritic-new.csv')

        updated += np.sum(np.array(olist) != -1)
        print('Done %i time updated %i remaining %0.02f mn' % (
        rows2get[-1], updated, ((len(newdf) - rows2get[-1]) * (time.time() - t1) / 60.0 / bs)), end='\r')

        rows2get = []
