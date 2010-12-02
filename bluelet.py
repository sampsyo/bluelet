import socket
import select

class Event(object):
    def __init__(self):
        raise NotImplementedError()
    def fire(self):
        pass
class WaitableEvent(Event):
    def waitables(self):
        """Return "waitable" objects to pass to select. Should return
        three iterables for input readiness, output readiness, and
        exceptional conditions (i.e., the three lists passed to
        select()).
        """
        return (), (), ()
    
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

class ReceiveEvent(WaitableEvent):
    def __init__(self, conn):
        self.conn = conn
    def waitables(self):
        return (self.conn.sock,), (), ()
    def fire(self):
        return self.conn.sock.recv(1024)
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
    def read(self):
        return ReceiveEvent(self)
    def write(self, data):
        return SendEvent(self, data)

class SpawnEvent(object):
    def __init__(self, coro):
        self.coro = coro
    def spawn(self):
        return self.coro
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

def trampoline(*coros):
    # Prime the coroutines.
    events = {}
    for coro in coros:
        event = coro.next()
        events[event] = coro
    
    while True:
        # Look for spawns.
        for event, coro in events.items():
            if isinstance(event, SpawnEvent):
                # Insert the new coroutine.
                spawned_coro = event.spawn()
                spawned_event = spawned_coro.next()
                events[spawned_event] = spawned_coro
                
                # Advance the old coroutine.
                new_event = coro.send(None)
                del events[event]
                events[new_event] = coro
            
        # Wait and fire.
        for event in _event_select(events.keys()):
            value = event.fire()
            coro = events[event]
            new_event = coro.send(value)
            del events[event]
            events[new_event] = coro

def echoer(conn):
    while True:
        data = yield conn.read()
        print 'Read from %s: %s' % (conn.addr[0], repr(data))
        yield conn.write(data)
    conn.close()
def echoserver():
    listener = Listener('127.0.0.1', 4915)
    while True:
        conn = yield listener.accept()
        yield spawn(echoer(conn))
if __name__ == '__main__':
    trampoline(echoserver())
