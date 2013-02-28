#!/usr/bin/env python
import liblo
import curses
import time
import sys, os

def usage():
    print """
%s [oscport=31415]

Monitor the oscport and print messages
--------------------------------------

Commands supported:

    path       args
    ...........................
    /print     label value
""" % os.path.split(sys.argv[0])[1]
    sys.exit(0)

if '--help' in sys.argv:
    usage()

try:
    PORT = int(sys.argv[1])
except IndexError:
    PORT = 31415

screen = curses.initscr()
screen.nodelay(1)
curses.noecho()

LABELWIDTH = 16

class Line:
    def __init__(self, label, line, value):
        self.label = label
        self._labelstr = label.ljust(LABELWIDTH)
        self.line = line
        self.value = value
    def __repr__(self):
        return "%s: %s" % (self._labelstr, self.value)

class Handler:
    def __init__(self):
        self.lines = {}
        self.lastline = 0
        self.needsrefresh = False
    def handle(self, label, values):
        s = " ".join(map(str, values))
        line = self.lines.get(label)
        if not line:
            self.lines[label] = line = Line(label, self.newline(), s)
        else:
            line.value = s
        line.needsrefresh = True
        self.needsrefresh = True

    def newline(self):
        out = self.lastline
        self.lastline += 1
        return out
    def refresh(self):
        if self.needsrefresh:
            for line in self.lines.values():
                if line.needsrefresh:
                    screen.move(line.line, LABELWIDTH)
                    screen.clrtoeol()
                    # screen.addstr(line.line, LABELWIDTH, "                           ")
                    screen.addstr(line.line, 1, str(line))
            screen.move(self.lastline+1, 0)
            screen.refresh()
            self.needsrefresh = False

handler = Handler()

def printfunc(path, values):
    label = values[0]
    if isinstance(label, basestring):
        handler.handle(label, values[1:])

s = liblo.Server(port=31415)
s.add_method('/print', typespec=None, func=printfunc)

def exit():
    global s
    del s
    curses.endwin()
    sys.exit(0)

if __name__ == '__main__':
    try:
        screen.refresh()
        while True:
            s.recv(50)
            handler.refresh()
    except KeyboardInterrupt:
        exit()
