# (C) Robert Konigsberg 2011, All Rights Reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# 
# Web Server components based on python web server,
# copyright Jon Berg , turtlemeat.com

import cgi
import codecs
import csv
import cStringIO
import getopt
import sqlite3
import string
import StringIO
import sys
import time

from os import curdir, sep, path
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from string import Template

global port
global db
global conn

# Default values
port = 80
db = 'obdgpslogger.db'

count = 0

class UnicodeWriter:
  def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
    # Redirect output to a queue
    self.queue = cStringIO.StringIO()
    self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
    self.stream = f
    self.encoder = codecs.getincrementalencoder(encoding)()

  def writerow(self, row):
    # Prevent converting None into unicode 'None' string.
    def f(x): return unicode(s).encode("utf-8") if s else None

    self.writer.writerow([f(s) for s in row])

    # Fetch UTF-8 output from the queue ...
    data = self.queue.getvalue()
    data = data.decode("utf-8")
    # ... and reencode it into the target encoding
    data = self.encoder.encode(data)
    # write to the target stream
    self.stream.write(data)
    # empty queue
    self.queue.truncate(0)

  def writerows(self, rows):
    for row in rows:
      self.writerow(row)

class RequestHandler(BaseHTTPRequestHandler):

  def genericHeader(self, code, type):
    self.send_response(code)
    self.send_header('Content-type', type)
    self.end_headers()

  def processAbout(self, conn):
    schema = readSchema(conn)
    rowCount = getRowCount(conn, "obd")
    def fmtline(key, value):
      return "<tr><td>%s</td><td>%s</td></tr>\n" % (key, value)
    fields = "\n".join([ fmtline(key, value) for key, value in schema.items()])

    range = getDateRange(conn)
    # Convert to int (1000 * self)
    range = [int(range[0] * 1000), int(range[1] * 1000)]

    self.renderTemplate("www/about.template",
       fields=fields, rowCount=rowCount,
       earliestDate=range[0], latestDate=range[1])

  def processCsv(self, conn):
    # Read the schema to find out which fields to export.
    fields = []
    schema = readSchema(conn)
    for key, value in schema.items():
      if (key == 'time'): continue
      if (value == 'REAL' or value == 'INTEGER'):
        fields.append(key)
 
    c = conn.cursor()
    sql = "select time, %s from obd" % (','.join(fields))
    c.execute(sql)

    # Using a StringIO as an intermediate object. Probably more efficient
    # to use some version of select/recv, but I don't know how to do that.
    intermediateOutput = StringIO.StringIO()
    writer = UnicodeWriter(intermediateOutput)

    # Write the header
    headers = ["Date"]
    headers.extend(fields)
    writer.writerow(headers)

    writer.writerows(c)

    self.genericHeader(200, 'text/html')
    self.wfile.write(intermediateOutput.getvalue())

  def renderTemplate(self, file, **kwds):
    f = open(curdir + sep + file)
    template = Template(f.read())
    html = template.substitute(**kwds)
    self.genericHeader(200, 'text/html')
    self.wfile.write(html)
    f.close()
  
  def processGraph(self, conn):
    fields = [];
    schema = readSchema(conn)
    for key, value in schema.items():
      if (key == 'time'): continue
      if (value == 'REAL' or value == 'INTEGER'):
        fields.append(key)

    jsfields = "fields=[%s];\n" % ", ".join(map(lambda(x): "\"%s\"" % x, fields));

    trips = getTrips(conn)
    jstrips = "trips=[%s];\n" % ", ".join(map(lambda(x): "[%d, %d]" % (x[0], x[1]), trips));
 
    f = open(curdir + sep + "www/graph.template")
    template = Template(f.read())
    html = template.substitute(javascriptFields=jsfields, javascriptTrips = jstrips)
    self.genericHeader(200, 'text/html')
    self.wfile.write(html)
    f.close()

  def sendFile(self, name, type):
    f = open(curdir + sep + name)
    self.genericHeader(200, type);
    self.wfile.write(f.read())
    f.close()

  def do_GET(self):
    try:
      if self.path == "/":
        self.renderTemplate("www/root.template")
        return

      if self.path == "/test":
        self.renderTemplate("www/test.template", path=self.path)
        return

      if self.path == "/about":
        self.processAbout(conn)
        return

      if self.path == "/graph":
        self.processGraph(conn)
        return

      if self.path == "/csv":
        self.processCsv(conn)
        return

      if self.path == "/interaction.js":
        self.sendFile("www/interaction.js", "text/javascript")
        return

      if self.path == "/dygraph-combined.js":
        self.sendFile("www/dygraph-combined.js", "text/javascript")
        return

      if self.path == "/favicon.ico":
        self.sendFile("www/favicon.ico", "image/x-icon")
        return

      self.send_error(404,'Unmapped Resource: %s' % self.path)
      return

    except IOError as (errno, strerror):
      sys.stderr.write("I/O error({0}): {1}\n".format(errno, strerror))
      # self.send_error(404,'File Not Found: %s' % self.path)

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

def getRowCount(conn, table):
  cur = conn.cursor();
  cur.execute("select count(0) from %s" % table);
  row = cur.fetchone()
  contents = row[0]
  cur.close
  return int(contents)

def getTrips(conn):
  data = []
  cur = conn.cursor();
  cur.execute("select tripid, start, end from trip");
  rows = cur
  for row in rows:
    data.append([row[1], row[2]]) 
  cur.close
  return data

def getDateRange(conn):
  cur = conn.cursor()
  cur.execute("select min(time), max(time) from obd")
  row = cur.fetchone()
  min = row[0]
  max = row[1]
  cur.close
  return [int(min), int(max)]

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
  # see http://docs.python.org/library/sqlite3.html
  conn.row_factory = sqlite3.Row
  print "Connected to database."

  try:
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

