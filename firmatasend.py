#!/usr/bin/env python
# stdlib
import glob
import sys
import time
import optparse

OSC_SC    = 57121
OSC_PRINT = 31415

try: 
	import pip
	PIP = True
except ImportError:
	PIP = False

def print_pip_installation():
	print """
	In order to easyily install the requirements, you need to install pip.
	At the Terminal, enter:

    $ curl -O https://raw.github.com/pypa/pip/master/contrib/get-pip.py
    $ python get-pip.py
	"""

try:
	import serial
except ImportError:
	print "pyserial was not found. This is a requirement for serial communication with Arduino."
	if not PIP:
		print_pip_installation()
	print "\n$ pip install pyserial"
	sys.exit(0)
	
try:
	import pyfirmata
except ImportError:
	print """pyfirmata is needed in order to communicate with any Arduino board."""
	if not PIP:
		print_pip_installation()
	print """
At the terminal:

    $ pip install pyfirmata

pyfirmata: https://bitbucket.org/fab/pyfirmata
"""
	sys.exit(0)

try:
	import liblo
	from liblo import send
except ImportError:
	print """
liblo was not found. This is a library to send OSC, and without it you will not be able
to send OSC. 

In order to have a working installation of liblo for python, you need to install first the 
C library 'liblo' and then its python bindings

	$ git clone git://gitorious.org/liblo/mainline.git
	$ cd mainline
	$ ./configure
	$ make
	$ sudo make install

Then install the python bindings:

    $ git clone git@github.com:gesellkammer/pyliblo-.git
    $ cd pyliblo-
    $ python setup.py install

"""

try:
	import rtmidi2 as rtmidi
	MIDIAVAILABLE = True
except ImportError:
	MIDIAVAILABLE = False
	print """
rtmidi2 was not found. MIDI communication will not be available

In order to be able to use MIDI, install rtmidi2. 
Assuming that you have git installed (if not, install that first)

    $ git clone git@github.com:gesellkammer/rtmidi2.git
    $ cd rtmidi2
    $ python setup.py install

NB: rtmidi2 is a python extension written in C++, so you will need a working
gcc. If you are in OSX, you should have installed the Developer Tools 
	"""


osc_analog_paths  = ["/firmata/a%d" % i for i in range(12)]
osc_digital_paths = ["/firmata/d%d" % i for i in range(20)]

def isiterable(obj):
	return hasattr(obj, '__iter__') and not isinstance(obj, basestring)

def get_port():
	devs = glob.glob("/dev/tty.usb*")
	if len(devs) == 0:
		print "No arduino board found! Exiting."
		sys.exit(0)
	if len(devs) > 1:
		print "Available Ports"
		for i, dev in enumerate(devs):
			print "[ %d ] %s" % (i, dev)
		print 
		port = raw_input("Select a port by entering the number: ")
		portnum = int(port)
		dev = devs[portnum]
	else:
		dev = devs[0]
	return dev

def get_arduino():
	dev = get_port()
	print "\nusing port: %s" % dev
	return pyfirmata.Arduino(dev)

def linlin(x, x0, x1, y0, y1):
	return (x - x0) / (x1 - x0) * (y1 - y0) + y0

def normalize(x, x0, x1):
	return (x - x0) / (x1 - x0)
	
def receive(callback, analog_pins=[0], digital_pins=range(5, 9), wait=20, async=False, echo=False, auto_calibrate=False):
	"""
	callback: a function expecting (pintype, pinnumber, value), where pintype is 'A' or 'D'
	"""
	a = get_arduino()
	ANALOG_PINS = 6
	if analog_pins == 'all':
		analog_pins = range(6)
	elif analog_pins is None:
		analog_pins = []
	if digital_pins == 'all':
		digital_pins = range(14)
	elif digital_pins is None:
		digital_pins = []
	# digital_pins = [p + ANALOG_PINS for p in digital_pins]
	apaths = ["/firmata/a%d" % i for i in analog_pins]
	dpaths = ["/firmata/d%d" % i for i in digital_pins]
	amins = [1] * 20
	amaxs = [1e-12] * 20

	time_sleep = time.sleep
	for apin in analog_pins:
		a.analog[apin].enable_reporting()
	for dpin in digital_pins:
		pin = a.digital[dpin]
		pin.mode = pyfirmata.INPUT
		pin.enable_reporting()
	print "listening... (press CTRL-C to stop)"
	lasttime = time.time()
	if async:
		raise ValueError("async is buggy at the moment, use sync")
		# use the iterator (creates another thread)
		it = pyfirmata.util.Iterator(a)
		it.start()
		try:
			while True:
				for i, apin in enumerate(analog_pins):
					value = a.analog[apin].read()
					if value is not None:
						if auto_calibrate:
							if value < amins[apin]:
								amins[apin] = value
							elif value > amaxs[apin]:
								amaxs[apin] = value
							amin = amins[apin]

							# value = linlin(value, amins[apin], amaxs[apin], 0, 1)
							value = (value - amin) / (amaxs[apin] - amin)
						callback('A', apin, value)
						if echo: 
							print "A%d: " % apin, value
				for i, dpin in enumerate(digital_pins):
					value = a.digital[dpin].read()
					if value is not None:
						value = 1 if str(value) == 'True' else 0
						callback('D', dpin, value)
						if echo: 
							print "D%d: " % dpin, value
				a.pass_time(wait)
		except KeyboardInterrupt:
			a.exit()
	else:	
		# sync: no iterator
		wait = wait/1000.
		try:
			a_iterate = a.iterate
			apins = [a.analog[apin] for apin in analog_pins]
			while True:
				a_iterate()
				t = time.time()
				if t - lasttime > wait:
					lasttime = t
					for apin in apins:
						value = apin.read()
						pin_number = apin.pin_number
						if value is not None:
							if auto_calibrate:
								if value < amins[pin_number]:
									amins[pin_number] = value
								elif value > amaxs[pin_number]:
									amaxs[pin_number] = value
								amin = amins[pin_number]
								value = (value - amin) / (amaxs[pin_number] - amin)
							callback('A', pin_number, value)
							if echo: 
								print "A%d: " % pin_number, value
					for dpin in digital_pins:
						value = a.digital[dpin].read()
						if value is not None:
							value = 1 if str(value) == 'True' else 0
							callback('D', dpin, value)
							if echo: 
								print "D%d: " % dpin, value
		except KeyboardInterrupt:
			a.exit()

def sendosc_callback(target=OSC_SC, analog_pins=[0], digital_pins=range(5, 9)):
	"""
	returns a callback which sends data to the target. See 'receive'
	NB: firmata reports the information normalized in the range 0-1
	the path is /firmata/porttype+portnumber data  (Example: /firmata/a0 0.04)

	target: either a port number or a tuple (host, port)
	analog_pins: a list of integers, 'all' or None
	digital_pins: idem
	wait: how long to wait between readings, in ms

	Example
	-------

	callback = sendosc_callback(57121)               # will send osc to port 57121 on the local maschine
	callback = sendosc_callback('localhost', 31415)  # will send osc to port 31415 on the local maschine
	callback = sendosc_callback('192.168.1.104', 57121) # will send osc to another maschine
	"""
	def callback(pintype, pinnumber, value):
		path = osc_analog_paths[pinnumber] if pintype == 'A' else osc_digital_paths[pinnumber]
		send(target, path, value)
	return callback
def sendosc_many_callback(targets, analog_pins=[0], digital_pins=range(5, 9)):
	"""
	see sensosc_callback. this version can send to many targets at once
	"""
	def callback(pintype, pinnumber, value):
		path = osc_analog_paths[pinnumber] if pintype == 'A' else osc_digital_paths[pinnumber]
		for target in targets:
			send(target, path, value)
	return callback
def sendosc(target=57121, analog_pins=[0], digital_pins=range(5, 9), wait=20, async=False, echo=False):
	"""
	target can be a list of targets
	"""
	if not isiterable(target):
		callback = sendosc_callback(target=target, analog_pins=analog_pins, digital_pins=digital_pins)
	else:
		callback = sendosc_many_callback(targets=target, analog_pins=analog_pins, digital_pins=digital_pins)
	receive(callback, analog_pins, digital_pins, wait, async, echo)

def sendmidi_callback(port='FIRMATA', channel=7, analog_pins=[0], digital_pins=range(5, 9), analogoffset=100, digitaloffset=30):
	"""
	A0 -> CC100
	A1 -> CC101
	...

	D0 -> CC30
	D1 -> CC31
	...
	"""
	if not MIDIAVAILABLE:
		raise RuntimeError("midi is not available!")
	o = rtmidi.MidiOut()
	if port in o.ports:
		o.open_port(port)
	else:
		print "'%s' is not an existing port. A virtual port will be created." % port
		o.open_virtual_port(port)	
	def callback(pintype, pinnumber, value):
		if pintype == 'A':
			value = max(min(int(value * 127 + 0.5), 127), 0) # clip it to 0-127
			o.send_cc(channel, pinnumber + analogoffset, value)
		else:
			o.send_cc(channel, pinnumber + digitaloffset, value * 127)
	return callback
def sendmidi(port='FIRMATA', channel=7, analog_pins=[0], digital_pins=range(5, 9), analogoffset=100, digitaloffset=30, wait=20, async=False, echo=False):
	"""
	tries to connect to devicename to send the data. if device does not exists, 
	creates a virtual device with the given device name and midi is sent to this device.
	To listen to this virtual device, either use it as your input in your host, or use a programm like MIDIPatchbay

	NB: do not ask for analog pins that are not connected, this will send spurious data down the line
	and can tax the midi pipeline in your maschine too much

	Example
	-------

	# will create a virtual port called FIRMATA, send the analog data to CC100-CC105 (if your Arduino has 6 analog pins)
	sendmidi('FIRMATA', channel=7, analog_pins='all', digital_pins=None)
	"""
	if not MIDIAVAILABLE:
		raise RuntimeError("midi is not available!")
	callback = sendmidi_callback(port, channel, analog_pins, digital_pins, analogoffset, digitaloffset)
	receive(callback, analog_pins, digital_pins, wait, async, echo)	

def send_osc_and_midi(osctarget=57121, midiport='FIRMATA', channel=7, analog_pins=[0], digital_pins=range(5, 9), wait=20, async=False, echo=False):
	osccallback = sendosc_callback(target=osctarget, analog_pins=analog_pins, digital_pins=digital_pins)
	midicallback = sendmidi_callback(midiport, channel, analog_pins, digital_pins)
	def callback(t, n, v):
		osccallback(t, n, v)
		midicallback(t, n, v)
	receive(callback, analog_pins, digital_pins, wait, async, echo)		

def get_midiports():
	if MIDIAVAILABLE:
		return rtmidi.MidiOut().ports

def select_midiport():
	if not MIDIAVAILABLE:
		raise RuntimeError("midi not available")
	ports = get_midiports()
	while True:
		for i, port in enumerate(ports):
			print "[ %d ] %s" % (i + 1, port)
		print
		n = raw_input("Select a midi port by number (1-%d): " % len(ports))
		try:
			n = int(n) - 1
			return ports[n]
		except ValueError:
			print "could not understand the answer, try again or press CTRL-C to exit"

if __name__ == '__main__':
	parser = optparse.OptionParser()
	parser.add_option("-o", "--osc", dest="osctarget", help="send data via osc in this or other host. Many comma-separated targets may be specified. Example: --osc 57121 or --osc localhost:57121 or --osc 127.0.0.1:57121,192.168.1.104:31415")
	parser.add_option("-m", "--midi", dest="midiport", help="send data via midi to the given existing or virtual port (a virtual port will be created if the given port does not exist). use `--midi select` to select from available ports or `--midi 0` to send to default port")
        parser.add_option("-a", "--analog", dest="analogpins", help="The analog pins to read. Either 'all' or a ':' delimited list of pins. Example: --analog 1:3:4", default=None)
	parser.add_option("-d", "--digital", dest="digitalpins", help="see --analog")
	parser.add_option("-w", "--wait", dest="wait", help="wait this amount of ms between each read", default=20)
	parser.add_option("-c", "--midichannel", dest="midichannel", default=7)
	parser.add_option("-e", "--echo", help="print the received data to stdout", nargs=0)
	options, args = parser.parse_args()
	osctarget = None
	async = False
	echo = options.echo is not None
	if options.osctarget:
		osctarget = options.osctarget.split(',')
		if len(osctarget) == 1:
			osctarget = osctarget[0]
	analogpins = options.analogpins
	if analogpins is not None:
		analogpins = map(int, analogpins.split(':'))
	digitalpins = options.digitalpins
	if digitalpins is not None:
		digitalpins = map(int, digitalpins.split(':'))	
	if analogpins is None and digitalpins is None:
		print "\nERROR: No pins selected to listen to. Use something like `--analog 0` to listen to the specified pin\n"
		sys.exit(0)
	if options.midiport is not None:
		if options.midiport in (-1, 'select'):
			midiport = select_midiport()
			print "sending data to ", midiport
		elif isinstance(options.midiport, int):
			try:
				midiport = get_midiports()[options.midiport]
			except IndexError:
				midiport = select_midiport()
		else:
			midiport = options.midiport
		if osctarget is not None:
			send_osc_and_midi(osctarget=osctarget, midiport=midiport, channel=options.midichannel, 
				analog_pins=analogpins, digital_pins=digitalpins, wait=options['wait'], async=async, echo=echo)
		else:
			sendmidi(midiport, channel=options.midichannel, 
				analog_pins=analogpins, digital_pins=digitalpins, wait=options.wait, async=async, echo=echo)
	elif osctarget:
		sendosc(target=osctarget, analog_pins=analogpins, digital_pins=digitalpins, wait=options.wait, async=async, echo=echo)
	else:
		print "No target action was found (either --osc or --midi). Use something like --osc 57121"
		sys.exit(0)
