import sys
sys.path[0:0] = '..'
import bluelet

def echoer(conn):
    while True:
        data = yield conn.recv(1024)
        if not data:
            break
        yield conn.sendall(data)

if __name__ == '__main__':
    bluelet.run(bluelet.server('', 4915, echoer))
