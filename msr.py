#!/usr/bin/env python
#
# File: msr.py
# Version: 1.1
# Author: Damien Bobillot (damien.bobillot.2002+msr@m4x.org)
# Licence: GNU GPL version 3
# Compatibility: tested with python 2.7 on Mac OS X, should work with any python installations.
#         
# Driver for the magnetic strip card reader/writer MSR605, and other versions
# 
# june 2011 - 1.0 - First version
# july 2011 - 1.1 - raw read/write, set loco/hico, set density
# 

import time
import serial

# defining the core object
class msr(serial.Serial):
    # protocol
    escape_code = "\x1B"
    end_code = "\x1C"
    
    # for set_coercivity
    hico=True
    loco=False
    
    # for set_bpi
    hibpi=True
    lobpi=False
    
    # for pack/unpack
    track1_map  = " !\"#$%&'()*+`,./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_"
    track23_map = "0123456789:;<=>?"
    parity_map  = [1,0,0,1,0,1,1,0,0,1,1,0,1,0,0,1,0,1,1,0,1,0,0,1,1,0,0,1,0,1,1,0, \
                   0,1,1,0,1,0,0,1,1,0,0,1,0,1,1,0,1,0,0,1,0,1,1,0,0,1,1,0,1,0,0,1]
                  # 1 = count of 1 in index is even, 0 = odd
    rev6bit_map = [0,32,16,48,8,40,24,56,4,36,20,52,12,44,28,60,2,34,18,50,10,42,26,58,6,38,22,54,14,46,30,62, \
                   1,33,17,49,9,41,25,57,5,37,21,53,13,45,29,61,3,35,19,51,11,43,27,59,7,39,23,55,15,47,31,63]
                  # give the reverse bitmap (6 bits) of a the index
    
    def __init__(self, dev_path):
        if dev_path.find("/") == -1: dev_path = "/dev/" + dev_path
        serial.Serial.__init__(self,dev_path,9600,8,serial.PARITY_NONE,timeout=0)
        self.reset()
    
    def __execute_noresult(self, command):
        self.write(msr.escape_code+command)
        time.sleep(0.1)
    
    def __execute_waitresult(self, command, timeout=10):
        # execute
        self.flushInput()
        self.write(msr.escape_code+command)
        time.sleep(0.1)
        
        # get result
        self.timeout=timeout
        result = self.read()
        time.sleep(0.5)
        if result == "": raise Exception("operation timed out")
        self.timeout=0
        result += self.read(1000)
        
        # parse result : status, result, data
        pos = result.rindex(msr.escape_code)
        return result[pos+1], result[pos+2:], result[0:pos]

    def reset(self):
        self.__execute_noresult("a")
    
    @staticmethod
    def __decode_isodatablock(data):
        # header and end
        if data[0:4] != msr.escape_code+"s"+msr.escape_code+"\x01":
            raise Exception("bad datablock : don't start with <ESC>s<ESC>[01]", data)
        if data[-2:] != "?"+msr.end_code:
            raise Exception("bad datablock : don't end with ?<FS>", data)
        
        # first strip
        strip1_start = 4
        strip1_end = data.index(msr.escape_code,strip1_start)
        if strip1_end == strip1_start:
            strip1_end += 2
            strip1 = None
        else:
            strip1 = data[strip1_start:strip1_end]

        # second strip
        strip2_start = strip1_end+2
        if data[strip1_end:strip2_start] != msr.escape_code+"\x02":
            raise Exception("bad datablock : missing <ESC>[02] at position %d" % strip1_end, data)
        strip2_end = data.index(msr.escape_code,strip2_start)
        if strip2_end == strip2_start:
            strip2_end += 2
            strip2 = None
        else:
            strip2 = data[strip2_start:strip2_end]
        
        # third strip
        strip3_start = strip2_end+2
        if data[strip2_end:strip3_start] != msr.escape_code+"\x03":
            raise Exception("bad datablock : missing <ESC>[03] at position %d" % strip2_end, data)
        if data[strip3_start] == msr.escape_code:
            strip3 = None
        else:
            strip3 = data[strip3_start:-2]
        
        return strip1, strip2, strip3
    
    @staticmethod
    def __encode_isodatablock(strip1, strip2, strip3):
        # use empty string if you don't want to set a given strip
        return "\x1bs\x1b\x01"+strip1+"\x1b\x02"+strip2+"\x1b\x03"+strip3+"?\x1C"
    
    @staticmethod
    def __decode_rawdatablock(data):
        # header
        if data[0:4] != msr.escape_code+"s"+msr.escape_code+"\x01":
            raise Exception("bad datablock : don't start with <ESC>s<ESC>[01]", data)
        
        # first strip
        strip1_start = 4
        strip1_end = strip1_start + 1 + ord(data[strip1_start]) # first byte is length
        strip1 = data[strip1_start+1:strip1_end]

        # second strip
        strip2_start = strip1_end+2
        if data[strip1_end:strip2_start] != msr.escape_code+"\x02":
            raise Exception("bad datablock : missing <ESC>[02] at position %d" % strip1_end, data)
        strip2_end = strip2_start + 1 + ord(data[strip2_start])
        strip2 = data[strip2_start+1:strip2_end]
        
        # third strip
        strip3_start = strip2_end+2
        if data[strip2_end:strip3_start] != msr.escape_code+"\x03":
            raise Exception("bad datablock : missing <ESC>[03] at position %d" % strip2_end, data)
        strip3_end = strip3_start + 1 + ord(data[strip3_start])
        strip3 = data[strip3_start+1:strip3_end]

        # trailer
        if data[strip3_end:] != "?"+msr.end_code:
            raise Exception("bad datablock : missing ?<FS> at position %d", strip3_end, data)
                
        return strip1, strip2, strip3

    @staticmethod
    def __encode_rawdatablock(strip1, strip2, strip3):
        # use empty string if you don't want to set a given strip : FIXME doesn't work
        datablock = "\x1bs"
        if strip1 != "":
            datablock += "\x1b\x01"+chr(len(strip1))+strip1
        if strip2 != "":
            datablock += "\x1b\x02"+chr(len(strip2))+strip2
        if strip3 != "":
            datablock += "\x1b\x03"+chr(len(strip3))+strip3
        datablock += "?\x1C"
        return datablock
        #return "\x1bs\x1b\x01"+chr(len(strip1))+strip1+"\x1b\x02"+chr(len(strip2))+strip2+"\x1b\x03"+chr(len(strip3))+strip3+"?\x1C"
    
    @staticmethod
    def pack_raw(data, mapping, bcount_code, bcount_output):
        # data : string to be encoded
        # mapping : string used to convert a character to a code
        # bcount_code : number of bits of character code (without the parity bit)
        # bcount_output : number of bits per output characters
        raw = ""
        lrc = 0       # parity odd
        rem_bits = 0  # remaining bits from previous loop
        rem_count = 0 # count of remaining bits
        for c in data:
            i = mapping.find(c)                      # convert char to code
            if i==-1: i = 0                          # fail to first code if char is not allowed
            lrc ^= i
            i |= msr.parity_map[i] << bcount_code    # add parity bit in front of the code
            rem_bits |= i << rem_count               # concate current code in front of remaining bits
            rem_count += bcount_code+1
            if rem_count >= bcount_output:
                raw += chr(rem_bits & ((1<<bcount_output)-1)) # write the bcount_output bits on the rigth
                rem_bits >>= bcount_output
                rem_count -= bcount_output
        # add one loop for LRC
        lrc |= msr.parity_map[i] << bcount_code
        rem_bits |= lrc << rem_count
        rem_count += bcount_code+1
        if rem_count >= bcount_output:
            raw += chr(rem_bits & ((1<<bcount_output)-1))
            rem_bits >>= bcount_output
            rem_count -= bcount_output
        # add remaining bits, filling with 0
        if rem_count > 0:
            raw += chr(rem_bits)
        return raw
    
    @staticmethod
    def unpack_raw(raw, mapping, bcount_code, bcount_output):
        # raw : string to be encoded
        # mapping : string used to convert a character to a code
        # bcount_code : number of bits of character code (without the parity bit)
        # bcount_output : number of bits per output characters
        # returns : data without trailing nulls, total length including trailing nulls, parity errors, lrc error
        data = ""
        parity_errors = ""
        rem_bits = 0  # remaining bits from previous loop
        rem_count = 0 # count of remaining bits
        lrc = 0       # parity odd
        last_non_null = -1
        for c in raw:
            rem_count += bcount_output               # append next bits on the right
            rem_bits = (rem_bits << bcount_output) | (ord(c) & ((1<<bcount_output)-1))
            while rem_count >= bcount_code+1:
                # get the bcount_code+parity bits on the left
                rem_count -= bcount_code+1
                i = rem_bits >> rem_count
                rem_bits &= ((1<<rem_count)-1)
                
                # reverse bits (assume bcount_code<=6)
                p = i & 0x1 # parity code
                i = msr.rev6bit_map[i>>1] >> (6-bcount_code)
                data += mapping[i]
                if i != 0: last_non_null = len(data)-1
                
                # check parity
                lrc ^= i
                if msr.parity_map[i] == p:
                    parity_errors += " "
                else:
                    parity_errors += "^"
                
        # check LRC (kept at the end of decoded data)
        lrc_error = (lrc != 0)
        
        return data[0:last_non_null+1], len(data), parity_errors[0:last_non_null+1], lrc_error
        
    def read_tracks(self):
        status, _, data = self.__execute_waitresult("r")
        if status != "0":
            raise Exception("read error : %c" % status)
        return self.__decode_isodatablock(data)

    def read_raw_tracks(self):
        status, _, data = self.__execute_waitresult("m")
        if status != "0":
            raise Exception("read error : %c" % status)
        return self.__decode_rawdatablock(data)

    def write_tracks(self, t1="", t2="", t3=""):
        data = self.__encode_isodatablock(t1,t2,t3)
        status, _, _ = self.__execute_waitresult("w"+data)
        if status != "0":
            raise Exception("write error : %c" % status)

    def write_raw_tracks(self, t1, t2, t3):
        data = self.__encode_rawdatablock(t1,t2,t3)
        status, _, _ = self.__execute_waitresult("n"+data)
        if status != "0":
            raise Exception("write error : %c" % status)

    def erase_tracks(self, t1=False, t2=False, t3=False):
        mask = 0
        if t1: mask |= 1
        if t2: mask |= 2
        if t3: mask |= 4
        status, _, _ = self.__execute_waitresult("c"+chr(mask))
        if status != "0":
            raise Exception("erase error : %c" % status)
    
    #def set_leadingzero(self, track13, track2):
    #    status, result, _ = self.__execute_waitresult("o"+chr(bpc1)+chr(bpc2)+chr(bpc3))
    #    if status != "0":
    #        raise Exception("set_bpc error : %c" % status)

    def set_bpc(self, bpc1, bpc2, bpc3):
        status, result, _ = self.__execute_waitresult("o"+chr(bpc1)+chr(bpc2)+chr(bpc3))
        if status != "0":
            raise Exception("set_bpc error : %c" % status)

    def set_bpi(self, bpi1=None, bpi2=None, bpi3=None):
        modes = []
        if bpi1==True: modes.append("\xA1")    # 210bpi
        elif bpi1==False: modes.append("\xA0") # 75bpi
        if bpi2==True: modes.append("\xD2")
        elif bpi2==False: modes.append("\x4B")
        if bpi2==True: modes.append("\xC1")
        elif bpi2==False: modes.append("\xC0")
        for m in modes:
            status, result, _ = self.__execute_waitresult("b"+m)
            if status != "0":
                raise Exception("set_bpi error : %c for %s" % (status,hex(m)))

    def set_coercivity(self, hico):
        if hico:
            status, _, _ = self.__execute_waitresult("x")
        else:
            status, _, _ = self.__execute_waitresult("y")
        if status != "0":
            raise Exception("set_hico error : %c" % status)

if __name__ == "__main__":
    # parse arguments
    import argparse
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument ('-r', '--read', action="store_true", help="read magnetic tracks")
    group.add_argument ('-w', '--write', action="store_true", help="write magnetic tracks")
    group.add_argument ('-e', '--erase', action="store_true", help="erase magnetic tracks")
    group.add_argument ('-C', '--hico', action="store_true", help="select high coercivity mode")
    group.add_argument ('-c', '--loco', action="store_true", help="select low coercivity mode")
    group.add_argument ('-b', '--bpi', help="bit per inch for each track (h or l)")
    parser.add_argument('-d', '--device', help="path to serial communication device")
    parser.add_argument('-0', '--raw', action="store_true", help="do not use ISO encoding/decoding")
    parser.add_argument('-t', '--tracks', default="123", help="select tracks (1, 2, 3, 12, 23, 13, 123)")
    parser.add_argument('-B', '--bpc', help="bit per caracters for each track (5 to 8)")
    parser.add_argument('data', nargs="*", help="(write only) 1, 2 or 3 arguments, matching --tracks")
    args = parser.parse_args();
    
    if (args.read or args.erase) and len(args.data) != 0 or args.write and (len(args.data) != len(args.tracks)):
        print "too many arguments"
        parser.print_help()
        exit(1)
    
    tracks = [False, False, False]
    data = ["", "", ""]
    for i in range(0,len(args.tracks)):
        n = int(args.tracks[i])-1
        if(n<0 or n>2 or tracks[n]):
            parser.print_help()
            exit(1)
        tracks[n] = True
        if(args.write):
            data[n] = args.data[i]

    bpc1 = 8
    bpc2 = 8
    bpc3 = 8
    if args.bpc:
        bpc1 = ord(args.bpc[0])-48
        bpc2 = ord(args.bpc[1])-48
        bpc3 = ord(args.bpc[2])-48
    elif args.raw:
        args.bpc = "888" # force setup, as it's kept accross runs

    if args.bpi:
        bpi1 = args.bpi[0] != "l"
        bpi2 = args.bpi[1] != "l"
        bpi3 = args.bpi[2] != "l"
    
    # main code
    try:
        dev = msr(args.device)
        
        if args.bpc:
            dev.set_bpc(bpc1,bpc2,bpc3)
        
        if args.read & args.raw:
            s1,s2,s3 = dev.read_raw_tracks()
            def print_result(num, res):
                s,l,perr,lerr = res
                line = "%d=%s" % (num, s)
                if len(s) != l: line += " (+%d null)" % (l-len(s))
                if lerr: line += " (LRC error)"
                print line
                if -1 != perr.find("^"): print "  %s <- parity errors" % perr
            if tracks[0]: print_result(1, msr.unpack_raw(s1, msr.track1_map,  6, bpc1))
            if tracks[1]: print_result(2, msr.unpack_raw(s2, msr.track23_map, 4, bpc2))
            if tracks[2]: print_result(3, msr.unpack_raw(s3, msr.track23_map, 4, bpc3))
        
        elif args.read: # iso mode
            s1,s2,s3 = dev.read_tracks()
            if tracks[0]: print "1=%s" % s1
            if tracks[1]: print "2=%s" % s2
            if tracks[2]: print "3=%s" % s3
        
        elif args.write & args.raw:
            d1 = ""
            d2 = ""
            d3 = ""
            if tracks[0]:
                d1 = msr.pack_raw(data[0], msr.track1_map,  6, bpc1)
            if tracks[1]:
                d2 = msr.pack_raw(data[1], msr.track23_map, 4, bpc2)
            if tracks[2]:
                d3 = msr.pack_raw(data[2], msr.track23_map, 4, bpc3)
            dev.write_raw_tracks(d1,d2,d3)
            
        elif args.write: # iso mode
            dev.write_tracks(data[0],data[1],data[2])
        
        elif args.erase:
            dev.erase_tracks(tracks[0],tracks[1],tracks[2])

        elif args.loco:
            dev.set_coercivity(msr.loco)
            
        elif args.hico:
            dev.set_coercivity(msr.hico)

        elif args.bpi:
            dev.set_bpi(bpi1,bpi2,bpi3)
        
    except Exception as e:
        print e
