# Based on python web server, copyright Jon Berg , turtlemeat.com

import string,cgi,time
from os import curdir, sep
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import getopt
import sys

global port
global db

class RequestHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    try:
      if self.path.endswith(".html"):
        f = open(curdir + sep + self.path) #self.path has /test.html
        #note that this potentially makes every file on your computer readable by the internet
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(f.read())
        f.close()
        return
      if self.path.endswith(".csv"):
        f = open(curdir + sep + self.path) #self.path has /test.html
        #note that this potentially makes every file on your computer readable by the internet
        self.send_response(200)
        self.send_header('Content-type', 'text/text')
        self.end_headers()
        self.wfile.write(f.read())
        f.close()
        return

      return
                
    except IOError:
      self.send_error(404,'File Not Found: %s' % self.path)

  def do_POST(self):
    global rootnode
    try:
      ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
      if ctype == 'multipart/form-data':
        query=cgi.parse_multipart(self.rfile, pdict)
        self.send_response(301)
    
        self.end_headers()
        upfilecontent = query.get('upfile')
        print "filecontent", upfilecontent[0]
        self.wfile.write("<HTML>POST OK.<BR><BR>");
        self.wfile.write(upfilecontent[0]);
                
    except :
      pass

def usage():
  sys.stderr.write(
      "Usage: %s [--port=port] [--db=dbname] [-? / -h / --help]\n" %
      sys.argv[0])

def main(argv):
  opts, args = getopt.getopt(argv, "h?", ["port=", "db=", "help"])

  port = 80
  db = 'obdgpslogger.db'
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

  try:
    print 'starting web server on port %d' % port
    server = HTTPServer(('', port), RequestHandler)
    print 'started httpserver.'
    server.serve_forever()
  except KeyboardInterrupt:
    print '^C received, shutting down server'
    server.socket.close()

if __name__ == '__main__':
  main(sys.argv[1:])

