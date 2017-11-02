""" The UIUC/NCSA license:

Copyright (c) 2014 Kwiat Quantum Information Group
All rights reserved.

Developed by:	Kwiat Quantum Information Group
                University of Illinois, Urbana-Champaign (UIUC)
                http://research.physics.illinois.edu/QI/Photonics/

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal with the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimers.
Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimers
in the documentation and/or other materials provided with the distribution.

Neither the names of Kwiat Quantum Information Group, UIUC, nor the names of its contributors may be used to endorse
or promote products derived from this Software without specific prior written permission.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE 
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE CONTRIBUTORS
OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR 
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS WITH THE SOFTWARE.
"""

"""
LibTTag python interface.

Note that when referring to "array", it means a numpy array. Channel arrays are of dtype uint8, and time tag arrays are of dtype uint64 when writing,
and of dtype double when reading if a resolution is set.

getfreebuffer():
    Returns the next free buffer number. Refer to tt_getNextFree()

deletebuffer(i):
    Deletes a buffer on linux, if process crashed

class TTBuffer

    Constructor: (buffernum,create=False,datapoints=50000000)
        This opens or creates a buffer object. If you know the buffer number of a time tagger to be "buffer_number", you can open it as such:
        
            x = TTBuffer(buffer_number)
        
        If you want to create a buffer, you will need to set create=True, and optionally give a number of datapoints:
        
            buffer_num = getfreebuffer()
            x = TTBuffer(buffer_num,True)
        
        If it fails to create or open a buffer, a RuntimeError will be thrown
        
    Operator[]:
        This allows you to access time tag data as arrays. For example, giving an index to a TTBuffer object returns the channel and time tag
        
            x = TTBuffer(buffer_number)
            
            print x[-1]     #Prints a tuple of the most recent data point: (channel, time tag)
            print x[0]      #Prints a tuple of the first data point. Note that once the buffer starts overwriting data points, indices that have
                            #   been overwritten will give errors!
        
        Negative indices are 'from most recent datapoint', and positive indices represent the number of datapoint that the buffer handled (same as libTTag indices).
        Since the buffer is circular, and can only hold a finite number of data points, giving an index that is out of bounds of the buffer will throw a ValueError.
        
        The object also supports slicing for getting arrays of data:
            
            print x[-50:]       #Prints the most recent 50 data points in the form (channel array, time tag array)
            print x[-30:-10:3]  #Takes the data between the 30th and 10th most recent points, and returns a tuple of every third data point: (channel array, time tag array)
            print x[0:20]       #Prints the first 20 data points in the form (channel array, time tag array)
            
        Just to make things clear, to access the channel or time tag, you just add on another [], for example:
            
            print x[-10:][1]        #Prints the 10 most recent time tags
            print x[-10:][1][-1]    #Prints the most recent time tag
        
    Operator(): (time)
        Gives you time-based access to the array. Returns all data points from the most recent "time" in seconds as a tuple (channel array, time tag array):
            
            x = TTBuffer(buffer_number)
            
            print x(0.5)    #Prints out the most recent half second of data in the form (channel array, time tag array)
            
        That's really all there is to it. The buffer's resolution needs to be set for this to work, but your time tagger's interface should take care of that.
        
    
    datapoints:
        Allows you to get (and set) the number of data points that the buffer has handled. 
            
            x = TTBuffer(buffer_number)
            
            print x.datapoints  #Prints the number of data points the buffer has handled
            
            x.datapoints = 50   #Sets the property to 50
            print x.datapoints  #Prints 50
            
        The datapoints property is, in effect, the length of the buffer. That is,
        
            print x[-1]
            print x[x.datapoints - 1]       #Both of these represent the same value
        
        If fact, it is what the "length" of the buffer was defined to be:
        
            assert len(x)==x.datapoints     #Two ways of getting the datapoint number
    
    channels:
        Allows you to get (and set) the number of channels of the buffer. This value affects all channel-based functionality,
        so you probably want to leave it as set by your time tagger's interface.
            
            x = TTBuffer(buffer_number)
            
            print x.channels    #Prints out the number of channels that the buffer supports
            
            x.channels = 16     #Sets the number of channels. Only do this if you created the buffer
            print x.channels    #Prints out 16
    
    resolution:
        Allows you to get (and set) the buffer's resolution. This value is nan if a resolution is unset. This value affects all time-based functionality,
        so you probably want to leave it as set by your time tagger's interface.
        
            x = TTBuffer(buffer_number)
            
            print x.resolution  #Prints out the resolution of the buffer
            
            x.resolution = 1e-5 #Sets the buffer's resolution. Only do this if you created the buffer/know the time tagger's resolution
            print x.resolution  #Prints 1e-5
    
    reference:
        Allows you to get (and set) the buffer's reference time. Consult libTTag's documentation if you want to know exactly what this does.
        
            x = TTBuffer(buffer_number)
            
            print x.reference       #Prints out current reference time
            x.reference = 37673567  #Sets the current reference time (might not overwrite, depending on data)
            
    runners:
        Allows you to get (and set) the buffer's runners. Consult libTTag's documentation for what this does.
        
            x = TTBuffer(buffer_number)
            
            print x.runners     #Prints out the current number of runners
            x.runners = 1       #Sets the number of runners to 1
            print x.runners     #Prints 1
        
        This is NOT the recommended way to start and stop data taking. For that, see start() and stop() below,
        which wrap addrunner and remrunner, the threadsafe methods of adding and removing runners.
         
        
    size():
        Returns the number of data points that the buffer can hold at one time. 
            
            x = TTBuffer(buffer_number)     #Suppose this is a buffer with size 50 million data points
            
            print x.size()                  #This should then print 50000000
            
        In effect, the only valid values of the buffer are within the most recent size() datapoints:
            
            print x.datapoints - x.size()   #The oldest data point that is still in the buffer
            
    start():
        Adds a runner to the buffer. This is used to tell time taggers to start taking data (wraps tt_addrunner)
            
            x = TTBuffer(buffer_number)
            
            x.start()       #Increments runners by 1
        
    stop():
        Removes a runner from the buffer. This is used to tell time taggers that this application no longer needs it to be obtaining new data. (wraps tt_remrunner)
            
            x = TTBuffer(buffer_number)
            
            x.stop()       #Decrements runners by 1
        
        
    add(): (channel, timetag)
        Adds a data point to the end of the buffer.
            
            x = TTBuffer(buffer_number)
            
            x.add(3,7487478)    #Adds the time tag 7487478 at channel 3
            print x[-1]         #Returns (3,7487478) if resolution is not set, and (3,7487478*x.resolution) if it is set.
        
    addarray(): (channels,timetags)
        Adds an array of data points to the end of the buffer.
            
            x = TTBuffer(buffer_number)
            
            #Create the data arrays. Note the dtypes.
            channels = array([3,5,8,2,9,3],dtype=uint8)
            tags = array([100,200,1000,3000,3100,4000],dtype=uint64)
            
            x.addarray(channels,tags)   #Adds the arrays to the end of the buffer
            
            #Now the most recent 6 data points are the ones just added
    
    
    singles(): (time)
        Returns an array of size channels with the singles counts in most recent "time". Refer to tt_singles documentation.
        
            x = TTBuffer(buffer_number)
            
            singles = x.singles(1.0)    #Returns per-channel singles for the last second of data
            print sum(singles)          #Prints the total number of singles for the whole time tagger in the last second
    
    coincidences(): (time,radius,delays=None)
        Refer to tt_coincidences documentation for how this function works. Returns a matrix of per-channel coincidences
        
            x = TTBuffer(buffer_number)
            
            coincidenceMatrix = x.coincidences(0.5,1e-5)    #Returns a matrix of per-channel coincidences in the last half second, with coincidence radius 1e-5 seconds.
            print coincidenceMatrix[1,5]                    #Prints coincidence count between channel 1 and 5
            
        An array of delays (in seconds) for each channel can also optionally be used (for explanation of delays, see libttag documentation)
        
            delays = zeros(x.channels,dtype=double)         #Creates array of 0 delays of the correct size. You will need to find delays yourself
            
            cMatrix = x.coincidences(0.5,1e-5,delays)       #Just like that, you are taking into account delays between channels
            
    multicoincidences(): (time,diameter,channels,delays=None)
        Refer to tt_multicoincidences documentation for how this function works. Returns the number of coincidences between multiple channels
        
            x = TTBuffer(buffer_number)
            
            print x.multicoincidences(0.5,2e-5,[0,1,2])     #Prints out the number of coincidences in a diameter of 2e-5s, between channels 0,1 and 2 at once, in the last half second.
            
        The optional delay array refers to delays between the channels given, and not all the channels:
        
            print x.multicoincidences(0.5,2e-5,[0,1,5],[-1e-3,3e-5,8e-2])   #Same as before, but channel 0,1, and 5 have delays of -1e-3, 3e-5, and 8e-2 seconds respectively
        
    correlate(): (time,windowradius,bins,channel1,channel2,channel1delay=0.0,channel2delay=0.0)
        Refer to tt_correlate documentation for how this function works. Returns the cross-correlation between the two given channels with the given properties.
        Again, the properties are explained in detail in libTTag's documentation file.
        
            x = TTBuffer(buffer_number)
            
            #Returns an array of size 20 holding the cross-correlation between channels 1 and 3 in window size 2e-3 (2*radius) within the last half second of data
            correlation = x.correlate(0.5,1e-3,20,1,3)
            
        Optionally, the delays for the two channels can be added
            
            #Channel 1 has delay 3e-4s, and channel 2 has delay -2e-5s
            correlation = x.correlate(0.5,1e-3,20,1,3,3e-4,-2e-5)
        
    
    isvalid():
        Checks if the buffer is correctly ordered. True means all is well, and False means that analysis functions might crash, and that the time tagger interface
        is doing something wrong.
        
            x = TTBuffer(buffer_number)
            
            if not x.isvalid():
                #shiiiiii
    
    
    
    buffernumber:   Property, gives the number of buffer that is open. This is used for comparison of buffer objects
    
    rawchannels:    Access to libTTag's internal channel buffer.
    rawtags:        Access to libTTag's internal time tag buffer.
    tt_buf:         Pointer to C tt_buf structure.


Direct access to libTTag's functions:
    libTTag's direct functionality is exposed through ctypes in object libttag:
    
        libttag.<libttag function>
    
    Look at the code to find details.

"""
#Author: Daniel Kumor

import sys
import os
import ctypes
import numpy
import numpy.ctypeslib

##################################################################################
#Simple Ctypes interface
#   This allows for calling libttag functions just as you would from C.
#   This interface is used within the pythonic "TTBuffer" class. You can
#   use it yourself for something similar to the C API

libttag=None
if (sys.maxsize > 2**32):
    libttag = numpy.ctypeslib.load_library("libttag",".")
else:
    libttag = numpy.ctypeslib.load_library("libttag32",".")
    
    
class tt_buf(ctypes.Structure):
    _fields_ = [("map",ctypes.POINTER(ctypes.c_ulonglong)),
                ("timetag",ctypes.POINTER(ctypes.c_ulonglong)),
                ("channel",ctypes.POINTER(ctypes.c_ubyte))]

#Defines the C library's functions and their arguments

libttag.tt_getNextFree.restype = ctypes.c_int

if (os.name=="posix"):
    libttag.tt_deleteMap.restype = None
    libttag.tt_deleteMap.argtypes = [ctypes.c_int]

libttag.tt_getBufferAmount.restype = ctypes.c_int

libttag.tt_open.restype = ctypes.POINTER(tt_buf)
libttag.tt_open.argtypes = [ctypes.c_int]

libttag.tt_close.restype = None
libttag.tt_close.argtypes = [ctypes.POINTER(tt_buf)]

libttag.tt_create.restype = ctypes.POINTER(tt_buf)
libttag.tt_create.argtypes = [ctypes.c_int,ctypes.c_ulonglong]

libttag.tt_buffersize.restype = ctypes.c_ulonglong
libttag.tt_buffersize.argtypes = [ctypes.POINTER(tt_buf)]

libttag.tt_maxdata.restype = ctypes.c_ulonglong
libttag.tt_maxdata.argtypes = [ctypes.POINTER(tt_buf)]

libttag.tt_datapoints.restype = ctypes.c_ulonglong
libttag.tt_datapoints.argtypes = [ctypes.POINTER(tt_buf)]

libttag.tt_setdatapoints.restype = None
libttag.tt_setdatapoints.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_ulonglong]

#tt_minindex:
##define tt_minindex(buffer) (tt_datapoints(buffer) <= tt_maxdata(buffer)? 0: tt_datapoints(buffer) - tt_maxdata(buffer))

libttag.tt_resolution.restype = ctypes.c_double
libttag.tt_resolution.argtypes = [ctypes.POINTER(tt_buf)]

libttag.tt_setresolution.restype = None
libttag.tt_setresolution.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_double]

libttag.tt_channels.restype = ctypes.c_int
libttag.tt_channels.argtypes = [ctypes.POINTER(tt_buf)]

libttag.tt_setchannels.restype = None
libttag.tt_setchannels.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_int]

libttag.tt_reference.restype = ctypes.c_ulonglong
libttag.tt_reference.argtypes = [ctypes.POINTER(tt_buf)]

libttag.tt_setreference.restype = None
libttag.tt_setreference.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_ulonglong]

libttag.tt_running.restype = ctypes.c_int
libttag.tt_running.argtypes = [ctypes.POINTER(tt_buf)]

libttag.tt_setrunners.restype = None
libttag.tt_setrunners.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_int]

libttag.tt_addrunner.restype = None
libttag.tt_addrunner.argtypes = [ctypes.POINTER(tt_buf)]

libttag.tt_remrunner.restype = None
libttag.tt_remrunner.argtypes = [ctypes.POINTER(tt_buf)]

libttag.tt_add.restype = None
libttag.tt_add.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_ubyte,ctypes.c_ulonglong]

libttag.tt_addarray.restype = None
libttag.tt_addarray.argtypes = [ctypes.POINTER(tt_buf),ctypes.POINTER(ctypes.c_ubyte),ctypes.POINTER(ctypes.c_ulonglong),
                                ctypes.c_ulonglong]

libttag.tt_addarray_offset.restype = None
libttag.tt_addarray_offset.argtypes = [ctypes.POINTER(tt_buf),ctypes.POINTER(ctypes.c_ubyte),ctypes.POINTER(ctypes.c_ulonglong),
                                ctypes.c_ulonglong, ctypes.c_int,ctypes.c_int]

libttag.tt_readarray.restype = ctypes.c_ulonglong
libttag.tt_readarray.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_ulonglong,
                                ctypes.POINTER(ctypes.c_ubyte),ctypes.POINTER(ctypes.c_ulonglong),ctypes.c_ulonglong]

libttag.tt_readchannel.restype = ctypes.c_ulonglong
libttag.tt_readchannel.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_ulonglong,ctypes.c_ubyte,
                                ctypes.POINTER(ctypes.c_ulonglong),ctypes.c_ulonglong]

libttag.tt_subtractreference.restype = ctypes.c_ulonglong
libttag.tt_subtractreference.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_ulonglong]

libttag.tt_bins2points.restype = ctypes.c_ulonglong
libttag.tt_bins2points.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_ulonglong,ctypes.c_ulonglong]

libttag.tt_time2bin.restype = ctypes.c_ulonglong
libttag.tt_time2bin.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_double]

libttag.tt_singles.restype = ctypes.c_ulonglong
libttag.tt_singles.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_double,ctypes.POINTER(ctypes.c_ulonglong)]

libttag.tt_coincidences.restype = ctypes.POINTER(ctypes.c_ulonglong)
libttag.tt_coincidences.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_double,ctypes.c_double,ctypes.POINTER(ctypes.c_ulonglong),
                                ctypes.POINTER(ctypes.c_double)]

libttag.tt_coincidences_nd.restype = ctypes.POINTER(ctypes.c_ulonglong)
libttag.tt_coincidences_nd.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_double,ctypes.c_double,ctypes.POINTER(ctypes.c_ulonglong)]

libttag.tt_multicoincidences.restype = ctypes.c_ulonglong
libttag.tt_multicoincidences.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_double,ctypes.c_double,ctypes.POINTER(ctypes.c_ubyte),
                                ctypes.c_int,ctypes.POINTER(ctypes.c_double)]

libttag.tt_correlate.restype = ctypes.POINTER(ctypes.c_ulonglong)
libttag.tt_correlate.argtypes = [ctypes.POINTER(tt_buf),ctypes.c_double,ctypes.c_double,ctypes.c_int,ctypes.c_ubyte,ctypes.c_double,
                                ctypes.c_ubyte,ctypes.c_double,ctypes.POINTER(ctypes.c_ulonglong)]

libttag.tt_free.restype = None
libttag.tt_free.argtypes = [ctypes.c_void_p]

libttag.tt_validateBuffer.restype = ctypes.c_int
libttag.tt_validateBuffer.argtypes = [ctypes.POINTER(tt_buf)]

##################################################################################
#Pythonic Interface
#   This is what you want to use - access to time tagger data buffer
#   in an easy-to-use object, with lower chances of segfaults.

class TTBuffer(object):    
    
    #Opens a buffer given a buffer number. If create is set to True, tries to
    #   create a buffer with enough memory for the given number of datapoints
    def __init__(self,buffernumber,create=False,datapoints=50000000):
        self.buffernumber = buffernumber
        
        #Added to allow getting tags in integer format
        self.tagsAsTime = True

        if (create):
            self.tt_buf = libttag.tt_create(buffernumber,datapoints)
        else:
            self.tt_buf = libttag.tt_open(buffernumber)
        if not (bool(self.tt_buf)): raise RuntimeError("Failed to open buffer")
        
        #Now, create rawchannels and rawtags arrays from the internal buffers.
        #   These are the arrays libTTag uses internally to hold data points. They
        #   are exposed here because why not?
        bufferlength = libttag.tt_maxdata(self.tt_buf)
        self.rawchannels = numpy.ctypeslib.as_array(self.tt_buf.contents.channel,(bufferlength,))
        self.rawtags = numpy.ctypeslib.as_array(self.tt_buf.contents.timetag,(bufferlength,))
    
    #Necessary so that __del__ has tt_close defined
    __internal_tt_close = libttag.tt_close
    
    #Deletes the buffer
    def __del__(self):
        if (bool(self.tt_buf)): self.__internal_tt_close(self.tt_buf)
    
    #Comparisons between TTBuffer objects will compare their buffer numbers
    def __cmp__(self,other):
        if (isinstance(other,TTBuffer)):
            return self.buffernumber - other.buffernumber
        else:
            return self.buffernumber - other
    
    def __len__(self):
        return self.getdatapoints()
    
    #Allows the operator []
    def __getitem__(self,i):
        if (isinstance(i,slice)):
            start = i.start
            stop = i.stop
            step = i.step
            
            if (start):
                if (start<0):
                    if (self.size()+start<0 or self.datapoints +start < 0):
                        raise ValueError("start index out of buffer bounds")
                    start = self.datapoints + start
                else:
                    if (start > self.datapoints or start < self.datapoints-self.size()):
                        raise ValueError("start index out of buffer bounds")
            else:
                if (self.datapoints > self.size()):
                    start = self.datapoints-self.size()
                else:
                    start = 0
            
            if (stop):
                if (stop<0):
                    if (self.size()+stop<0 or self.datapoints +stop < 0):
                        raise ValueError("stop index out of buffer bounds")
                    stop = self.datapoints + stop
                else:
                    if (stop > self.datapoints or stop < self.datapoints-self.size()):
                        raise ValueError("stop index out of buffer bounds")
            else:
                stop = self.datapoints
            
            if (stop < start): raise ValueError("Array indexing invalid")
            elif (stop == start): return (array([],dtype=numpy.uint8),array([],dtype=numpy.double))
            
            arrlen = stop-start
            
            c = numpy.empty(arrlen,dtype=numpy.uint8)
            t = numpy.empty(arrlen,dtype=numpy.uint64)
            
            libttag.tt_readarray(self.tt_buf,start,
                                c.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
                                t.ctypes.data_as(ctypes.POINTER(ctypes.c_ulonglong)),
                                arrlen)
            
            if (step):
                c=c[::step]
                t=t[::step]
            
            if (numpy.isnan(self.resolution) or self.tagsAsTime==False):
                return (c,t)
            else:
                return (c,t.astype(numpy.double)*self.resolution)
                
        else:
            if (i<0):
                if (self.size()+i<0 or self.datapoints +i < 0):
                    raise ValueError("Array index out of buffer bounds")
                i = self.datapoints + i
            else:
                if (i > self.datapoints or i < self.datapoints-self.size()):
                    raise ValueError("Array index out of buffer bounds")
            c=ctypes.c_ubyte()
            t=ctypes.c_ulonglong()
            
            libttag.tt_readarray(self.tt_buf,i,ctypes.byref(c),ctypes.byref(t),1)
            if (numpy.isnan(self.resolution) or self.tagsAsTime==False):
                return (c.value,t.value)
            else:
                return (c.value,t.value*self.resolution)
            
            
        
    
    #Calling the object with a time returns the most recent datapoints within the time
    def __call__(self,t):
        if (numpy.isnan(self.resolution)):  raise RuntimeError("Resolution unset")
        if (t<=0. or self.datapoints==0): return (array([],dtype=numpy.uint8),array([],dtype=numpy.double))
        
        #First, convert the time to bins, and remove reference time
        bins = libttag.tt_subtractreference(self.tt_buf,libttag.tt_time2bin(self.tt_buf,t))
        if (bins == 0): return (array([],dtype=numpy.uint8),array([],dtype=numpy.double))
        
        #Now get the number of datapoints, the +1 is to include most recent
        points = libttag.tt_bins2points(self.tt_buf,self.datapoints-1,bins)+1
        if (points > self.size()): 
            print("TTBuffer: WARNING: time given larger than buffer size")
            points = self.size()
        
        #Return the datapoints
        return self[-points:]
        
    
    #The number of datapoints that the buffer can hold at one time
    def size(self):
        return libttag.tt_maxdata(self.tt_buf)
    
    #The number of datapoints that the buffer has processed can be both accessed and set
    def getdatapoints(self):
        return libttag.tt_datapoints(self.tt_buf)
    def setdatapoints(self,d):
        libttag.tt_setdatapoints(self.tt_buf,d)
    datapoints = property(getdatapoints,setdatapoints)
    
    #The channel amount of the buffer can be both accessed and set
    def getchannels(self):
        return libttag.tt_channels(self.tt_buf)
    def setchannels(self,c):
        if (c>256 or c<1): raise ValueError("Invalid channel amount")
        libttag.tt_setchannels(self.tt_buf,c)
    channels = property(getchannels,setchannels)
    
    #The resolution of the buffer can be both accessed and set
    def getresolution(self):
        return libttag.tt_resolution(self.tt_buf)
    def setresolution(self,res):
        libttag.tt_setresolution(self.tt_buf,res)
    resolution = property(getresolution,setresolution)
    
    #The reference value of the buffer can be accessed and set
    def getreference(self):
        return libttag.tt_reference(self.tt_buf)
    def setreference(self,ref):
        libttag.tt_setreference(self.tt_buf,ref)
    reference = property(getreference,setreference)
    
    #The number of runners currently registered can be accessed and set
    def getrunners(self):
        return libttag.tt_running(self.tt_buf)
    def setrunners(self,r):
        libttag.tt_setrunners(self.tt_buf,r)
    runners = property(getrunners,setrunners)
    
    #Can start and stop data taking by adding and removing runners
    def start(self):
        libttag.tt_addrunner(self.tt_buf)
    def stop(self):
        return libttag.tt_remrunner(self.tt_buf)
    
    #Just to make sure buffer is valid
    def isvalid(self):
        res=libttag.tt_validateBuffer(self.tt_buf)
        return (res==1)
    
    #Adding a single datapoint
    def add(self,channel,timetag):
        libttag.tt_add(self.tt_buf,channel,timetag)
    
    def addarray(self,channels,timetags):
        if (len(channels)!=len(timetags)):
            raise ValueError("Channel and Time tag arrays need to be same length")
        if not (isinstance(channels,numpy.ndarray)):
            channels = numpy.array(channels,dtype=numpy.uint8)
        if not (isinstance(timetags,numpy.ndarray)):
            timetags = numpy.array(timetags,dtype=numpy.uint64)
        if (channels.dtype!=numpy.uint8 or timetags.dtype!=numpy.uint64):
            raise ValueError("Channel and time tag arrays are of wrong type")
        return libttag.tt_addarray(self.tt_buf,channels.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),
                                    timetags.ctypes.data_as(ctypes.POINTER(ctypes.c_ulonglong)),len(channels))
    
    #Here are the data analysis functions!
    
    def singles(self,time):
        s = numpy.zeros(self.channels,dtype=numpy.uint64)
        libttag.tt_singles(self.tt_buf,time,s.ctypes.data_as(ctypes.POINTER(ctypes.c_ulonglong)))
        return s
    
    def coincidences(self,time,radius,delays=None):
        coincidenceMatrix = numpy.zeros((self.channels,self.channels),dtype=numpy.uint64)
        if (delays!=None):
            if not (isinstance(delays,numpy.ndarray)):
                delays = numpy.array(delays,dtype=numpy.double)
            if (delays.dtype!=numpy.double or len(delays)>self.channels):
                raise ValueError("Delay array incorrect type or length")
            if (len(delays)<self.channels):
                d = numpy.zeros(self.channels,dtype=numpy.double)
                d[0:len(delays)]=delays
                delays=d
            libttag.tt_coincidences(self.tt_buf,time,radius,coincidenceMatrix.ctypes.data_as(ctypes.POINTER(ctypes.c_ulonglong)),
                                    delays.ctypes.data_as(ctypes.POINTER(ctypes.c_double)))
        else:
            #If there are no delays, run the nd version of tt_coincidences, which will probably be quite a bit faster
            libttag.tt_coincidences_nd(self.tt_buf,time,radius,coincidenceMatrix.ctypes.data_as(ctypes.POINTER(ctypes.c_ulonglong)))
        return coincidenceMatrix
    
    def multicoincidences(self,time,diameter,channels,delays=None):
        if not (isinstance(channels,numpy.ndarray)):
            channels = numpy.array(channels,dtype=numpy.uint8)
        if (channels.dtype!=numpy.uint8):
            channels = channels.astype(numpy.uint8)
        if (delays!=None):
            if not (isinstance(delays,numpy.ndarray)):
                delays = numpy.array(delays,dtype=numpy.double)
            if (delays.dtype!=numpy.double or len(delays)!=len(channels)):
                raise ValueError("Delay array incorrect type or length")
            return libttag.tt_multicoincidences(self.tt_buf,time,diameter,
                        channels.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),len(channels),
                        delays.ctypes.data_as(ctypes.POINTER(ctypes.c_double)))
        else:
            return libttag.tt_multicoincidences(self.tt_buf,time,diameter,
                        channels.ctypes.data_as(ctypes.POINTER(ctypes.c_ubyte)),len(channels),None)
        
    def correlate(self,time,windowradius,bins,channel1,channel2,channel1delay=0.0,channel2delay=0.0):
        corr = numpy.zeros(bins,dtype=numpy.uint64)
        libttag.tt_correlate(self.tt_buf,time,windowradius,bins,channel1,channel1delay,
                            channel2,channel2delay,corr.ctypes.data_as(ctypes.POINTER(ctypes.c_ulonglong)))
        return corr


def getfreebuffer():
    return libttag.tt_getNextFree()

def deletebuffer(i):
    libttag.tt_deleteMap(i)

if (__name__=="__main__"):
    #This isn't really a full-feature test. It is there just to make me feel better about myself
    print("Testing python interface to libTTag")
    
    assert getfreebuffer()==0
    x=TTBuffer(0,create=True,datapoints=50)
    
    assert getfreebuffer()==1
    assert x.size()==50
    assert x.datapoints==0
    assert numpy.isnan(x.resolution)
    assert x.channels==256
    assert x.runners==0
    
    x.resolution = 0.001
    x.channels=10
    x.add(5,800)
    x.start()
    
    assert x.resolution == 0.001
    assert x.channels==10
    assert x.runners == 1
    assert x.datapoints == 1
    assert x[0][0]==5
    assert x[-1][1]==.8
    
    x.stop()
    x.addarray([1,1,2,3,5,8],[1000,2000,3000,4000,5000,6000])
    
    assert x.runners == 0
    assert x.datapoints==7
    assert x(1.0)[0][0]==5
    assert x(1.0)[0][1]==8
    assert x.singles(15.0)[1]==2
    
    assert x.coincidences(15.0,0.5,[0,-1,0,0,0,0,0,0,0,0])[1,2]==1
    print(x.coincidences(15.0,0.5,[0,0,0,0,0,0,0,0,0,0]))
    print(x.coincidences(15.0,0.5))

    assert x.multicoincidences(15.0,0.5,[1,2],[-1,0])==1
    assert x.multicoincidences(15.0,0.5,[1,2])==0
    assert x.correlate(15,2,20,1,1)[4]==1
    
    print("\nSuccessfully finished tests")

