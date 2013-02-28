OSCMON
------

A set of utilities to monitor and interact with programs using OSC

At this point, a primitive interaction with Supercollider is available

### Supercollider

    { 
        SinOsc.ar(0.1) !> A2K.kr(_) !> SendOsc.print(_, Impulse.kr(10), 'sine' 
    }.play;

This will send the value whenever it is triggered to the OSC address 31415, which is the default address of oscprint.py. There each new label will be displayed in an ad-hoc gui.

