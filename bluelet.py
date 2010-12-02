import socket
import select

class Event(object):
    pass
class WaitableEvent(Event):
    def waitables(self):
        """Return "waitable" objects to pass to select. Should return
        three iterables for input readiness, output readiness, and
        exceptional conditions (i.e., the three lists passed to
        select()).
        """
        return (), (), ()
    def fire(self):
        pass

class NullEvent(Event):
    """An event that does nothing. Used to simply yield control."""
    
class AcceptEvent(WaitableEvent):
    def __init__(self, listener):
        self.listener = listener
    def waitables(self):
        return (self.listener.sock,), (), ()
    def fire(self):
        sock, addr = self.listener.sock.accept()
        return Connection(sock, addr)
class Listener(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen(1)
    def accept(self):
        return AcceptEvent(self)
    def close(self):
        self.sock.close()

class ReceiveEvent(WaitableEvent):
    def __init__(self, conn, bufsize):
        self.conn = conn
        self.bufsize = bufsize
    def waitables(self):
        return (self.conn.sock,), (), ()
    def fire(self):
        return self.conn.sock.recv(self.bufsize)
class SendEvent(WaitableEvent):
    def __init__(self, conn, data):
        self.conn = conn
        self.data = data
    def waitables(self):
        return (), (self.conn.sock,), ()
    def fire(self):
        self.conn.sock.send(self.data)
class Connection(object):
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
    def close(self):
        self.sock.close()
    def read(self, bufsize):
        return ReceiveEvent(self, bufsize)
    def write(self, data):
        return SendEvent(self, data)

class SpawnEvent(object):
    def __init__(self, coro):
        self.spawned = coro
def spawn(coro):
    return SpawnEvent(coro)

def _event_select(events):
    """Perform a select() over all the Events provided, returning the
    ones ready to be fired.
    """
    # Gather waitables.
    waitable_to_event = {}
    rlist, wlist, xlist = [], [], []
    for event in events:
        if isinstance(event, WaitableEvent):
            r, w, x = event.waitables()
            rlist += r
            wlist += w
            xlist += x
            for waitable in r + w + x:
                waitable_to_event[waitable] = event

    # Perform select() if we have any waitables.
    if rlist or wlist or xlist:
        rready, wready, xready = select.select(rlist, wlist, xlist)
        ready = rready + wready + xready
    else:
        ready = []

    # Gather ready events corresponding to the ready waitables.
    ready_events = set()
    for waitable in ready:
        ready_events.add(waitable_to_event[waitable])
    return ready_events

def _advance_thread(threads, event, value):
    """After an event is fired, run a given coroutine associated with
    it in the threads dict until it yields again. If the coroutine
    exits, then the thread is removed from the pool.
    """
    coro = threads[event]
    next_event = None
    try:
        next_event = coro.send(value)
    except StopIteration:
        # Thread is done.
        del threads[event]
    except:
        # Thread raised some other exception.
        del threads[event]
        raise
    else:
        # Replace key with next event produced by the thread.
        del threads[event]
        threads[next_event] = coro

def trampoline(*coros):
    # The "threads" dictionary keeps track of all the currently-
    # executing coroutines. It maps their currently-blocking "event"
    # to the associated coroutine.
    threads = {}

    # Put all coroutines into the dictionary, marking them as ready
    # to run.
    for coro in coros:
        threads[NullEvent()] = coro
    
    # Continue advancing threads until none remain (i.e., all
    # terminate).
    while threads:
        # Look for events that can be run immediately. Currently, our
        # only non-"blocking" events are spawning and the null event.
        # Continue running immediate events until nothing is ready.
        while True:
            have_ready = False
            for event in threads.keys():
                if isinstance(event, SpawnEvent):
                    threads[NullEvent()] = event.spawned # Spawn.
                    _advance_thread(threads, event, None)
                    have_ready = True
                elif isinstance(event, NullEvent):
                    _advance_thread(threads, event, None)
                    have_ready = True

            # Only start the select when nothing else is ready.
            if not have_ready:
                break
            
        # Wait and fire.
        for event in _event_select(threads.keys()):
            value = event.fire()
            _advance_thread(threads, event, value)

def echoer(conn):
    while True:
        data = yield conn.read(1024)
        if not data:
            break
        print 'Read from %s: %s' % (conn.addr[0], repr(data))
        yield conn.write(data)
    conn.close()
def echoserver():
    listener = Listener('127.0.0.1', 4917)
    while True:
        conn = yield listener.accept()
        yield spawn(echoer(conn))
if __name__ == '__main__':
    trampoline(echoserver())
