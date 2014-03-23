#!/usr/bin/env python2
import sys
import msr
import tty
import termios

if len(sys.argv) < 2:
    print "USAGE: ./msrtool.py <SERIALDEVICE>"
    sys.exit()

dev = msr.msr(sys.argv[1])


def mode_read(dev):
    print "[r] swipe card to read, ^C to cancel"
    t1, t2, t3 = dev.read_tracks()
    print "Track 1:", t1
    print "Track 2:", t2
    print "Track 3:", t3


def mode_compare(dev):
    print "[r] swipe card to read, ^C to cancel"
    t1, t2, t3 = dev.read_tracks()
    print "Track 1:", t1
    print "Track 2:", t2
    print "Track 3:", t3
    print "[r] swipe card to compare, ^C to cancel"
    b1, b2, b3 = dev.read_tracks()
    if b1 == t1 and b2 == t2 and t3 == t3:
        print "Compare OK"
    else:
        print "Track 1:", b1
        print "Track 2:", b2
        print "Track 3:", b3
        print "Compare FAILED"


def bulk_compare(dev):
    print "[r] swipe card to read, ^C to cancel"
    t1, t2, t3 = dev.read_tracks()
    print "Track 1:", t1
    print "Track 2:", t2
    print "Track 3:", t3
    while True:
        print "[r] swipe card to compare, ^C to cancel"
        try:
            b1, b2, b3 = dev.read_tracks()
        except KeyboardInterrupt:
            break
        if b1 == t1 and b2 == t2 and t3 == t3:
            print "Compare OK"
        else:
            print "Track 1:", b1
            print "Track 2:", b2
            print "Track 3:", b3
            print "Compare FAILED"


def mode_erase(dev):
    print "[e] swipe card to erase all tracks, ^C to cancel"
    dev.erase_tracks(t1=True, t2=True, t3=True)
    print "Erased."


def mode_copy(dev):
    print "[c] swipe card to read, ^C to cancel"
    t1, t2, t3 = dev.read_tracks()
    print "Track 1:", t1
    print "Track 2:", t2
    print "Track 3:", t3
    kwargs = {}
    if t1 is not None:
        kwargs['t1'] = t1[1:-1]
    if t2 is not None:
        kwargs['t2'] = t2[1:-1]
    if t3 is not None:
        kwargs['t3'] = t3[1:-1]
    print "[c] swipe card to write, ^C to cancel"
    dev.write_tracks(**kwargs)
    print "Written."


def bulk_copy(dev):
    print "[c] swipe card to read, ^C to cancel"
    t1, t2, t3 = dev.read_tracks()
    print "Track 1:", t1
    print "Track 2:", t2
    print "Track 3:", t3
    kwargs = {}
    if t1 is not None:
        kwargs['t1'] = t1[1:-1]
    if t2 is not None:
        kwargs['t2'] = t2[1:-1]
    if t3 is not None:
        kwargs['t3'] = t3[1:-1]
    while True:
        try:
            print "[c] swipe card to write, ^C to cancel"
            dev.write_tracks(**kwargs)
            print "Written."
        except KeyboardInterrupt:
            break
        except Exception as e:
            print "Failed. Error:", e
            break


def mode_write(dev):
    print "[w] Input your data. Enter for not writing to a track."
    kwargs = {}
    print "Track 1:",
    t1 = raw_input().strip()
    print "Track 2:",
    t2 = raw_input().strip()
    print "Track 3:",
    t3 = raw_input().strip()
    if t1 != "":
        kwargs['t1'] = t1
    if t2 != "":
        kwargs['t2'] = t2
    if t3 != "":
        kwargs['t3'] = t3
    print "[w] swipe card to write, ^C to cancel"
    dev.write_tracks(**kwargs)
    print "Written."


def bulk_write(dev):
    print "[w] Input your data. Enter for not writing to a track."
    kwargs = {}
    print "Track 1:",
    t1 = raw_input().strip()
    print "Track 2:",
    t2 = raw_input().strip()
    print "Track 3:",
    t3 = raw_input().strip()
    if t1 != "":
        kwargs['t1'] = t1
    if t2 != "":
        kwargs['t2'] = t2
    if t3 != "":
        kwargs['t3'] = t3
    while True:
        print "[w] swipe card to write, ^C to cancel"
        try:
            dev.write_tracks(**kwargs)
        except KeyboardInterrupt:
            break
        print "Written."


def settings(dev):
    print """
Settings
(h) hico     (l) loco     (q) quit
"""
    while True:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        if ch == 'q':
            break
        elif ch == 'h':
            dev.set_coercivity(dev.hico)
            print "Hico set."
        elif ch == 'l':
            dev.set_coercivity(dev.loco)
            print "Loco set."


def quit(dev):
    print "[q] bye."
    sys.exit(0)


while True:
    print """
What do you want to do?
(r) read         (w) write        (c) copy
(R) bulk read    (W) bulk write   (C) bulk copy
(m) compare      (e) erase        (s) settings
(M) bulk compare (E) bulk erase   (q) quit
    """
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    fnc = {
        'r': mode_read,
        'c': mode_copy,
        'C': bulk_copy,
        'e': mode_erase,
        'w': mode_write,
        'W': bulk_write,
        'm': mode_compare,
        'M': bulk_compare,
        's': settings,
        'q': quit,
    }
    if ch in fnc:
        try:
            fnc[ch](dev)
        except KeyboardInterrupt:
            continue
        except Exception as e:
            print "Failed. Error:", e
            continue
    elif ch.lower() in fnc:
        while True:
            try:
                fnc[ch.lower()](dev)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print "Failed. Error:", e
                break
    else:
        print "Method not found."
