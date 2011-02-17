import sys
import urllib
import json
import threading
import multiprocessing
import time
sys.path.insert(0, '..')
import bluelet

URL = 'http://api.twitter.com/1/statuses/user_timeline.json' \
      '?screen_name=%s&count=1'
USERNAMES = ('samps', 'b33ts', 'ev', 'biz', 'twitter')

def run_bluelet():
    # No lock is required guarding the shared variable because only
    # one thread is actually running at a time.
    tweets = {}

    def fetch(username):
        url = URL % username
        f = urllib.urlopen(url)
        data = yield bluelet.read(f)
        tweets[username] = json.loads(data)[0]['text']

    def crawl():
        for username in USERNAMES:
            yield bluelet.spawn(fetch(username))

    bluelet.run(crawl())
    return tweets

def run_sequential():
    tweets = {}

    for username in USERNAMES:
        url = URL % username
        f = urllib.urlopen(url)
        data = f.read()
        tweets[username] = json.loads(data)[0]['text']

    return tweets

def run_threaded():
    # We need a lock to avoid conflicting updates to the tweet
    # dictionary.
    lock = threading.Lock()
    tweets = {}

    class Fetch(threading.Thread):
        def __init__(self, username):
            threading.Thread.__init__(self)
            self.username = username
        def run(self):
            url = URL % self.username
            f = urllib.urlopen(url)
            data = f.read()
            tweet = json.loads(data)[0]['text']
            with lock:
                tweets[self.username] = tweet

    # Start every thread and then wait for them all to finish.
    threads = [Fetch(name) for name in USERNAMES]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return tweets

def _process_fetch(username):
    # Mapped functions in multiprocessing can't be closures, so this
    # has to be at the module-global scope.
    url = URL % username
    f = urllib.urlopen(url)
    data = f.read()
    tweet = json.loads(data)[0]['text']
    return (username, tweet)
def run_processes():
    pool = multiprocessing.Pool(len(USERNAMES))
    tweet_pairs = pool.map(_process_fetch, USERNAMES)
    return dict(tweet_pairs)

if __name__ == '__main__':
    strategies = {
        'bluelet': run_bluelet,
        'sequential': run_sequential,
        'threading': run_threaded,
        'multiprocessing': run_processes,
    }
    for name, func in strategies.iteritems():
        start = time.time()
        tweets = func()
        end = time.time()
        print '%s: %.2f seconds' % (name, (end - start))

    # Show the tweets, just for fun.
    print
    for username, tweet in tweets.iteritems():
        print '%s: %s' % (username, tweet)
