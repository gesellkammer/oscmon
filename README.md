OSCMON
------

A set of utilities to monitor and interact with programs using OSC

At this point, a primitive interaction with Supercollider is available

### Supercollider

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

This will send the value whenever it is triggered to the OSC address 31415, which is the default address of oscprint.py. There each new label will be displayed in an ad-hoc gui.

