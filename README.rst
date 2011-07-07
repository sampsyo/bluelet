Bluelet
=======

Bluelet is a simple, pure-Python solution for writing intelligible asynchronous socket applications. It uses `PEP 342 coroutines`_ to make concurrent I/O look and act like sequential programming.

In this way, it is similar to the `Greenlet`_ green-threads library and its associated packages `Eventlet`_ and `Gevent`_. Bluelet has a simpler, 100% Python implementation that comes at the cost of flexibility and performance when compared to Greenlet-based solutions. However, it should be sufficient for many applications that don't need serious scalability; it can be thought of as a less-horrible alternative to `asyncore`_ or an asynchronous replacement for `SocketServer`_ (and more).

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

Other Examples
--------------

This repository also includes a few less-trivial examples of Bluelet's
programming model.

httpd
'''''

The ``httpd.py`` example implements a very simple Web server in less than 100
lines of Python. Start the program and navigate to
http://127.0.0.1:8088/ in your Web browser to see it
in action.

This example demonstrates the implementation of a network server that is
slightly more complicated than the echo server described above. Again, the code
for the server just looks like a sequential, one-connection-at-a-time program
with ``yield`` expressions inserted—but it runs concurrently and can service
many requests at the same time.

crawler
'''''''

``crawler.py`` demonstrates how Bluelet can be used for *client* code in
addition to just servers. It implements a very simple asynchronous HTTP client
and makes a series of requests for tweets from the Twitter API.

The ``crawler.py`` program actually implements the same set of requests four
times to compare their performance:

* The sequential version makes one request, waits for the response, and then
  makes the next request.
* The "threaded" version spawns one OS thread per request and makes all the
  requests concurrently.
* The "processes" version uses Python's `multiprocessing`_ module to make
  each request in a separate OS process. It uses the multiprocessing module's
  convenient parallel ``map`` implementation.
* The Bluelet version runs each HTTP request in a Bluelet coroutine. The
  requests run concurrently but they use a single thread in a single process.

.. _multiprocessing: http://docs.python.org/library/multiprocessing.html

The sequential implementation will almost certainly be the slowest. The three
other implementations are all concurrent and should have roughly the same
performance. The thread- and process-based implementations incur spawning
overhead; the multiprocessing implementation could see advantages by avoiding
the GIL (but this is unlikely to be significant as the network latency is
dominant); the Bluelet implementation has no spawning overhead but has some
scheduling logic that may slow things down.

``crawler.py`` reports the runtime of each implementation. On my machine, this
is what I see::

  sequential: 4.62 seconds
  threading: 0.81 seconds
  multiprocessing: 0.13 seconds
  bluelet: 0.20 seconds

The numbers are noisy and somewhat inconsistent across runs, but in general we
see that Bluelet is competitive with the other two concurrent implementations
and that the sequential version is much slower.

Basic Usage
-----------

To get started with Bluelet, you just write a coroutine that yield Bluelet
events and invoke it using ``bluelet.run``::

    import bluelet
    def coro():
        yield bluelet.end()
    bluelet.run(coro())

``bluelet.run`` takes a generator (a running coroutine) as an argument and runs
it to completion. It's the gateway into the Bluelet scheduling universe.
Remember that, in Python, any "function" with a ``yield`` expression in it is a
coroutine—that's what makes ``coro`` special.

The key to programming with Bluelet is to use ``yield`` expressions where you
would typically do anything that blocks or you need to interact with the Bluelet
scheduler. Technically, every ``yield`` statement sends an "event" object to the
Bluelet scheduler that's running it, but you can usually get by without thinking
about event objects at all. Here are some of the Bluelet ``yield``
expressions that make up Bluelet's network socket API:

* ``conn = yield bluelet.connect(host, port)``: Connects to a network host and
  returns a "connection" object usable for communication.
* ``yield conn.send(data)``: Send a string of data over the connection. Returns
  the amount of data actually sent.
* ``yield conn.sendall(data)``: Send the string of data, continuously sending
  chunks of the data until it is all sent.
* ``data = yield conn.recv(bufsize)``: Receive data from the connection.
* ``data = yield conn.readline(delim="\n")``: Read a line of data from the
  connection, where lines are delimited by ``delim``.
* ``server = bluelet.Listener(host, port)``: Constructs a Bluelet server
  object that can be used to asynchronously wait for connections. (There's no
  ``yield`` here; this just a constructor.)
* ``conn = yield server.accept()``: Asynchronously wait for a connection to the
  server, returning a connection object as above.

These tools are enough to build asynchronous client and server applications with
Bluelet. There's also one convenient off-the-shelf coroutine, called
``bluelet.server``, that helps you get off the ground with a server application
quickly. This line::

    bluelet.run(bluelet.server(host, port, handler_coro))

runs an asynchronous socket server, listening for concurrent connections. For
each incoming connection ``conn``, the server calls ``handler_coro(conn))`` and
adds that coroutine to the Bluelet scheduler.

Bluelet also provides some non-socket-related tools encapsulating generic
green-threads capabilities:

* ``res = yield bluelet.call(coro())``: Invokes another coroutine as a
  "sub-coroutine", much like calling a function in ordinary Python code.
  Pedantically, the current coroutine is suspended and ``coro`` is started up;
  when ``coro`` finishes, Bluelet returns control to the current coroutine and
  returns the value returned by ``coro`` (see ``bluelet.end``, below). The
  effect is similar to Python's proposed `"yield from" syntax`_.
* ``res = yield coro())``: Shorthand for the above. Just yielding any generator
  object is equivalent to using ``bluelet.call``.
* ``yield bluelet.spawn(coro())``: Like ``call`` but makes the child coroutine
  run concurrently. Both coroutines remain in the thread scheduler. This is how
  you can build programs that, for example, handle multiple network connections
  at once (it's used internally by ``bluelet.server``).
* ``yield bluelet.end(value=None)``: Terminate the current coroutine and, if the
  present coroutine was invoked by another one using ``bluelet.call``, return
  the specified value to it. Analogous to ``return`` in ordinary Python.
* ``yield bluelet.null()``: Yield without doing anything special. This just
  makes it possible to let another coroutine run if one is waiting to. It's
  useful if you have to do a long-running, blocking operation in a coroutine and
  want to give other green threads a chance to get work done.

.. _"yield from" syntax: http://www.python.org/dev/peps/pep-0380/

Together, this small set of ``yield`` statements are enough to build any
application that can benefit from simple, pure-Python collaborative
multitasking.

Authors
-------

Bluelet is by `Adrian Sampson`_. Please contact me if you have questions or
comments about Bluelet.

.. _Adrian Sampson: http://github.com/sampsyo/
