# Based on python web server, copyright Jon Berg , turtlemeat.com

import string,cgi,time
from os import curdir, sep, path
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import getopt
import sys
import sqlite3

global port
global db
global conn

# Default values
port = 80
db = 'obdgpslogger.db'

class RequestHandler(BaseHTTPRequestHandler):

  # Get handlers:
  # schema displays schema in a nice format
  # csv is a servlet to return data in csv format, used by graph.
  # graph is a servlet to render a graph

  def genericHeader(self, code, type):
    self.send_response(code)
    self.send_header('Content-type', type)
    self.end_headers()

  def processSchema(self, conn):
    schema = readSchema(conn)
    self.genericHeader(200, 'text/html')
    self.wfile.write("""
<html>
<head><title>Schema</title></head>
<body>
<h2>Database Schema</h2>
<table border="1">
<tr><th>Name</td><th>Type</th></tr>
""")

    for key, value in schema.items():
      self.wfile.write("<tr><td>%s</td><td>%s</td></tr>\n" % (key, value))
    self.wfile.write("""
</table>
</body>
</html>
""")

  def do_GET(self):
    try:
      if self.path == "/test":
        self.genericHeader(200, 'text/html')
        self.wfile.write("""
<html>
<head><title>Test page</title></head>
<body>
  URL: %s
</body>
</html>
""" % (self.path))
        return
      if self.path == "/schema":
        self.processSchema(conn)
      if self.path.endswith(".html"):
        f = open(curdir + sep + self.path) #self.path has /test.html
        #note that this potentially makes every file on your computer readable by the internet
        self.genericHeader(200, 'text/html')
        self.wfile.write(f.read())
        f.close()
        return
      if self.path.endswith(".csv"):
        f = open(curdir + sep + self.path) #self.path has /test.html
        #note that this potentially makes every file on your computer readable by the internet
        self.genericHeader(200, 'text/text')
        self.wfile.write(f.read())
        f.close()
        return

      return
                
    except IOError:
      self.send_error(404,'File Not Found: %s' % self.path)

def usage():
  sys.stderr.write(
      "Usage: %s [--port=port] [--db=dbname] [-? / -h / --help]\n" %
      sys.argv[0])


def readSchema(conn):
  cur = conn.cursor();
  cur.execute("select sql from sqlite_master where tbl_name='obd' and type='table'")
  row = cur.fetchone()

  contents = row[0]
  # Text is like:  
  # CREATE TABLE obd (load_pct REAL,temp REAL,REAL,time REAL, trip INTEGER, ecu INTEGER DEFAULT 0)

  # Remove up to and including opening paren, and then remove close paren
  trim = contents[contents.index('(') + 1:]
  trim = trim[0:-1]

  schema = {}
  for field in trim.split(','):
    arry = field.strip().split(' ', 2)
    schema[arry[0]] = arry[1]
  cur.close()
  return schema

def parseArgs(argv):
  global db
  global port

  opts, args = getopt.getopt(argv, "h?", ["port=", "db=", "help"])

  for o, a in opts:
    if o == "--port":
      port = int(a)
    elif o == "--db":
      db = a
    elif o in ("-h", "--help", "-?"):
      usage()
      sys.exit()
    else:
      assert False, "unhandled option"

def main(argv):
  global conn

  parseArgs(argv)

  if (not path.exists(db)):
    assert False, "Database %s does not exist" % db
  conn = sqlite3.connect(db)
  try:
    # see http://docs.python.org/library/sqlite3.html
    conn.row_factory = sqlite3.Row

    # Remove, just testing for now
    print readSchema(conn)
    print 'starting web server on port %d' % port
    server = HTTPServer(('', port), RequestHandler)
    print 'started httpserver.'
    server.serve_forever()

  except KeyboardInterrupt:
    print '^C received, shutting down server'
    server.socket.close()

  finally:
    conn.close()

if __name__ == '__main__':
  main(sys.argv[1:])

