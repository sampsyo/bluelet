import sys
import os
sys.path.insert(0, '..')
import bluelet

ROOT = '.'

def parse_request(s):
    lines = s.split('\r\n')
    method, path, version = lines.pop(0).split(None, 2)
    headers = {}
    for line in lines:
        if not line:
            continue
        key, value = line.split(': ', 1)
        headers[key] = value
    return method, path, headers

def respond(method, path, headers):
    # Strip leading / and add prefix.
    if path.startswith('/') and len(path) > 0:
        filename = path[1:]
    else:
        filename = path
    filename = os.path.join(ROOT, filename)

    if os.path.isdir(filename):
        # Directory listing.
        files = []
        for name in os.listdir(filename):
            files.append('<li><a href="%s">%s</a></li>' % (name, name))
        html = "<html><head><title>%s</title></head><body>" \
               "<h1>%s</h1><ul>%s</ul></body></html>""" % \
               (path, path, ''.join(files))
        return '200 OK', {'Content-Type': 'text/html'}, html

    elif os.path.exists(filename):
        # Send file contents.
        with open(filename) as f:
            return '200 OK', {'Content-Type': 'text/plain'}, f.read()

    else:
        # Not found.
        return '404 Not Found', {'Content-Type': 'text/html'}, \
               '<html><head><title>404 Not Found</title></head>' \
               '<body><h1>Not found.</h1></body></html>'

def webrequest(conn):
    # Get the HTTP request.
    request = ''
    while True:
        data = yield conn.recv(1024)
        if not data:
            break
        request += data
        if '\r\n\r\n' in data:
            break

    # Parse and log the request and get the response values.
    method, path, headers = parse_request(request)
    print '%s %s' % (method, path)
    status, headers, content = respond(method, path, headers)

    # Send response.
    yield conn.sendall("HTTP/1.1 %s\r\n" % status)
    for key, value in headers.iteritems():
        yield conn.sendall("%s: %s\r\n" % (key, value))
    yield conn.sendall("\r\n")
    yield conn.sendall(content)

if __name__ == '__main__':
    bluelet.run(bluelet.server('', 8088, webrequest))
