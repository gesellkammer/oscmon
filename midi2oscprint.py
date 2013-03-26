#!/usr/bin/env python
import rtmidi2 as rtmidi

midiin = rtmidi.MidiInMulti().open_ports("*")
print "Listening to:"
for port in midiin.get_openports():
    print "   - ", midiin.get_port_name(port)

from liblo import send as oscsend

OSCPORT = 31415

def callback(src, msg, t):
    msgt, ch = rtmidi.splitchannel(msg[0])
    val1 = int(msg[1])
    val2 = int(msg[2])
    msgtstr = rtmidi.msgtype2str(msgt).ljust(6)
    oscsend(31415, "/print", "MIDI/" + src, msgtstr, ch, val1, val2)

midiin.set_qualified_callback(callback)

while True:
    a = raw_input("press q and ENTER to exit ")
    if a == "q":
        break


    

    
