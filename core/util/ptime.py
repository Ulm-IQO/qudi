# -*- coding: utf-8 -*-
"""
ptime.py -  Precision time function made os-independent (should have been taken
care of by python)

QuDi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

QuDi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with QuDi. If not, see <http://www.gnu.org/licenses/>.

Copyright (C) 2015 Jan M. Binder jan.binder@uni-ulm.de

Derived form ACQ4:
Copyright 2010  Luke Campagnola
Originally distributed under MIT/X11 license. See documentation/MITLicense.txt for more infomation.
"""


import sys
import time as systime
START_TIME = None
time = None

def winTime():
    """Return the current time in seconds with high precision. (windows version, use Manager.time() to stay platform independent)."""
    return systime.clock() + START_TIME
    #return systime.time()

def unixTime():
    """Return the current time in seconds with high precision (unix version, use Manager.time() to stay platform independent)."""
    return systime.time()

if 'win' in sys.platform:
    cstart = systime.clock()  ### Required to start the clock in windows
    START_TIME = systime.time() - cstart
    
    time = winTime
else:
    time = unixTime

