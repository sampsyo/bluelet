import sys
import urllib
import json
sys.path.insert(0, '..')
import bluelet

URL = 'http://api.twitter.com/1/statuses/user_timeline.json' \
      '?screen_name=%s&count=1'
USERNAMES = ('samps', 'b33ts', 'ev', 'biz', 'twitter')

def run_bluelet():
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

if __name__ == '__main__':
    tweets = run_bluelet()
    for name, tweet in tweets.iteritems():
        print '%s: %s' % (name, tweet)
