#!/usr/bin/env python
import liblo
import curses
import time
import sys, os
from math import *
from peach import *
from e.elib import sort_natural
    
def usage():
    print """
%s [oscport] [options]

By default the OSC port 31415 is used. This value is also preconfigured in the accompannying utilities
for Supercollider and for the command-line (SendOSC in Supercollider, midi2oscprint.py) so 
its probably a good idea to leave it as it is. 

OPTIONS:

--sort             sort the lines each time a new label is found (default=True)
--nosort           do not sort the lines each automatically
--autocalibrate    calibrate faders acording to the received values (default=True). VUs are never autocalibrated
--noautocalibrate  do not autocalibrate faders.

Monitor the oscport and print messages
--------------------------------------

Commands supported:

path            args
---------------------------
/print          label value
/print/config   "linenum" label line   | set the y position 
                                       | this will have no effect if --sort was specified
                "fader" label min max  | either creates a fader widget with the given label
                                       | or converts the line to a fader 
                "range" label min max  | this is a synonim for "fader"
                "remove" label         | remove the line if it exists
                "transform" label func | apply the given transform to the value before printing it
                                       | possible transforms are:
                                       |     * m2n      --> convert a midinote to its note representation
                                       |     * f2m      --> convert frequency to midinote
                                       |     * db2amp   --> convert dB to linear amp
                                       |     * amp2db   --> convert linear amp to dB 
                                       |     * f2n      --> frequency to note representation
/print/fader    label value [min max]  | print the value and convert the line to a fader 
                                       | if it was not already. 
/print/vu       label value            | value is a linear amp (0-1). It will be converted to dB
                                       | and shown as a VU meter with a range of -75 to 0 dB
/print/clear    --                     | remove all lines
/print/sort     --                     | sort the lines

                
 
""" % os.path.split(sys.argv[0])[1]
    sys.exit(0)

autosort = True

if '--help' in sys.argv:
    usage()

def getarg(arg):
    if arg in sys.argv:
        out = True
        sys.argv.remove(arg)
    else:
        out = False
    return out

if getarg('--sort'):
    autosort = True
if getarg('--nosort'):
    autosort = False
if getarg('--autocalibrate'):
    autocalibrate = True
if getarg('--noautocalibrate'):
    autocalibrate = False

try:
    PORT = int(sys.argv[1])
except IndexError:
    PORT = 31415

screen = curses.initscr()
curses.start_color()
curses.use_default_colors()
curses.init_color(curses.COLOR_BLACK, 113, 113, 113)

curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
curses.init_pair(curses.COLOR_YELLOW, curses.COLOR_YELLOW, curses.COLOR_BLACK)
curses.init_pair(curses.COLOR_GREEN, curses.COLOR_GREEN, curses.COLOR_BLACK)
curses.init_pair(curses.COLOR_BLUE, curses.COLOR_BLUE, curses.COLOR_BLACK)

screen.nodelay(1)
curses.noecho()
screen.keypad(1)

screeny, screenx = screen.getmaxyx()

LABELWIDTH = 20
CURSOR_EXCEPTIONS = [
    lambda label: any(label.startswith(s) for s in ["__", "MIDI/", "/firmata"]),
    lambda label: any(label.endswith(s) for s in ["_"])
]

COLORS = {
    curses.COLOR_GREEN : lambda label: any(label.startswith(s) for s in ["MIDI/", "/firmata"]),
    curses.COLOR_BLUE  : lambda label: label.startswith("__")
}

def get_color(label):
    for color, func in COLORS.iteritems():
        if func(label):
            return color
    return None

def label_show_cursor(label):
    if any(func(label) for func in CURSOR_EXCEPTIONS):
        return False
    return True

def amp2vu(x):
    return amp2db(x*x)

def normalize_label(label):
    return label.rstrip("_ ")

class Line(object):
    def __init__(self, label, line, value, isfooter=False):
        self.label = label
        self._labelstr = normalize_label(label).ljust(LABELWIDTH)[:LABELWIDTH]
        self._line = line
        self._value = value
        self.needsrefresh = True
        self._transforms = []
        self._time_last_update = 0
        self.show_cursor = not isfooter and label_show_cursor(label)
        self.isfooter = isfooter
        self.color = get_color(label)
    @property
    def value(self):
        return self._value
    @value.setter
    def value(self, newvalue):
        if self._transforms:
            for func in self._transforms:
                newvalue = func(newvalue)
        if newvalue != self._value:
            self._value = newvalue
            self.needsrefresh = True
            self._time_last_update = time.time()
    @property
    def line(self):
        return self._line
    @line.setter
    def line(self, newlinenumber):
        self._line = newlinenumber
        self.needsrefresh = True
    def __repr__(self):
        if self.label:
            return "%s: %s" % (self._labelstr, tostr(self.value))
        else:
            return self.value

class Footer(Line):
    def __repr__(self):
        return self.value

def clip(x, x0, x1):
    return max(min(x, x1), x0)

class LineFader(Line):
    def __init__(self, label, line, value, minvalue=0, maxvalue=1, width=30, autocalibrate=True):
        Line.__init__(self, label, line, value)
        self.set_range(minvalue, maxvalue)
        self.width = width
        self.autocalibrate = autocalibrate
        self.unit = ""
        self.posttransforms = None
    @Line.value.setter
    def value(self, value):
        if self._transforms:
            for func in self._transforms:
                value = func(value)
        if value != self._value:
            if self.autocalibrate:
                if self.autocalibrate == "up":
                    if value > self.maxvalue:
                        self.maxvalue =value
                else:
                    if value > self.maxvalue:
                        self.maxvalue =value
                    elif value < self.minvalue:
                        self.minvalue = value
            else:
                value = clip(value, self.minvalue, self.maxvalue)
            self._value = value
            self.needsrefresh = True
    def set_range(self, minvalue, maxvalue):
        self.minvalue = minvalue
        self.maxvalue = maxvalue
    def get_n(self):
        try:
            n = int((self.value - self.minvalue) / (self.maxvalue - self.minvalue) * self.width + 0.5)
        except OverflowError:
            n = 0
        except ValueError:
            n = 0
        return n

    def __repr__(self):
        n = self.get_n()
        fader = "=" * n + " " * (self.width - n)
        return "%s:  %s %s [%s]" % (self._labelstr, str(round(self.value, 2)).ljust(7), self.unit, fader)

class VuFader(LineFader):
    def __init__(self, *args, **kws):
        LineFader.__init__(self, *args, **kws)
        self.width = 36
        self.autocalibrate = False
        self._transforms = [amp2db]
        self.minvalue = -72
        self.maxvalue = 0
        self.unit = "dB"
        self.show_cursor = False
        self.color = curses.COLOR_YELLOW

def percent(x):
    return int(x * 100)

class PercentFader(LineFader):
    def __init__(self, *args, **kws):
        LineFader.__init__(self, *args, **kws)
        self.autocalibrate = False
        self._transforms = [percent]
        self.minvalue = 0
        self.maxvalue = 100
        self.unit = "%"

def tostr(val):
    if isinstance(val, basestring):
        return val
    if val <= 1e-12:
        x = 0
    else:
        x = max(0, int(log(val+1e-12, 10)))
    try:
        rst = val - int(val)
    except OverflowError:
        return str(val)
    if rst < 1e-12:
        val = int(val)
    else:
        aftercomma = 7 - x
        val = round(val, aftercomma)
    return " "*(4-x) + str(val)

TRANSFORMS = {
    'm2n':lambda value:m2n(float(value)),
    'ampdb': lambda value:clip(amp2db(float(value)), -90, 0),
    'amp2db': lambda value:clip(amp2db(float(value)), -90, 0),
    'f2n': f2n
}

class Handler:
    def __init__(self, autosort=autosort):
        self.maxy = screeny
        self.initlines()
        self.lastline = 0
        self.needsrefresh = True
        self.autosort = autosort
        self._cursor = 0
    def initlines(self):
        info = '__info__'
        footer = Footer("__info__", self.maxy-1, 'OSC port: %d | (q)uit | (r)efresh | (s)ort | (c)lear' % PORT, isfooter=True)
        self.lines = {info: footer}
        self.footer = footer
    def handle(self, label, values, linenum=None):
        if len(values) > 1:
            value = " ".join(tostr(v) for v in values)
        else:
            # valuestr = str(values[0])
            value = values[0]
        line = self.lines.get(label)
        if not line:
            linenum = linenum if linenum is not None else self.newline()
            self.lines[label] = line = Line(label, linenum, value)
            if self.autosort:
                self.sort_lines()
        else:
            line.value = value
        # line.needsrefresh = True
        self.needsrefresh = True
        return line
    def newline(self):
        out = self.lastline
        self.lastline += 1
        return out
    def sort_lines(self):
        lines = [(label, line) for label, line in self.lines.iteritems() if not line.isfooter]
        # lines.sort()
        lines = sort_natural(lines, key=lambda elem:elem[0])
        for i, (label, line) in enumerate(lines):
            line.line = i
            line.needsrefresh = True
        self.needsrefresh = True
    def refresh(self, force=False):
        if force: 
            screen.clear()
        if self.needsrefresh or force:
            cursor = self._cursor
            for line in self.lines.values():
                if line.needsrefresh or force:
                    screen.move(line.line, LABELWIDTH)
                    screen.clrtoeol()
                    if line.color is not None:
                        screen.addstr(line.line, 2, str(line), curses.color_pair(line.color))
                    else:
                        screen.addstr(line.line, 2, str(line))
                    if line.show_cursor:
                        cursor = line.line
                    line.needsrefresh = False
            if cursor != self._cursor:
                screen.addstr(self._cursor, 0, " ")
                self._cursor = cursor
                screen.addstr(cursor, 0, ">", curses.color_pair(1))

            screen.move(self.lastline+1, 0)
            screen.refresh()
            self.needsrefresh = False
    def lineconfig(self, label, method, args):
        func = getattr(self, "lineconfig_" + method)
        if func is not None:
            func(label, *args)
    def lineconfig_linenum(self, label, num):
        line = self.getline(label)
        if num > self.lastline:
            self.lastline = num
        else:
            # is there someone with this line
            oldline = [l for l in self.lines.itervalues() if l.line == num]
            if oldline:
                oldline = oldline[0]
                oldline.line = line.line
            line.line = num
        
        self.refresh(force=True)
    def getline(self, label):
        line = self.lines.get(label)
        if line is None:
            line = self.handle(label, "?")
        return line
    def lineconfig_range(self, label, minvalue, maxvalue):
        return self.lineconfig_range(label, minvalue, maxvalue)
    def lineconfig_remove(self, label):
        self.lines.pop(label, None)
    def lineconfig_transform(self, label, functionname):
        func = TRANSFORMS.get(functionname)
        line = self.getline(label)
        if line and func:
            line._transforms.append(func)
            line.needsrefresh = True
            self.needsrefresh=True
    def lineconfig_fader(self, label, minvalue, maxvalue):
        line = self.getline(label)
        if isinstance(line, LineFader):
            line.minvalue = minvalue
            line.maxvalue = maxvalue
            line.needsrefresh = True
        else:
            fader = LineFader(label, line.line, line.value, minvalue, maxvalue)
            self.lines[label] = fader
        self.needsrefresh=True
    def newfader(self, label, linenum, minvalue, maxvalue):
        if linenum == -1:
            linenum = self.newline()
        fader = LineFader(label, linenum, minvalue, minvalue, maxvalue)
        self.lines[label] = fader
        self.refresh(force=True)
    def printasfader(self, label, value, minvalue=None, maxvalue=None):
        line = self.getline(label)
        if isinstance(line, LineFader):
            line.value = value
            self.needsrefresh=True
        else:
            line = LineFader(label, line.line, value)
            if minvalue:
                line.minvalue = minvalue
            if maxvalue:
                line.maxvalue = maxvalue
            self.lines[label] = line
        self.needsrefresh=True
    def printaspercent(self, label, value):
        line = self.getline(label)
        if isinstance(line, PercentFader):
            line.value = value
        else:
            line = PercentFader(label, line.line, value)
            self.lines[label] = line
        self.needsrefresh=True
        
    def printasvu(self, label, value):
        line = self.getline(label)
        if isinstance(line, VuFader):
            line.value = value
        else:
            vufader = VuFader(label, line.line, value)
            self.lines[label] = vufader
        self.needsrefresh=True
    def clear(self, *args, **kws):
        self.initlines()
        self.refresh(force=True)

handler = Handler()

def printfunc(path, values):
    handler.handle(values[0], values[1:])
def lineconfig(path, values):
    method, label = values[0:2]
    args = values[2:]
    handler.lineconfig(label, method, args)
def defaultfunc(path, values):
    handler.handle(path, values)

s = liblo.Server(port=31415)
s.add_method('/print', typespec=None, func=printfunc)

s.add_method('/print/lineconfig', typespec=None, func=lineconfig)
s.add_method('/print/config', typespec=None, func=lineconfig)
s.add_method('/print/fader', typespec=None, func=lambda path, values: handler.printasfader(*values))
s.add_method('/print/vu', typespec=None, func=lambda path, values: handler.printasvu(*values))
s.add_method('/print/clear', typespec=None, func=handler.clear)
s.add_method('/print/sort', typespec=None, func=lambda *args, **kws: handler.sort_lines())
s.add_method('/print/percent', typespec=None, func=lambda path, values: handler.printaspercent(*values))
s.add_method(None, None, func=defaultfunc)

def exit(msg=""):
    global s
    del s
    curses.endwin()
    print msg
    sys.exit(0)

if __name__ == '__main__':
    try:
        screen.refresh()
        R = ord("r")
        S = ord("s")
        Q = ord("q")
        C = ord("c")
        recv = s.recv
        getch = screen.getch
        REFRESH = curses.KEY_REFRESH
        handler_refresh = handler.refresh
        while True:
            c = getch()
            if   c == Q:  # (q)uit
                exit()
            elif c == R:  # (r)efresh
                curses.endwin()
                screen = curses.initscr()
                maxy, maxx = screen.getmaxyx()
                handler.footer.line = maxy - 1
                handler.refresh(force=True)
            elif c == S:  # (s)ort
                handler.sort_lines()
                handler.refresh(force=True)
            elif c == C:  # (c)lear
                handler.clear()
            recv(50)
            if handler.needsrefresh:
                handler_refresh()
    except KeyboardInterrupt:
        exit()
    
        
