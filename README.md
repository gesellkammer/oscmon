OSCMON
------

A set of utilities to monitor and interact with programs using OSC

At this point, a primitive interaction with Supercollider is available

oscprint.py   
===========

A terminal-based logging utility.

### Supercollider
    
    // This will send the value whenever it is triggered to the 
    // OSC address 31415, which is the default address of oscprint.py.
    // Each new label will be displayed in an ad-hoc gui.
    { 
        SinOsc.ar(0.1) !> A2K.kr(_) !> SendOSC.print(_, Impulse.kr(10), 'sine'); 
    }.play;

    // or, more general: send the amplitude to the osc port 31415 (the default here)
    // and print it each time an onset is detected
    {
        var source = SoundIn.ar(0);
        var amp = Amplitude.kr(source);
        source !> FFTL(_, 1024) !> Onsets.kr(_) !> SendOSC.kr(amp, _, 31415, '/print', 'onset');
    }

firmatasend.py
==============

Listens to a firmata serial connection and sends the data either to OSC, MIDI or both

midi2oscprint.py
================

This is a little utility to monitor midi from inside oscprint.py
It sends all midi messages from all connected sources to 
oscprint under the namespace MIDI. It makes it easier than
switching to the midi monitor to see where something is comming from


