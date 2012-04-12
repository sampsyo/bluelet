from __future__ import print_function
import sys
sys.path.insert(0, '..')
import bluelet
import multiprocessing


def root1():
    listener = bluelet.Listener('127.0.0.1', 4915)
    conn = yield listener.accept()
    listener.close()

    yield conn.sendall(b'a message\n')
    conn.close()

    yield bluelet.null()


def root2():
    conn = yield bluelet.connect('127.0.0.1', 4915)

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


def main():
    ta = BlueletProc(root1())
    tb = BlueletProc(root2())
    ta.start()
    tb.start()
    ta.join()
    tb.join()


if __name__ == '__main__':
    main()
