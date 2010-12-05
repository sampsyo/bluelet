Bluelet
=======

Bluelet is a simple, pure-Python solution for writing intelligible asynchronous socket applications. It uses `PEP 342 coroutines`_ to make concurrent I/O look and act like sequential programming.

In this way, it is similar to the `Greenlet`_ green-threads library and its associated packages `Eventlet`_ and `Gevent`_. Bluelet has a simpler, 100% Python implementation that comes at the cost of flexibility and performance when compared to Greenlet-based solutions. However, it should be sufficient for many applications that don't need serious scalability; it can be thought of as a less-horrible alternative to `asyncore`_ or an asynchronous replacement for `SocketServer`_.

.. _PEP 342 coroutines: http://www.python.org/dev/peps/pep-0342/
.. _asyncore: http://docs.python.org/library/asyncore.html
.. _SocketServer: http://docs.python.org/library/socketserver.html
.. _Greenlet: http://pypi.python.org/pypi/greenlet
.. _Eventlet: http://eventlet.net/
.. _Gevent: http://www.gevent.org/

The "Echo" Server
-----------------

An "echo" server is a canonical stupid example for demonstrating socket programming. It simply accepts connections, reads lines, and writes everything it reads back to the client.

Here's an example using plain Python sockets::

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

The code is very simple, but its synchronousness has a major problem: the server can accept only one connection at a time. This won't do even for very small server applications.

One solution to this problem is to fork several operating system threads or processes that each run the same synchronous code. This, however, quickly becomes complex and makes the application harder to manage. Python's asyncore module provides a way to write *asynchronous* servers that accept multiple connections in the same OS thread::

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

Async I/O lets the thread run a single ``select()`` loop to handle all connections and send *callbacks* when events (such as accepts and data packets) occur. However, the code becomes much more complex: the execution of a simple echo server gets broken up into smaller methods and the control flow becomes hard to follow.

Bluelet (like other coroutine-based async I/O libraries) lets you write code that *looks* sequential but *acts* concurrent. Like so::

  import bluelet
  def echoer(conn):
      while True:
          data = yield conn.recv(1024)
          if not data:
              break
          yield conn.sendall(data)
  bluelet.run(bluelet.server('', 4915, echoer))

Except for the ``yield`` keyword, note that this code appears very similar to our first, sequential version. (Bluelet also takes care of the boilerplate socket setup code.) This works because ``echoer`` is a Python coroutine: everywhere it says ``yield``, it temporarily suspends its execution. Bluelet's scheduler then takes over and waits for events, just like asyncore. When a socket event happens, the coroutine is resumed at the point it yielded. So there's no need to break up your code; it can all appear as a single code block. Neat!

Authors
-------

Bluelet is by `Adrian Sampson`_.

.. _Adrian Sampson: http://github.com/sampsyo/
