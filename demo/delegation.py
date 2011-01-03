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
    result = yield bluelet.call(child())
    print 'Child returned:', repr(result)
    print 'Parent ending.'

if __name__ == '__main__':
    bluelet.run(parent())
