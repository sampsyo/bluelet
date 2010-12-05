import asyncore
import socket
class Echoer(asyncore.dispatcher_with_send):
    def handle_read(self):
        data = self.recv(1024)
        self.send(data)
class EchoServer(asyncore.dispatcher):
    def __init__(self):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(('', 4915))
        self.listen(1)
    def handle_accept(self):
        sock, addr = self.accept()
        handler = Echoer(sock)
server = EchoServer()
asyncore.loop()
