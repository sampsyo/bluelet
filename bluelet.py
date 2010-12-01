import socket
import select

class Event(object):
    def waitables(self):
        raise NotImplementedError()
    def fire(self):
        raise NotImplementedError()
    
class AcceptEvent(Event):
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

class ReceiveEvent(Event):
    def __init__(self, conn):
        self.conn = conn
    def waitables(self):
        return (self.conn.sock,), (), ()
    def fire(self):
        return self.conn.sock.recv(1024)
class SendEvent(Event):
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
        self.event = coro.next()
def spawn(coro):
    return SpawnEvent(coro)

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
                events[event.event] = event.coro
                
                # Advance the old coroutine.
                new_event = coro.send(None)
                del events[event]
                events[new_event] = coro
            
        # Wait.
        waitables = {}
        iwait, owait, ewait = [], [], []
        for event, coro in events.items():
            if not isinstance(event, SpawnEvent):
                print event
                i, o, e = event.waitables()
                iwait += i
                owait += o
                ewait += e
                for waitable in i + o + e:
                    waitables[waitable] = event
        print iwait, owait, ewait
        iready, oready, eready = select.select(iwait, owait, ewait)
    
        # Fire.
        for ready in iready + oready + eready:
            event = waitables[ready]
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
    listener = Listener('127.0.0.1', 4920)
    while True:
        conn = yield listener.accept()
        yield spawn(echoer(conn))
if __name__ == '__main__':
    trampoline(echoserver())
