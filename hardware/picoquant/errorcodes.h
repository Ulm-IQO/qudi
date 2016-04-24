/*

This file contains the header file for the error code of the Picoharp300 device.

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

Copyright (C) 2015 Alexander Stark alexander.stark@uni-ulm.de

*/


/* 
Taken from:
http://www.picoquant.com/products/category/tcspc-and-time-tagging-modules/picoharp-300-stand-alone-tcspc-module-with-usb-interface

Error codes taken from PHLib  Ver. 3.0      December 2013
*/


#define ERROR_NONE                                0

#define ERROR_DEVICE_OPEN_FAIL                   -1
#define ERROR_DEVICE_BUSY                        -2
#define ERROR_DEVICE_HEVENT_FAIL                 -3
#define ERROR_DEVICE_CALLBSET_FAIL               -4
#define ERROR_DEVICE_BARMAP_FAIL                 -5
#define ERROR_DEVICE_CLOSE_FAIL                  -6
#define ERROR_DEVICE_RESET_FAIL                  -7
#define ERROR_DEVICE_GETVERSION_FAIL             -8
#define ERROR_DEVICE_VERSION_MISMATCH            -9
#define ERROR_DEVICE_NOT_OPEN                   -10
#define ERROR_DEVICE_LOCKED                     -11


#define ERROR_INSTANCE_RUNNING                  -16
#define ERROR_INVALID_ARGUMENT                  -17
#define ERROR_INVALID_MODE                      -18
#define ERROR_INVALID_OPTION                    -19
#define ERROR_INVALID_MEMORY                    -20
#define ERROR_INVALID_RDATA                     -21
#define ERROR_NOT_INITIALIZED                   -22
#define ERROR_NOT_CALIBRATED                    -23
#define ERROR_DMA_FAIL                          -24
#define ERROR_XTDEVICE_FAIL                     -25
#define ERROR_FPGACONF_FAIL                     -26
#define ERROR_IFCONF_FAIL                       -27
#define ERROR_FIFORESET_FAIL                    -28
#define ERROR_STATUS_FAIL                       -29

#define ERROR_USB_GETDRIVERVER_FAIL             -32
#define ERROR_USB_DRIVERVER_MISMATCH            -33
#define ERROR_USB_GETIFINFO_FAIL                -34
#define ERROR_USB_HISPEED_FAIL                  -35
#define ERROR_USB_VCMD_FAIL                     -36
#define ERROR_USB_BULKRD_FAIL                   -37

#define ERROR_HARDWARE_F01                      -64
#define ERROR_HARDWARE_F02                      -65
#define ERROR_HARDWARE_F03                      -66
#define ERROR_HARDWARE_F04                      -67
#define ERROR_HARDWARE_F05                      -68
#define ERROR_HARDWARE_F06                      -69
#define ERROR_HARDWARE_F07                      -70
#define ERROR_HARDWARE_F08                      -71
#define ERROR_HARDWARE_F09                      -72
#define ERROR_HARDWARE_F10                      -73
#define ERROR_HARDWARE_F11                      -74
#define ERROR_HARDWARE_F12                      -75
#define ERROR_HARDWARE_F13                      -76
#define ERROR_HARDWARE_F14                      -77
#define ERROR_HARDWARE_F15                      -78

