from __future__ import print_function
import sys
sys.path.insert(0, '..')
import bluelet

def sleeper(duration):
    print('Going to sleep for %i seconds...' % duration)
    yield bluelet.sleep(duration)
    print('...woke up after %i seconds.' % duration)
        
def sleepy():
    for i in (0, 1, 3, 5):
        yield bluelet.spawn(sleeper(i))

if __name__ == '__main__':
    bluelet.run(sleepy())
