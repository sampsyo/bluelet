"""Demonstrates various ways of writing an application that makes
many URL requests.

Unfortunately, because the Python standard library only includes
blocking HTTP libraries, taking advantage of asynchronous I/O currently
entails writing a custom HTTP client. This example includes a very
simple, GET-only HTTP requester.
"""
from __future__ import print_function
import sys
import json
import threading
import multiprocessing
import time
sys.path.insert(0, '..')
import bluelet

# Python 2/3 compatibility.

PY3 = sys.version_info[0] == 3
if PY3:
    from urllib.parse import urlparse
    from urllib.request import urlopen
else:
    from urlparse import urlparse
    from urllib import urlopen


URL = 'http://api.twitter.com/1/statuses/user_timeline.json' \
      '?screen_name=%s&count=1'
USERNAMES = ('samps', 'b33ts', 'twitter', 'twitterapi', 'Support')

class AsyncHTTPClient(object):
    """A basic Bluelet-based asynchronous HTTP client. Only supports
    very simple GET queries.
    """
    def __init__(self, host, port, path):
        self.host = host
        self.port = port
        self.path = path

    def headers(self):
        """Returns the HTTP headers for this request."""
        heads = [
            "GET %s HTTP/1.1" % self.path,
            "Host: %s" % self.host,
            "User-Agent: bluelet-example",
        ]
        return "\r\n".join(heads).encode('utf8') + b"\r\n\r\n"


    # Convenience methods.

    @classmethod
    def from_url(cls, url):
        """Construct a request for the specified URL."""
        res = urlparse(url)
        path = res.path
        if res.query:
            path += '?' + res.query
        return cls(res.hostname, res.port or 80, path)

    @classmethod
    def fetch(cls, url):
        """Fetch content from an HTTP URL. This is a coroutine suitable
        for yielding to bluelet.
        """
        client = cls.from_url(url)
        yield client._connect()
        yield client._request()
        status, headers, body = yield client._read()
        yield bluelet.end(body)
    

    # Internal coroutines.

    def _connect(self):
        self.conn = yield bluelet.connect(self.host, self.port)

    def _request(self):
        yield self.conn.sendall(self.headers())

    def _read(self):
        buf = []
        while True:
            data = yield self.conn.recv(4096)
            if not data:
                break
            buf.append(data)
        response = ''.join(buf)

        # Parse response.
        headers, body = response.split("\r\n\r\n", 1)
        headers = headers.split("\r\n")
        status = headers.pop(0)
        version, code, message = status.split(' ', 2)
        headervals = {}
        for header in headers:
            key, value = header.split(": ")
            headervals[key] = value

        yield bluelet.end((int(code), headers, body))


# Various ways of writing the crawler.

def run_bluelet():
    # No lock is required guarding the shared variable because only
    # one thread is actually running at a time.
    tweets = {}

    def fetch(username):
        url = URL % username
        data = yield AsyncHTTPClient.fetch(url)
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
        f = urlopen(url)
        data = f.read().decode('utf8')
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
            f = urlopen(url)
            data = f.read().decode('utf8')
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
    f = urlopen(url)
    data = f.read().decode('utf8')
    tweet = json.loads(data)[0]['text']
    return (username, tweet)
def run_processes():
    pool = multiprocessing.Pool(len(USERNAMES))
    tweet_pairs = pool.map(_process_fetch, USERNAMES)
    return dict(tweet_pairs)


# Main driver.

if __name__ == '__main__':
    strategies = {
        'bluelet': run_bluelet,
        'sequential': run_sequential,
        'threading': run_threaded,
        'multiprocessing': run_processes,
    }
    for name, func in strategies.items():
        start = time.time()
        tweets = func()
        end = time.time()
        print('%s: %.2f seconds' % (name, (end - start)))

    # Show the tweets, just for fun.
    print()
    for username, tweet in tweets.items():
        print('%s: %s' % (username, tweet))
