import socket
listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.bind(('', 4915))
listener.listen(1)
while True:
    sock, addr = listener.accept()
    while True:
        data = sock.recv(1024)
        if not data:
            break
        sock.sendall(data)
