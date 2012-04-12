from __future__ import print_function
import sys
sys.path.insert(0, '..')
import bluelet
import multiprocessing

def root1(conn):
    yield conn.sendall(b'a message\n')
    conn.close()

    yield bluelet.null()

def root2(conn):
    data = yield conn.readline()
    print(repr(data))
    conn.close()

    yield bluelet.null()

class BlueletProc(multiprocessing.Process):
    def __init__(self, coro):
        super(BlueletProc, self).__init__()
        self.coro = coro

    def run(self):
        bluelet.run(self.coro)

def channel(port=4915):
    connections = [None, None]
    listener = bluelet.Listener('127.0.0.1', port)

    def listen():
        connections[0] = yield listener.accept()  # Avoiding nonlocal.
    listen_thread = listen()
    yield bluelet.spawn(listen_thread)

    connections[1] = yield bluelet.connect('127.0.0.1', port)

    yield bluelet.join(listen_thread)

    yield bluelet.end(connections)

def main():
    conn1, conn2 = yield channel()
    if False:
        # Run in bluelet (i.e., no parallelism).
        yield bluelet.spawn(root1(conn1))
        yield bluelet.spawn(root2(conn2))
    else:
        # Run in separate processes.
        ta = BlueletProc(root1(conn1))
        tb = BlueletProc(root2(conn2))
        ta.start()
        tb.start()
        ta.join()
        tb.join()

if __name__ == '__main__':
    bluelet.run(main())
