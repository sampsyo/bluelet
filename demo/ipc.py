from __future__ import print_function
import sys
sys.path.insert(0, '..')
import bluelet
import multiprocessing
import pickle
import uuid

def thread1(ep):
    yield ep.put("hello!")
    yield ep.put(123)
    yield ep.put({"foo": "bar"})
    print((yield ep.get()))

def thread2(ep):
    print((yield ep.get()))
    print((yield ep.get()))
    print((yield ep.get()))
    yield ep.put(["test", 1234, "foo"])

class BlueletProc(multiprocessing.Process):
    def __init__(self, coro):
        super(BlueletProc, self).__init__()
        self.coro = coro

    def run(self):
        bluelet.run(self.coro)

class Endpoint(object):
    def __init__(self, conn, sentinel):
        self.conn = conn
        self.sentinel = sentinel

    def put(self, obj):
        yield self.conn.sendall(pickle.dumps(obj) + self.sentinel)

    def get(self):
        data = yield self.conn.readline(self.sentinel)
        data = data[:-len(self.sentinel)]
        yield bluelet.end(pickle.loads(data))

def channel(port=4915):
    # Create a pair of connected sockets.
    connections = [None, None]
    listener = bluelet.Listener('127.0.0.1', port)

    def listen():
        connections[0] = yield listener.accept()  # Avoiding nonlocal.
    listen_thread = listen()
    yield bluelet.spawn(listen_thread)

    connections[1] = yield bluelet.connect('127.0.0.1', port)

    yield bluelet.join(listen_thread)

    # Wrap sockets in Endpoints.
    sentinel = uuid.uuid4().bytes  # Somewhat hacky...
    yield bluelet.end((Endpoint(connections[0], sentinel),
                       Endpoint(connections[1], sentinel)))

def main():
    ep1, ep2 = yield channel()
    if False:
        # Run in bluelet (i.e., no parallelism).
        yield bluelet.spawn(thread1(ep1))
        yield bluelet.spawn(thread2(ep2))
    else:
        # Run in separate processes.
        ta = BlueletProc(thread1(ep1))
        tb = BlueletProc(thread2(ep2))
        ta.start()
        tb.start()
        ta.join()
        tb.join()

if __name__ == '__main__':
    bluelet.run(main())
