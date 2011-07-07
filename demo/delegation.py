"""A demonstration of Bluelet's approach to invoking (delegating to)
sub-coroutines and spawning child coroutines.
"""
import sys
sys.path.insert(0, '..')
import bluelet

def child():
    print 'Child started.'
    yield bluelet.null()
    print 'Child resumed.'
    yield bluelet.null()
    print 'Child ending.'
    yield bluelet.end(42)
def parent():
    print 'Parent started.'
    yield bluelet.null()
    print 'Parent resumed.'
    result = yield child()
    print 'Child returned:', repr(result)
    print 'Parent ending.'

def exc_child():
    yield bluelet.null()
    raise Exception()
def exc_parent():
    try:
        yield exc_child()
    except Exception, exc:
        print 'Parent caught:', repr(exc)
def exc_grandparent():
    yield bluelet.spawn(exc_parent())

if __name__ == '__main__':
    bluelet.run(parent())
    bluelet.run(exc_grandparent())
