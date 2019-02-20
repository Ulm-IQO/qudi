"""
.. module: uc480.uc480_h
   :platform: Windows, Linux
.. moduleauthor:: Daniel Dietze <daniel.dietze@berkeley.edu>

Thorlabs' uc480 header file translated to python.

..

   The uc480 python module is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   The uc480 python module is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with the uc480 python module. If not, see <http://www.gnu.org/licenses/>.

   Copyright 2015 Daniel Dietze <daniel.dietze@berkeley.edu>.
"""
import platform
import ctypes

if platform.system() == "Windows":
    import ctypes.wintypes as wt
else:
    import wintypes_linux as wt

#  ----------------------------------------------------------------------------
#  Color modes
#  ----------------------------------------------------------------------------
IS_COLORMODE_INVALID      =          0
IS_COLORMODE_MONOCHROME   =          1
IS_COLORMODE_BAYER        =          2
IS_COLORMODE_CBYCRY       =          4

#  ----------------------------------------------------------------------------
#   Sensor Types
#  ----------------------------------------------------------------------------
IS_SENSOR_INVALID  = 0x0000

#  CMOS sensors
IS_SENSOR_C0640R13M = 0x0001 #  cmos, 0640x0480, rolling, 1/3", mono,
IS_SENSOR_C0640R13C = 0x0002 #  cmos, 0640x0480, rolling, 1/3", color,
IS_SENSOR_C1280R23M = 0x0003 #  cmos, 1280x1024, rolling, 1/1.8", mono,
IS_SENSOR_C1280R23C = 0x0004 #  cmos, 1280x1024, rolling, 1/1.8", color,

IS_SENSOR_C1600R12C = 0x0008 #  cmos, 1600x1200, rolling, 1/2", color,

IS_SENSOR_C2048R12C = 0x000A #  cmos, 2048x1536, rolling, 1/2", color,
IS_SENSOR_C2592R12M = 0x000B #  cmos, 2592x1944, rolling, 1/2", mono
IS_SENSOR_C2592R12C = 0x000C #  cmos, 2592x1944, rolling, 1/2", color

IS_SENSOR_C0640G12M = 0x0010 #  cmos, 0640x0480, global,  1/2", mono,
IS_SENSOR_C0640G12C = 0x0011 #  cmos, 0640x0480, global,  1/2", color,
IS_SENSOR_C0752G13M = 0x0012 #  cmos, 0752x0480, global,  1/3", mono,
IS_SENSOR_C0752G13C = 0x0013 #  cmos, 0752x0480, global,  1/3", color,

IS_SENSOR_C1282R13C = 0x0015 #  cmos, 1280x1024, rolling, 1/3", color,

IS_SENSOR_C1601R13C = 0x0017 #  cmos, 1600x1200, rolling, 1/3.2", color,

IS_SENSOR_C0753G13M = 0x0018 #  cmos, 0752x0480, global,  1/3", mono,
IS_SENSOR_C0753G13C = 0x0019 #  cmos, 0752x0480, global,  1/3", color,

IS_SENSOR_C0754G13M = 0x0022 #  cmos, 0752x0480, global,  1/3", mono, single board (LE)
IS_SENSOR_C0754G13C = 0x0023 #  cmos, 0752x0480, global,  1/3", color, single board (LE)

IS_SENSOR_C1284R13C = 0x0025 #  cmos, 1280x1024, rolling, 1/3", color, single board (LE))
IS_SENSOR_C1604R13C = 0x0027 #  cmos, 1600x1200, rolling, 1/3.2", color, single board (LE)
IS_SENSOR_C1285R12M = 0x0028 #  cmos, 1280x1024, rolling, 1/2", mono,  single board
IS_SENSOR_C1285R12C = 0x0029 #  cmos, 1280x1024, rolling, 1/2", color, single board
IS_SENSOR_C1605R12C = 0x002B #  cmos, 1600x1200, rolling, 1/2", color, single board
IS_SENSOR_C2055R12C = 0x002D #  cmos, 2048x1536, rolling, 1/2", color, single board
IS_SENSOR_C2595R12M = 0x002E #  cmos, 2592x1944, rolling, 1/2", mono,  single board
IS_SENSOR_C2595R12C = 0x002F #  cmos, 2592x1944, rolling, 1/2", color, single board

IS_SENSOR_C1280R12M = 0x0030 #  cmos, 1280x1024, rolling, 1/2", mono,
IS_SENSOR_C1280R12C = 0x0031 #  cmos, 1280x1024, rolling, 1/2", color,

IS_SENSOR_C1283R12M = 0x0032 #  cmos, 1280x1024, rolling, 1/2", mono, single board
IS_SENSOR_C1283R12C = 0x0033 #  cmos, 1280x1024, rolling, 1/2", color, single board

IS_SENSOR_C1603R12M = 0x0034 #  cmos, 1600x1200, rolling, 1/2", mono, single board
IS_SENSOR_C1603R12C = 0x0035 #  cmos, 1600x1200, rolling, 1/2", color, single board
IS_SENSOR_C2053R12C = 0x0037 #  cmos, 2048x1536, rolling, 1/2", color, single board
IS_SENSOR_C2593R12M = 0x0038 #  cmos, 2592x1944, rolling, 1/2", mono,  single board
IS_SENSOR_C2593R12C = 0x0039 #  cmos, 2592x1944, rolling, 1/2", color, single board

IS_SENSOR_C1286R12M = 0x003A #  cmos, 1280x1024, rolling, 1/2", mono, single board
IS_SENSOR_C1286R12C = 0x003B #  cmos, 1280x1024, rolling, 1/2", color, single board

IS_SENSOR_C1287R12M_WO = 0x003C #  cmos, 1280x1024, rolling, 1/2", color, USB board
IS_SENSOR_C1287R12C_WO = 0x003D #  cmos, 1280x1024, rolling, 1/2", color, USB board

IS_SENSOR_C3840R12M = 0x003E #  cmos, 3840x2760, rolling, 1/2.5", mono
IS_SENSOR_C3840R12C = 0x003F #  cmos, 3840x2760, rolling, 1/2.5", color

IS_SENSOR_C3845R12M = 0x0040 #  cmos, 3840x2760, rolling, 1/2.5", mono,  single board
IS_SENSOR_C3845R12C = 0x0041 #  cmos, 3840x2760, rolling, 1/2.5", color, single board

IS_SENSOR_C0768R12M = 0x004A #  cmos, 0768x0576, rolling, HDR sensor, 1/2", mono
IS_SENSOR_C0768R12C = 0x004B #  cmos, 0768x0576, rolling, HDR sensor, 1/2", color

IS_SENSOR_C2057R12M_WO = 0x0044 #  cmos, 2048x1536, rolling, 1/2", mono,  USB board (special version WO)
IS_SENSOR_C2057R12C_WO = 0x0045 #  cmos, 2048x1536, rolling, 1/2", color, USB board (special version WO)

IS_SENSOR_C2597R12M = 0x0048 #  cmos, 2592x1944, rolling, 1/2", mono,  USB board (special version WO)
IS_SENSOR_C2597R12C = 0x0049 #  cmos, 2592x1944, rolling, 1/2", color, WO board (special version WO)

IS_SENSOR_C1280G12M = 0x0050 #  cmos, 1280x1024, global, 1/2", mono
IS_SENSOR_C1280G12C = 0x0051 #  cmos, 1280x1024, global, 1/2", color

#  CCD sensors
IS_SENSOR_D1024G13M = 0x0080 #  ccd, 1024x0768, global, 1/3", mono,
IS_SENSOR_D1024G13C = 0x0081 #  ccd, 1024x0768, global, 1/3", color,

IS_SENSOR_D0640G13M = 0x0082 #  ccd, 0640x0480, global, 1/3", mono
IS_SENSOR_D0640G13C = 0x0083 #  ccd, 0640x0480, global, 1/3", color

IS_SENSOR_D1281G12M = 0x0084 #  ccd, 1280x1024, global, 1/2", mono
IS_SENSOR_D1281G12C = 0x0085 #  ccd, 1280x1024, global, 1/2", color

IS_SENSOR_D0640G12M = 0x0088 #  ccd, 0640x0480, global, 1/2", mono,
IS_SENSOR_D0640G12C = 0x0089 #  ccd, 0640x0480, global, 1/2", color,

IS_SENSOR_D0640G14M = 0x0090 #  ccd, 0640x0480, global, 1/4", mono,
IS_SENSOR_D0640G14C = 0x0091 #  ccd, 0640x0480, global, 1/4", color,

IS_SENSOR_D0768G12M = 0x0092 #  ccd, 0768x0582, global, 1/2", mono,
IS_SENSOR_D0768G12C = 0x0093 #  ccd, 0768x0582, global, 1/2", color,

IS_SENSOR_D1280G12M = 0x0096 #  ccd, 1280x1024, global, 1/2", mono,
IS_SENSOR_D1280G12C = 0x0097 #  ccd, 1280x1024, global, 1/2", color,

IS_SENSOR_D1600G12M = 0x0098 #  ccd, 1600x1200, global, 1/1.8", mono,
IS_SENSOR_D1600G12C = 0x0099 #  ccd, 1600x1200, global, 1/1.8", color,

IS_SENSOR_D1280G13M = 0x009A #  ccd, 1280x960, global, 1/3", mono,
IS_SENSOR_D1280G13C = 0x009B #  ccd, 1280x960, global, 1/3", color,


#  ----------------------------------------------------------------------------
#  error codes
#  ----------------------------------------------------------------------------
IS_NO_SUCCESS                 =        -1  #  function call failed
IS_SUCCESS                    =        0   #  function call succeeded
IS_INVALID_CAMERA_HANDLE      =        1   #  camera handle is not valid or zero
IS_INVALID_HANDLE             =        1   #  a handle other than the camera handle is invalid

IS_IO_REQUEST_FAILED          =        2   #  an io request to the driver failed
IS_CANT_OPEN_DEVICE           =        3   #  returned by is_InitCamera
IS_CANT_CLOSE_DEVICE          =        4
IS_CANT_SETUP_MEMORY          =        5
IS_NO_HWND_FOR_ERROR_REPORT   =        6
IS_ERROR_MESSAGE_NOT_CREATED  =        7
IS_ERROR_STRING_NOT_FOUND     =        8
IS_HOOK_NOT_CREATED           =        9
IS_TIMER_NOT_CREATED          =       10
IS_CANT_OPEN_REGISTRY         =       11
IS_CANT_READ_REGISTRY         =       12
IS_CANT_VALIDATE_BOARD        =       13
IS_CANT_GIVE_BOARD_ACCESS     =       14
IS_NO_IMAGE_MEM_ALLOCATED     =       15
IS_CANT_CLEANUP_MEMORY        =       16
IS_CANT_COMMUNICATE_WITH_DRIVER =     17
IS_FUNCTION_NOT_SUPPORTED_YET   =     18
IS_OPERATING_SYSTEM_NOT_SUPPORTED =   19

IS_INVALID_VIDEO_IN       =           20
IS_INVALID_IMG_SIZE       =           21
IS_INVALID_ADDRESS        =           22
IS_INVALID_VIDEO_MODE     =           23
IS_INVALID_AGC_MODE       =           24
IS_INVALID_GAMMA_MODE     =           25
IS_INVALID_SYNC_LEVEL     =           26
IS_INVALID_CBARS_MODE     =           27
IS_INVALID_COLOR_MODE     =           28
IS_INVALID_SCALE_FACTOR   =           29
IS_INVALID_IMAGE_SIZE     =           30
IS_INVALID_IMAGE_POS      =           31
IS_INVALID_CAPTURE_MODE   =           32
IS_INVALID_RISC_PROGRAM   =           33
IS_INVALID_BRIGHTNESS     =           34
IS_INVALID_CONTRAST       =           35
IS_INVALID_SATURATION_U   =           36
IS_INVALID_SATURATION_V   =           37
IS_INVALID_HUE            =           38
IS_INVALID_HOR_FILTER_STEP  =         39
IS_INVALID_VERT_FILTER_STEP  =        40
IS_INVALID_EEPROM_READ_ADDRESS =      41
IS_INVALID_EEPROM_WRITE_ADDRESS  =    42
IS_INVALID_EEPROM_READ_LENGTH    =    43
IS_INVALID_EEPROM_WRITE_LENGTH   =    44
IS_INVALID_BOARD_INFO_POINTER    =    45
IS_INVALID_DISPLAY_MODE          =    46
IS_INVALID_ERR_REP_MODE          =    47
IS_INVALID_BITS_PIXEL            =    48
IS_INVALID_MEMORY_POINTER        =    49

IS_FILE_WRITE_OPEN_ERROR          =   50
IS_FILE_READ_OPEN_ERROR           =   51
IS_FILE_READ_INVALID_BMP_ID       =   52
IS_FILE_READ_INVALID_BMP_SIZE     =   53
IS_FILE_READ_INVALID_BIT_COUNT    =   54
IS_WRONG_KERNEL_VERSION           =   55

IS_RISC_INVALID_XLENGTH      =        60
IS_RISC_INVALID_YLENGTH      =        61
IS_RISC_EXCEED_IMG_SIZE      =        62

#  DirectDraw Mode errors
IS_DD_MAIN_FAILED              =      70
IS_DD_PRIMSURFACE_FAILED       =      71
IS_DD_SCRN_SIZE_NOT_SUPPORTED  =      72
IS_DD_CLIPPER_FAILED           =      73
IS_DD_CLIPPER_HWND_FAILED      =      74
IS_DD_CLIPPER_CONNECT_FAILED   =      75
IS_DD_BACKSURFACE_FAILED       =      76
IS_DD_BACKSURFACE_IN_SYSMEM    =      77
IS_DD_MDL_MALLOC_ERR           =      78
IS_DD_MDL_SIZE_ERR             =      79
IS_DD_CLIP_NO_CHANGE           =      80
IS_DD_PRIMMEM_NULL             =      81
IS_DD_BACKMEM_NULL             =      82
IS_DD_BACKOVLMEM_NULL          =      83
IS_DD_OVERLAYSURFACE_FAILED    =      84
IS_DD_OVERLAYSURFACE_IN_SYSMEM =      85
IS_DD_OVERLAY_NOT_ALLOWED      =      86
IS_DD_OVERLAY_COLKEY_ERR       =      87
IS_DD_OVERLAY_NOT_ENABLED      =      88
IS_DD_GET_DC_ERROR             =      89
IS_DD_DDRAW_DLL_NOT_LOADED     =      90
IS_DD_THREAD_NOT_CREATED       =      91
IS_DD_CANT_GET_CAPS            =      92
IS_DD_NO_OVERLAYSURFACE        =      93
IS_DD_NO_OVERLAYSTRETCH        =      94
IS_DD_CANT_CREATE_OVERLAYSURFACE =    95
IS_DD_CANT_UPDATE_OVERLAYSURFACE =    96
IS_DD_INVALID_STRETCH            =    97

IS_EV_INVALID_EVENT_NUMBER    =      100
IS_INVALID_MODE               =      101
IS_CANT_FIND_FALCHOOK         =      102
IS_CANT_FIND_HOOK             =      102
IS_CANT_GET_HOOK_PROC_ADDR    =      103
IS_CANT_CHAIN_HOOK_PROC       =      104
IS_CANT_SETUP_WND_PROC        =      105
IS_HWND_NULL                  =      106
IS_INVALID_UPDATE_MODE        =      107
IS_NO_ACTIVE_IMG_MEM          =      108
IS_CANT_INIT_EVENT            =      109
IS_FUNC_NOT_AVAIL_IN_OS       =      110
IS_CAMERA_NOT_CONNECTED       =      111
IS_SEQUENCE_LIST_EMPTY        =      112
IS_CANT_ADD_TO_SEQUENCE       =      113
IS_LOW_OF_SEQUENCE_RISC_MEM   =      114
IS_IMGMEM2FREE_USED_IN_SEQ    =      115
IS_IMGMEM_NOT_IN_SEQUENCE_LIST=      116
IS_SEQUENCE_BUF_ALREADY_LOCKED=      117
IS_INVALID_DEVICE_ID          =      118
IS_INVALID_BOARD_ID           =      119
IS_ALL_DEVICES_BUSY           =      120
IS_HOOK_BUSY                  =      121
IS_TIMED_OUT                  =      122
IS_NULL_POINTER               =      123
IS_WRONG_HOOK_VERSION         =      124
IS_INVALID_PARAMETER          =      125   #  a parameter specified was invalid
IS_NOT_ALLOWED                =      126
IS_OUT_OF_MEMORY              =      127
IS_INVALID_WHILE_LIVE         =      128
IS_ACCESS_VIOLATION           =      129   #  an internal exception occurred
IS_UNKNOWN_ROP_EFFECT         =      130
IS_INVALID_RENDER_MODE        =      131
IS_INVALID_THREAD_CONTEXT     =      132
IS_NO_HARDWARE_INSTALLED      =      133
IS_INVALID_WATCHDOG_TIME      =      134
IS_INVALID_WATCHDOG_MODE      =      135
IS_INVALID_PASSTHROUGH_IN     =      136
IS_ERROR_SETTING_PASSTHROUGH_IN =    137
IS_FAILURE_ON_SETTING_WATCHDOG  =    138
IS_NO_USB20                     =    139   #  the usb port doesnt support usb 2.0
IS_CAPTURE_RUNNING              =    140   #  there is already a capture running

IS_MEMORY_BOARD_ACTIVATED      =     141   #  operation could not execute while mboard is enabled
IS_MEMORY_BOARD_DEACTIVATED    =     142   #  operation could not execute while mboard is disabled
IS_NO_MEMORY_BOARD_CONNECTED   =     143   #  no memory board connected
IS_TOO_LESS_MEMORY             =     144   #  image size is above memory capacity
IS_IMAGE_NOT_PRESENT           =     145   #  requested image is no longer present in the camera
IS_MEMORY_MODE_RUNNING         =     146
IS_MEMORYBOARD_DISABLED        =     147

IS_TRIGGER_ACTIVATED         =       148   #  operation could not execute while trigger is enabled
IS_WRONG_KEY                 =       150
IS_CRC_ERROR                 =       151
IS_NOT_YET_RELEASED          =       152   #  this feature is not available yet
IS_NOT_CALIBRATED            =       153   #  the camera is not calibrated
IS_WAITING_FOR_KERNEL        =       154   #  a request to the kernel exceeded
IS_NOT_SUPPORTED             =       155   #  operation mode is not supported
IS_TRIGGER_NOT_ACTIVATED     =       156   #  operation could not execute while trigger is disabled
IS_OPERATION_ABORTED         =       157
IS_BAD_STRUCTURE_SIZE        =       158
IS_INVALID_BUFFER_SIZE       =       159
IS_INVALID_PIXEL_CLOCK       =       160
IS_INVALID_EXPOSURE_TIME     =       161
IS_AUTO_EXPOSURE_RUNNING     =       162
IS_CANNOT_CREATE_BB_SURF     =       163   #  error creating backbuffer surface
IS_CANNOT_CREATE_BB_MIX      =       164   #  backbuffer mixer surfaces can not be created
IS_BB_OVLMEM_NULL            =       165   #  backbuffer overlay mem could not be locked
IS_CANNOT_CREATE_BB_OVL      =       166   #  backbuffer overlay mem could not be created
IS_NOT_SUPP_IN_OVL_SURF_MODE =       167   #  function not supported in overlay surface mode
IS_INVALID_SURFACE           =       168   #  surface invalid
IS_SURFACE_LOST              =       169   #  surface has been lost
IS_RELEASE_BB_OVL_DC         =       170   #  error releasing backbuffer overlay DC
IS_BB_TIMER_NOT_CREATED      =       171   #  backbuffer timer could not be created
IS_BB_OVL_NOT_EN             =       172   #  backbuffer overlay has not been enabled
IS_ONLY_IN_BB_MODE           =       173   #  only possible in backbuffer mode
IS_INVALID_COLOR_FORMAT      =       174   #  invalid color format
IS_INVALID_WB_BINNING_MODE   =       175   #  invalid binning mode for AWB
IS_INVALID_I2C_DEVICE_ADDRESS =      176   #  invalid I2C device address
IS_COULD_NOT_CONVERT          =      177   #  current image couldn't be converted
IS_TRANSFER_ERROR             =      178   #  transfer failed
IS_PARAMETER_SET_NOT_PRESENT  =      179   #  the parameter set is not present
IS_INVALID_CAMERA_TYPE        =      180   #  the camera type in the ini file doesn't match
IS_INVALID_HOST_IP_HIBYTE     =      181   #  HIBYTE of host address is invalid
IS_CM_NOT_SUPP_IN_CURR_DISPLAYMODE = 182   #  color mode is not supported in the current display mode
IS_NO_IR_FILTER                   =  183
IS_STARTER_FW_UPLOAD_NEEDED       =  184   #  device starter firmware is not compatible

IS_DR_LIBRARY_NOT_FOUND          =       185   #  the DirectRender library could not be found
IS_DR_DEVICE_OUT_OF_MEMORY       =       186   #  insufficient graphics adapter video memory
IS_DR_CANNOT_CREATE_SURFACE      =       187   #  the image or overlay surface could not be created
IS_DR_CANNOT_CREATE_VERTEX_BUFFER =      188   #  the vertex buffer could not be created
IS_DR_CANNOT_CREATE_TEXTURE       =      189   #  the texture could not be created
IS_DR_CANNOT_LOCK_OVERLAY_SURFACE =      190   #  the overlay surface could not be locked
IS_DR_CANNOT_UNLOCK_OVERLAY_SURFACE =    191   #  the overlay surface could not be unlocked
IS_DR_CANNOT_GET_OVERLAY_DC         =    192   #  cannot get the overlay surface DC
IS_DR_CANNOT_RELEASE_OVERLAY_DC     =    193   #  cannot release the overlay surface DC
IS_DR_DEVICE_CAPS_INSUFFICIENT      =    194   #  insufficient graphics adapter capabilities
IS_INCOMPATIBLE_SETTING             =    195   #  Operation is not possible because of another incompatible setting
IS_DR_NOT_ALLOWED_WHILE_DC_IS_ACTIVE =   196   #  user App still has DC handle.
IS_DEVICE_ALREADY_PAIRED             =   197   #  The device is already paired
IS_SUBNETMASK_MISMATCH               =   198   #  The subnetmasks of the device and the adapter differ
IS_SUBNET_MISMATCH                   =   199   #  The subnets of the device and the adapter differ
IS_INVALID_IP_CONFIGURATION          =   200   #  The IP configuation of the device is invalid
IS_DEVICE_NOT_COMPATIBLE             =   201   #  The device is incompatible to the driver
IS_NETWORK_FRAME_SIZE_INCOMPATIBLE   =   202   #  The frame size settings of the device and the network adapter are incompatible
IS_NETWORK_CONFIGURATION_INVALID     =   203   #  The network adapter configuration is invalid
IS_ERROR_CPU_IDLE_STATES_CONFIGURATION = 204   #  The setting of the CPU idle state configuration failed
IS_DEVICE_BUSY                        =  205   #  The device is busy. The operation must be executed again later.


#  ----------------------------------------------------------------------------
#  common definitions
#  ----------------------------------------------------------------------------
IS_OFF                      =        0
IS_ON                       =        1
IS_IGNORE_PARAMETER         =        -1


#  ----------------------------------------------------------------------------
#   device enumeration
#  ----------------------------------------------------------------------------
IS_USE_DEVICE_ID             =       0x8000
IS_ALLOW_STARTER_FW_UPLOAD   =       0x10000

#  ----------------------------------------------------------------------------
#  AutoExit enable/disable
#  ----------------------------------------------------------------------------
IS_GET_AUTO_EXIT_ENABLED      =      0x8000
IS_DISABLE_AUTO_EXIT          =      0
IS_ENABLE_AUTO_EXIT           =      1


#  ----------------------------------------------------------------------------
#  live/freeze parameters
#  ----------------------------------------------------------------------------
IS_GET_LIVE                   =      0x8000

IS_WAIT                      =       0x0001
IS_DONT_WAIT                 =       0x0000
IS_FORCE_VIDEO_STOP          =       0x4000
IS_FORCE_VIDEO_START         =       0x4000
IS_USE_NEXT_MEM              =       0x8000


#  ----------------------------------------------------------------------------
#  video finish constants
#  ----------------------------------------------------------------------------
IS_VIDEO_NOT_FINISH         =        0
IS_VIDEO_FINISH             =        1


#  ----------------------------------------------------------------------------
#  bitmap render modes
#  ----------------------------------------------------------------------------
IS_GET_RENDER_MODE           =       0x8000

IS_RENDER_DISABLED           =       0x0000
IS_RENDER_NORMAL             =       0x0001
IS_RENDER_FIT_TO_WINDOW      =       0x0002
IS_RENDER_DOWNSCALE_1_2      =       0x0004
IS_RENDER_MIRROR_UPDOWN      =       0x0010
IS_RENDER_DOUBLE_HEIGHT      =       0x0020
IS_RENDER_HALF_HEIGHT        =       0x0040

IS_RENDER_PLANAR_COLOR_RED    =      0x0080
IS_RENDER_PLANAR_COLOR_GREEN  =      0x0100
IS_RENDER_PLANAR_COLOR_BLUE   =      0x0200

IS_RENDER_PLANAR_MONO_RED      =     0x0400
IS_RENDER_PLANAR_MONO_GREEN    =     0x0800
IS_RENDER_PLANAR_MONO_BLUE     =     0x1000

IS_USE_AS_DC_STRUCTURE         =     0x4000
IS_USE_AS_DC_HANDLE            =     0x8000

#  ----------------------------------------------------------------------------
#  external trigger modes
#  ----------------------------------------------------------------------------
IS_GET_EXTERNALTRIGGER       =       0x8000
IS_GET_TRIGGER_STATUS        =       0x8001
IS_GET_TRIGGER_MASK          =       0x8002
IS_GET_TRIGGER_INPUTS        =       0x8003
IS_GET_SUPPORTED_TRIGGER_MODE  =     0x8004
IS_GET_TRIGGER_COUNTER         =     0x8000

#  old defines for compatibility
IS_SET_TRIG_OFF            =         0x0000
IS_SET_TRIG_HI_LO          =         0x0001
IS_SET_TRIG_LO_HI          =         0x0002
IS_SET_TRIG_SOFTWARE       =         0x0008
IS_SET_TRIG_HI_LO_SYNC     =         0x0010
IS_SET_TRIG_LO_HI_SYNC     =         0x0020

IS_SET_TRIG_MASK           =         0x0100

#  New defines
IS_SET_TRIGGER_CONTINUOUS     =      0x1000
IS_SET_TRIGGER_OFF            =      IS_SET_TRIG_OFF
IS_SET_TRIGGER_HI_LO          =      (IS_SET_TRIGGER_CONTINUOUS | IS_SET_TRIG_HI_LO)
IS_SET_TRIGGER_LO_HI          =      (IS_SET_TRIGGER_CONTINUOUS | IS_SET_TRIG_LO_HI)
IS_SET_TRIGGER_SOFTWARE       =      (IS_SET_TRIGGER_CONTINUOUS | IS_SET_TRIG_SOFTWARE)
IS_SET_TRIGGER_HI_LO_SYNC     =      IS_SET_TRIG_HI_LO_SYNC
IS_SET_TRIGGER_LO_HI_SYNC     =      IS_SET_TRIG_LO_HI_SYNC
IS_SET_TRIGGER_PRE_HI_LO      =      (IS_SET_TRIGGER_CONTINUOUS | 0x0040)
IS_SET_TRIGGER_PRE_LO_HI      =      (IS_SET_TRIGGER_CONTINUOUS | 0x0080)

IS_GET_TRIGGER_DELAY          =      0x8000
IS_GET_MIN_TRIGGER_DELAY      =      0x8001
IS_GET_MAX_TRIGGER_DELAY      =      0x8002
IS_GET_TRIGGER_DELAY_GRANULARITY  =  0x8003


#  ----------------------------------------------------------------------------
#  Timing
#  ----------------------------------------------------------------------------
#  pixelclock
IS_GET_PIXEL_CLOCK           =       0x8000
IS_GET_DEFAULT_PIXEL_CLK     =       0x8001
IS_GET_PIXEL_CLOCK_INC       =       0x8005

#  frame rate
IS_GET_FRAMERATE              =      0x8000
IS_GET_DEFAULT_FRAMERATE      =      0x8001
#  exposure
IS_GET_EXPOSURE_TIME          =      0x8000
IS_GET_DEFAULT_EXPOSURE       =      0x8001
IS_GET_EXPOSURE_MIN_VALUE     =      0x8002
IS_GET_EXPOSURE_MAX_VALUE     =      0x8003
IS_GET_EXPOSURE_INCREMENT     =      0x8004
IS_GET_EXPOSURE_FINE_INCREMENT =     0x8005


#  ----------------------------------------------------------------------------
#  Gain definitions
#  ----------------------------------------------------------------------------
IS_GET_MASTER_GAIN          =        0x8000
IS_GET_RED_GAIN             =        0x8001
IS_GET_GREEN_GAIN           =        0x8002
IS_GET_BLUE_GAIN            =        0x8003
IS_GET_DEFAULT_MASTER       =        0x8004
IS_GET_DEFAULT_RED          =        0x8005
IS_GET_DEFAULT_GREEN        =        0x8006
IS_GET_DEFAULT_BLUE         =        0x8007
IS_GET_GAINBOOST            =        0x8008
IS_SET_GAINBOOST_ON         =        0x0001
IS_SET_GAINBOOST_OFF        =        0x0000
IS_GET_SUPPORTED_GAINBOOST  =        0x0002
IS_MIN_GAIN                 =        0
IS_MAX_GAIN                 =        100


#  ----------------------------------------------------------------------------
#  Gain factor definitions
#  ----------------------------------------------------------------------------
IS_GET_MASTER_GAIN_FACTOR   =        0x8000
IS_GET_RED_GAIN_FACTOR      =        0x8001
IS_GET_GREEN_GAIN_FACTOR    =        0x8002
IS_GET_BLUE_GAIN_FACTOR     =        0x8003
IS_SET_MASTER_GAIN_FACTOR   =        0x8004
IS_SET_RED_GAIN_FACTOR      =        0x8005
IS_SET_GREEN_GAIN_FACTOR    =        0x8006
IS_SET_BLUE_GAIN_FACTOR     =        0x8007
IS_GET_DEFAULT_MASTER_GAIN_FACTOR =  0x8008
IS_GET_DEFAULT_RED_GAIN_FACTOR    =  0x8009
IS_GET_DEFAULT_GREEN_GAIN_FACTOR  =  0x800a
IS_GET_DEFAULT_BLUE_GAIN_FACTOR   =  0x800b
IS_INQUIRE_MASTER_GAIN_FACTOR     =  0x800c
IS_INQUIRE_RED_GAIN_FACTOR        =  0x800d
IS_INQUIRE_GREEN_GAIN_FACTOR      =  0x800e
IS_INQUIRE_BLUE_GAIN_FACTOR       =  0x800f


#  ----------------------------------------------------------------------------
#  Global Shutter definitions
#  ----------------------------------------------------------------------------
IS_SET_GLOBAL_SHUTTER_ON       =     0x0001
IS_SET_GLOBAL_SHUTTER_OFF      =     0x0000
IS_GET_GLOBAL_SHUTTER          =     0x0010
IS_GET_SUPPORTED_GLOBAL_SHUTTER  =   0x0020


#  ----------------------------------------------------------------------------
#  Black level definitions
#  ----------------------------------------------------------------------------
IS_GET_BL_COMPENSATION         =     0x8000
IS_GET_BL_OFFSET               =     0x8001
IS_GET_BL_DEFAULT_MODE         =     0x8002
IS_GET_BL_DEFAULT_OFFSET       =     0x8003
IS_GET_BL_SUPPORTED_MODE       =     0x8004

IS_BL_COMPENSATION_DISABLE     =     0
IS_BL_COMPENSATION_ENABLE      =     1
IS_BL_COMPENSATION_OFFSET      =     32

IS_MIN_BL_OFFSET               =     0
IS_MAX_BL_OFFSET               =     255

#  ----------------------------------------------------------------------------
#  hardware gamma definitions
#  ----------------------------------------------------------------------------
IS_GET_HW_GAMMA                =     0x8000
IS_GET_HW_SUPPORTED_GAMMA      =     0x8001

IS_SET_HW_GAMMA_OFF            =     0x0000
IS_SET_HW_GAMMA_ON             =     0x0001

#  ----------------------------------------------------------------------------
#  camera LUT
#  ----------------------------------------------------------------------------
IS_ENABLE_CAMERA_LUT           =         0x0001
IS_SET_CAMERA_LUT_VALUES       =         0x0002
IS_ENABLE_RGB_GRAYSCALE        =         0x0004
IS_GET_CAMERA_LUT_USER         =         0x0008
IS_GET_CAMERA_LUT_COMPLETE     =         0x0010
IS_GET_CAMERA_LUT_SUPPORTED_CHANNELS =   0x0020

#  ----------------------------------------------------------------------------
#  camera LUT presets
#  ----------------------------------------------------------------------------
IS_CAMERA_LUT_IDENTITY        =      0x00000100
IS_CAMERA_LUT_NEGATIV         =      0x00000200
IS_CAMERA_LUT_GLOW1           =      0x00000400
IS_CAMERA_LUT_GLOW2           =      0x00000800
IS_CAMERA_LUT_ASTRO1          =      0x00001000
IS_CAMERA_LUT_RAINBOW1        =      0x00002000
IS_CAMERA_LUT_MAP1            =      0x00004000
IS_CAMERA_LUT_COLD_HOT        =      0x00008000
IS_CAMERA_LUT_SEPIC           =      0x00010000
IS_CAMERA_LUT_ONLY_RED        =      0x00020000
IS_CAMERA_LUT_ONLY_GREEN      =      0x00040000
IS_CAMERA_LUT_ONLY_BLUE       =      0x00080000

IS_CAMERA_LUT_64              =      64
IS_CAMERA_LUT_128             =      128


#  ----------------------------------------------------------------------------
#  image parameters
#  ----------------------------------------------------------------------------
#  brightness
IS_GET_BRIGHTNESS           =        0x8000
IS_MIN_BRIGHTNESS           =        0
IS_MAX_BRIGHTNESS           =        255
IS_DEFAULT_BRIGHTNESS       =        -1
#  contrast
IS_GET_CONTRAST             =        0x8000
IS_MIN_CONTRAST             =        0
IS_MAX_CONTRAST             =        511
IS_DEFAULT_CONTRAST         =        -1
#  gamma
IS_GET_GAMMA                =        0x8000
IS_MIN_GAMMA                =        1
IS_MAX_GAMMA                =        1000
IS_DEFAULT_GAMMA            =        -1
#  saturation   (Falcon)
IS_GET_SATURATION_U         =        0x8000
IS_MIN_SATURATION_U         =        0
IS_MAX_SATURATION_U         =        200
IS_DEFAULT_SATURATION_U     =        100
IS_GET_SATURATION_V         =        0x8001
IS_MIN_SATURATION_V         =        0
IS_MAX_SATURATION_V         =        200
IS_DEFAULT_SATURATION_V     =        100
#  hue  (Falcon)
IS_GET_HUE                  =        0x8000
IS_MIN_HUE                  =        0
IS_MAX_HUE                  =        255
IS_DEFAULT_HUE              =        128


#  ----------------------------------------------------------------------------
#  Image position and size
#  ----------------------------------------------------------------------------

#  deprecated defines
IS_GET_IMAGE_SIZE_X         =        0x8000
IS_GET_IMAGE_SIZE_Y         =        0x8001
IS_GET_IMAGE_SIZE_X_INC     =        0x8002
IS_GET_IMAGE_SIZE_Y_INC     =        0x8003
IS_GET_IMAGE_SIZE_X_MIN     =        0x8004
IS_GET_IMAGE_SIZE_Y_MIN     =        0x8005
IS_GET_IMAGE_SIZE_X_MAX     =        0x8006
IS_GET_IMAGE_SIZE_Y_MAX     =        0x8007

IS_GET_IMAGE_POS_X          =        0x8001
IS_GET_IMAGE_POS_Y          =        0x8002
IS_GET_IMAGE_POS_X_ABS      =        0xC001
IS_GET_IMAGE_POS_Y_ABS      =        0xC002
IS_GET_IMAGE_POS_X_INC      =        0xC003
IS_GET_IMAGE_POS_Y_INC      =        0xC004
IS_GET_IMAGE_POS_X_MIN      =        0xC005
IS_GET_IMAGE_POS_Y_MIN      =        0xC006
IS_GET_IMAGE_POS_X_MAX      =        0xC007
IS_GET_IMAGE_POS_Y_MAX      =        0xC008

IS_SET_IMAGE_POS_X_ABS      =        0x00010000
IS_SET_IMAGE_POS_Y_ABS      =        0x00010000
IS_SET_IMAGEPOS_X_ABS       =        0x8000
IS_SET_IMAGEPOS_Y_ABS       =        0x8000


#  Valid defines

#  Image
IS_AOI_IMAGE_SET_AOI        =        0x0001
IS_AOI_IMAGE_GET_AOI        =        0x0002
IS_AOI_IMAGE_SET_POS        =        0x0003
IS_AOI_IMAGE_GET_POS        =        0x0004
IS_AOI_IMAGE_SET_SIZE       =        0x0005
IS_AOI_IMAGE_GET_SIZE       =        0x0006
IS_AOI_IMAGE_GET_POS_MIN    =        0x0007
IS_AOI_IMAGE_GET_SIZE_MIN   =        0x0008
IS_AOI_IMAGE_GET_POS_MAX    =        0x0009
IS_AOI_IMAGE_GET_SIZE_MAX   =        0x0010
IS_AOI_IMAGE_GET_POS_INC    =        0x0011
IS_AOI_IMAGE_GET_SIZE_INC   =        0x0012
IS_AOI_IMAGE_GET_POS_X_ABS  =        0x0013
IS_AOI_IMAGE_GET_POS_Y_ABS  =        0x0014
IS_AOI_IMAGE_GET_ORIGINAL_AOI =      0x0015

IS_AOI_IMAGE_POS_ABSOLUTE  =         0x10000000

#  Fast move
IS_AOI_IMAGE_SET_POS_FAST   =        0x0020
IS_AOI_IMAGE_SET_POS_FAST_SUPPORTED = 0x0021

#  Auto features
IS_AOI_AUTO_BRIGHTNESS_SET_AOI   =   0x0030
IS_AOI_AUTO_BRIGHTNESS_GET_AOI   =   0x0031
IS_AOI_AUTO_WHITEBALANCE_SET_AOI =   0x0032
IS_AOI_AUTO_WHITEBALANCE_GET_AOI =   0x0033

#  Multi AOI
IS_AOI_MULTI_GET_SUPPORTED_MODES =   0x0100
IS_AOI_MULTI_SET_AOI             =   0x0200
IS_AOI_MULTI_GET_AOI             =   0x0400
IS_AOI_MULTI_DISABLE_AOI         =   0x0800
IS_AOI_MULTI_MODE_AXES           =   0x0001
IS_AOI_MULTI_MODE_X_Y_AXES       =   0x0001
IS_AOI_MULTI_MODE_Y_AXES         =   0x0002

#  AOI sequence
IS_AOI_SEQUENCE_GET_SUPPORTED    =   0x0050
IS_AOI_SEQUENCE_SET_PARAMS       =   0x0051
IS_AOI_SEQUENCE_GET_PARAMS       =   0x0052
IS_AOI_SEQUENCE_SET_ENABLE       =   0x0053
IS_AOI_SEQUENCE_GET_ENABLE       =   0x0054

IS_AOI_SEQUENCE_INDEX_AOI_1     =    0
IS_AOI_SEQUENCE_INDEX_AOI_2     =    1
IS_AOI_SEQUENCE_INDEX_AOI_3     =    2
IS_AOI_SEQUENCE_INDEX_AOI_4     =    4

#  ----------------------------------------------------------------------------
#  ROP effect constants
#  ----------------------------------------------------------------------------
IS_GET_ROP_EFFECT               =    0x8000
IS_GET_SUPPORTED_ROP_EFFECT     =    0x8001

IS_SET_ROP_NONE                 =    0
IS_SET_ROP_MIRROR_UPDOWN        =    8
IS_SET_ROP_MIRROR_UPDOWN_ODD    =    16
IS_SET_ROP_MIRROR_UPDOWN_EVEN   =    32
IS_SET_ROP_MIRROR_LEFTRIGHT     =    64


#  ----------------------------------------------------------------------------
#  Subsampling
#  ----------------------------------------------------------------------------
IS_GET_SUBSAMPLING               =       0x8000
IS_GET_SUPPORTED_SUBSAMPLING     =       0x8001
IS_GET_SUBSAMPLING_TYPE          =       0x8002
IS_GET_SUBSAMPLING_FACTOR_HORIZONTAL =   0x8004
IS_GET_SUBSAMPLING_FACTOR_VERTICAL  =    0x8008

IS_SUBSAMPLING_DISABLE              =    0x00

IS_SUBSAMPLING_2X_VERTICAL       =       0x0001
IS_SUBSAMPLING_2X_HORIZONTAL     =       0x0002
IS_SUBSAMPLING_4X_VERTICAL       =       0x0004
IS_SUBSAMPLING_4X_HORIZONTAL     =       0x0008
IS_SUBSAMPLING_3X_VERTICAL       =       0x0010
IS_SUBSAMPLING_3X_HORIZONTAL     =       0x0020
IS_SUBSAMPLING_5X_VERTICAL       =       0x0040
IS_SUBSAMPLING_5X_HORIZONTAL     =       0x0080
IS_SUBSAMPLING_6X_VERTICAL       =       0x0100
IS_SUBSAMPLING_6X_HORIZONTAL     =       0x0200
IS_SUBSAMPLING_8X_VERTICAL       =       0x0400
IS_SUBSAMPLING_8X_HORIZONTAL     =       0x0800
IS_SUBSAMPLING_16X_VERTICAL      =       0x1000
IS_SUBSAMPLING_16X_HORIZONTAL    =       0x2000

IS_SUBSAMPLING_COLOR             =       0x01
IS_SUBSAMPLING_MONO              =       0x02

IS_SUBSAMPLING_MASK_VERTICAL      =      (IS_SUBSAMPLING_2X_VERTICAL | IS_SUBSAMPLING_4X_VERTICAL | IS_SUBSAMPLING_3X_VERTICAL | IS_SUBSAMPLING_5X_VERTICAL | IS_SUBSAMPLING_6X_VERTICAL | IS_SUBSAMPLING_8X_VERTICAL | IS_SUBSAMPLING_16X_VERTICAL)
IS_SUBSAMPLING_MASK_HORIZONTAL    =      (IS_SUBSAMPLING_2X_HORIZONTAL | IS_SUBSAMPLING_4X_HORIZONTAL | IS_SUBSAMPLING_3X_HORIZONTAL | IS_SUBSAMPLING_5X_HORIZONTAL | IS_SUBSAMPLING_6X_HORIZONTAL | IS_SUBSAMPLING_8X_HORIZONTAL | IS_SUBSAMPLING_16X_HORIZONTAL)

#  Compatibility
IS_SUBSAMPLING_VERT             =        IS_SUBSAMPLING_2X_VERTICAL
IS_SUBSAMPLING_HOR              =        IS_SUBSAMPLING_2X_HORIZONTAL


#  ----------------------------------------------------------------------------
#  Binning
#  ----------------------------------------------------------------------------
IS_GET_BINNING                  =    0x8000
IS_GET_SUPPORTED_BINNING        =    0x8001
IS_GET_BINNING_TYPE             =    0x8002
IS_GET_BINNING_FACTOR_HORIZONTAL=    0x8004
IS_GET_BINNING_FACTOR_VERTICAL  =    0x8008

IS_BINNING_DISABLE              =    0x00

IS_BINNING_2X_VERTICAL          =    0x0001
IS_BINNING_2X_HORIZONTAL        =    0x0002
IS_BINNING_4X_VERTICAL          =    0x0004
IS_BINNING_4X_HORIZONTAL        =    0x0008
IS_BINNING_3X_VERTICAL          =    0x0010
IS_BINNING_3X_HORIZONTAL        =    0x0020
IS_BINNING_5X_VERTICAL          =    0x0040
IS_BINNING_5X_HORIZONTAL        =    0x0080
IS_BINNING_6X_VERTICAL          =    0x0100
IS_BINNING_6X_HORIZONTAL        =    0x0200
IS_BINNING_8X_VERTICAL          =    0x0400
IS_BINNING_8X_HORIZONTAL        =    0x0800
IS_BINNING_16X_VERTICAL         =    0x1000
IS_BINNING_16X_HORIZONTAL       =    0x2000

IS_BINNING_COLOR                =    0x01
IS_BINNING_MONO                 =    0x02

IS_BINNING_MASK_VERTICAL        =    (IS_BINNING_2X_VERTICAL | IS_BINNING_3X_VERTICAL | IS_BINNING_4X_VERTICAL | IS_BINNING_5X_VERTICAL | IS_BINNING_6X_VERTICAL | IS_BINNING_8X_VERTICAL | IS_BINNING_16X_VERTICAL)
IS_BINNING_MASK_HORIZONTAL      =    (IS_BINNING_2X_HORIZONTAL | IS_BINNING_3X_HORIZONTAL | IS_BINNING_4X_HORIZONTAL | IS_BINNING_5X_HORIZONTAL | IS_BINNING_6X_HORIZONTAL | IS_BINNING_8X_HORIZONTAL | IS_BINNING_16X_HORIZONTAL)

#  Compatibility
IS_BINNING_VERT                =     IS_BINNING_2X_VERTICAL
IS_BINNING_HOR                 =     IS_BINNING_2X_HORIZONTAL

#  ----------------------------------------------------------------------------
#  Auto Control Parameter
#  ----------------------------------------------------------------------------
IS_SET_ENABLE_AUTO_GAIN         =    0x8800
IS_GET_ENABLE_AUTO_GAIN         =    0x8801
IS_SET_ENABLE_AUTO_SHUTTER      =    0x8802
IS_GET_ENABLE_AUTO_SHUTTER      =    0x8803
IS_SET_ENABLE_AUTO_WHITEBALANCE =    0x8804
IS_GET_ENABLE_AUTO_WHITEBALANCE =    0x8805
IS_SET_ENABLE_AUTO_FRAMERATE    =    0x8806
IS_GET_ENABLE_AUTO_FRAMERATE    =    0x8807
IS_SET_ENABLE_AUTO_SENSOR_GAIN  =    0x8808
IS_GET_ENABLE_AUTO_SENSOR_GAIN  =    0x8809
IS_SET_ENABLE_AUTO_SENSOR_SHUTTER =  0x8810
IS_GET_ENABLE_AUTO_SENSOR_SHUTTER =  0x8811
IS_SET_ENABLE_AUTO_SENSOR_GAIN_SHUTTER = 0x8812
IS_GET_ENABLE_AUTO_SENSOR_GAIN_SHUTTER = 0x8813
IS_SET_ENABLE_AUTO_SENSOR_FRAMERATE    = 0x8814
IS_GET_ENABLE_AUTO_SENSOR_FRAMERATE    = 0x8815
IS_SET_ENABLE_AUTO_SENSOR_WHITEBALANCE = 0x8816
IS_GET_ENABLE_AUTO_SENSOR_WHITEBALANCE = 0x8817


IS_SET_AUTO_REFERENCE        =       0x8000
IS_GET_AUTO_REFERENCE        =       0x8001
IS_SET_AUTO_GAIN_MAX         =       0x8002
IS_GET_AUTO_GAIN_MAX         =       0x8003
IS_SET_AUTO_SHUTTER_MAX      =       0x8004
IS_GET_AUTO_SHUTTER_MAX      =       0x8005
IS_SET_AUTO_SPEED            =       0x8006
IS_GET_AUTO_SPEED            =       0x8007
IS_SET_AUTO_WB_OFFSET        =       0x8008
IS_GET_AUTO_WB_OFFSET        =       0x8009
IS_SET_AUTO_WB_GAIN_RANGE    =       0x800A
IS_GET_AUTO_WB_GAIN_RANGE    =       0x800B
IS_SET_AUTO_WB_SPEED         =       0x800C
IS_GET_AUTO_WB_SPEED         =       0x800D
IS_SET_AUTO_WB_ONCE          =       0x800E
IS_GET_AUTO_WB_ONCE          =       0x800F
IS_SET_AUTO_BRIGHTNESS_ONCE  =       0x8010
IS_GET_AUTO_BRIGHTNESS_ONCE  =       0x8011
IS_SET_AUTO_HYSTERESIS       =       0x8012
IS_GET_AUTO_HYSTERESIS       =       0x8013
IS_GET_AUTO_HYSTERESIS_RANGE =       0x8014
IS_SET_AUTO_WB_HYSTERESIS    =       0x8015
IS_GET_AUTO_WB_HYSTERESIS    =       0x8016
IS_GET_AUTO_WB_HYSTERESIS_RANGE =    0x8017
IS_SET_AUTO_SKIPFRAMES       =       0x8018
IS_GET_AUTO_SKIPFRAMES       =       0x8019
IS_GET_AUTO_SKIPFRAMES_RANGE =       0x801A
IS_SET_AUTO_WB_SKIPFRAMES    =       0x801B
IS_GET_AUTO_WB_SKIPFRAMES    =       0x801C
IS_GET_AUTO_WB_SKIPFRAMES_RANGE  =   0x801D
IS_SET_SENS_AUTO_SHUTTER_PHOTOM  =           0x801E
IS_SET_SENS_AUTO_GAIN_PHOTOM     =           0x801F
IS_GET_SENS_AUTO_SHUTTER_PHOTOM  =           0x8020
IS_GET_SENS_AUTO_GAIN_PHOTOM     =           0x8021
IS_GET_SENS_AUTO_SHUTTER_PHOTOM_DEF   =      0x8022
IS_GET_SENS_AUTO_GAIN_PHOTOM_DEF      =      0x8023
IS_SET_SENS_AUTO_CONTRAST_CORRECTION  =      0x8024
IS_GET_SENS_AUTO_CONTRAST_CORRECTION  =      0x8025
IS_GET_SENS_AUTO_CONTRAST_CORRECTION_RANGE = 0x8026
IS_GET_SENS_AUTO_CONTRAST_CORRECTION_INC   = 0x8027
IS_GET_SENS_AUTO_CONTRAST_CORRECTION_DEF   = 0x8028
IS_SET_SENS_AUTO_CONTRAST_FDT_AOI_ENABLE   = 0x8029
IS_GET_SENS_AUTO_CONTRAST_FDT_AOI_ENABLE   = 0x8030
IS_SET_SENS_AUTO_BACKLIGHT_COMP            = 0x8031
IS_GET_SENS_AUTO_BACKLIGHT_COMP            = 0x8032
IS_GET_SENS_AUTO_BACKLIGHT_COMP_RANGE      = 0x8033
IS_GET_SENS_AUTO_BACKLIGHT_COMP_INC        = 0x8034
IS_GET_SENS_AUTO_BACKLIGHT_COMP_DEF        = 0x8035
IS_SET_ANTI_FLICKER_MODE                   = 0x8036
IS_GET_ANTI_FLICKER_MODE                   = 0x8037
IS_GET_ANTI_FLICKER_MODE_DEF               = 0x8038

#  ----------------------------------------------------------------------------
#  Auto Control definitions
#  ----------------------------------------------------------------------------
IS_MIN_AUTO_BRIGHT_REFERENCE    =      0
IS_MAX_AUTO_BRIGHT_REFERENCE    =    255
IS_DEFAULT_AUTO_BRIGHT_REFERENCE =   128
IS_MIN_AUTO_SPEED                =     0
IS_MAX_AUTO_SPEED                =   100
IS_DEFAULT_AUTO_SPEED            =    50

IS_DEFAULT_AUTO_WB_OFFSET     =        0
IS_MIN_AUTO_WB_OFFSET         =      -50
IS_MAX_AUTO_WB_OFFSET         =       50
IS_DEFAULT_AUTO_WB_SPEED      =       50
IS_MIN_AUTO_WB_SPEED          =        0
IS_MAX_AUTO_WB_SPEED          =      100
IS_MIN_AUTO_WB_REFERENCE      =        0
IS_MAX_AUTO_WB_REFERENCE      =      255


#  ----------------------------------------------------------------------------
#  AOI types to set/get
#  ----------------------------------------------------------------------------
IS_SET_AUTO_BRIGHT_AOI      =        0x8000
IS_GET_AUTO_BRIGHT_AOI      =        0x8001
IS_SET_IMAGE_AOI            =        0x8002
IS_GET_IMAGE_AOI            =        0x8003
IS_SET_AUTO_WB_AOI          =        0x8004
IS_GET_AUTO_WB_AOI          =        0x8005


#  ----------------------------------------------------------------------------
#  color modes
#  ----------------------------------------------------------------------------
IS_GET_COLOR_MODE       =            0x8000

IS_SET_CM_RGB32        =             0
IS_SET_CM_RGB24        =             1
IS_SET_CM_RGB16        =             2
IS_SET_CM_RGB15        =             3
IS_SET_CM_Y8           =             6
IS_SET_CM_RGB8         =             7
IS_SET_CM_BAYER        =             11
IS_SET_CM_UYVY         =             12
IS_SET_CM_UYVY_MONO    =             13
IS_SET_CM_UYVY_BAYER   =             14
IS_SET_CM_CBYCRY       =             23

IS_SET_CM_RGBY         =             24
IS_SET_CM_RGB30        =             25
IS_SET_CM_Y12          =             26
IS_SET_CM_BAYER12      =             27
IS_SET_CM_Y16          =             28
IS_SET_CM_BAYER16      =             29

IS_CM_MODE_MASK        =             0x007F

#  planar vs packed format
IS_CM_FORMAT_PACKED        =         0x0000
IS_CM_FORMAT_PLANAR        =         0x2000
IS_CM_FORMAT_MASK          =         0x2000

#  BGR vs. RGB order
IS_CM_ORDER_BGR          =           0x0000
IS_CM_ORDER_RGB          =           0x0080
IS_CM_ORDER_MASK          =          0x0080


#  define compliant color format names
IS_CM_MONO8          =       IS_SET_CM_Y8                                              #  occupies 8 Bit
IS_CM_MONO12         =       IS_SET_CM_Y12                                             #  occupies 16 Bit
IS_CM_MONO16         =       IS_SET_CM_Y16                                             #  occupies 16 Bit

IS_CM_BAYER_RG8      =       IS_SET_CM_BAYER                                           #  occupies 8 Bit
IS_CM_BAYER_RG12     =       IS_SET_CM_BAYER12                                         #  occupies 16 Bit
IS_CM_BAYER_RG16     =       IS_SET_CM_BAYER16                                         #  occupies 16 Bit

IS_CM_SENSOR_RAW8    =       IS_SET_CM_BAYER                                           #  occupies 8 Bit
IS_CM_SENSOR_RAW12   =       IS_SET_CM_BAYER12                                         #  occupies 16 Bit
IS_CM_SENSOR_RAW16   =       IS_SET_CM_BAYER16                                         #  occupies 16 Bit

IS_CM_BGR5_PACKED     =      (IS_SET_CM_RGB15 | IS_CM_ORDER_BGR | IS_CM_FORMAT_PACKED) #  occupies 16 Bit
IS_CM_BGR555_PACKED   =      (IS_SET_CM_RGB15 | IS_CM_ORDER_BGR | IS_CM_FORMAT_PACKED) #  occupies 16 Bit
IS_CM_BGR565_PACKED   =      (IS_SET_CM_RGB16 | IS_CM_ORDER_BGR | IS_CM_FORMAT_PACKED) #  occupies 16 Bit

IS_CM_RGB8_PACKED     =      (IS_SET_CM_RGB24 | IS_CM_ORDER_RGB | IS_CM_FORMAT_PACKED) #  occupies 24 Bit
IS_CM_BGR8_PACKED     =      (IS_SET_CM_RGB24 | IS_CM_ORDER_BGR | IS_CM_FORMAT_PACKED) #  occupies 24 Bit
IS_CM_RGBA8_PACKED    =      (IS_SET_CM_RGB32 | IS_CM_ORDER_RGB | IS_CM_FORMAT_PACKED) #  occupies 32 Bit
IS_CM_BGRA8_PACKED    =      (IS_SET_CM_RGB32 | IS_CM_ORDER_BGR | IS_CM_FORMAT_PACKED) #  occupies 32 Bit
IS_CM_RGBY8_PACKED    =      (IS_SET_CM_RGBY  | IS_CM_ORDER_RGB | IS_CM_FORMAT_PACKED) #  occupies 32 Bit
IS_CM_BGRY8_PACKED    =      (IS_SET_CM_RGBY  | IS_CM_ORDER_BGR | IS_CM_FORMAT_PACKED) #  occupies 32 Bit
IS_CM_RGB10V2_PACKED  =      (IS_SET_CM_RGB30 | IS_CM_ORDER_RGB | IS_CM_FORMAT_PACKED) #  occupies 32 Bit
IS_CM_BGR10V2_PACKED  =      (IS_SET_CM_RGB30 | IS_CM_ORDER_BGR | IS_CM_FORMAT_PACKED) #  occupies 32 Bit

IS_CM_RGB10_PACKED    =      (25 | IS_CM_ORDER_RGB | IS_CM_FORMAT_PACKED)
IS_CM_BGR10_PACKED    =      (25 | IS_CM_ORDER_BGR | IS_CM_FORMAT_PACKED)

IS_CM_RGB12_PACKED    =      (30 | IS_CM_ORDER_RGB | IS_CM_FORMAT_PACKED)              #  occupies 48 Bit
IS_CM_BGR12_PACKED    =      (30 | IS_CM_ORDER_BGR | IS_CM_FORMAT_PACKED)              #  occupies 48 Bit
IS_CM_RGBA12_PACKED   =      (31 | IS_CM_ORDER_RGB | IS_CM_FORMAT_PACKED)              #  occupies 64 Bit
IS_CM_BGRA12_PACKED   =      (31 | IS_CM_ORDER_BGR | IS_CM_FORMAT_PACKED)              #  occupies 64 Bit

IS_CM_YUV422_PACKED    =     1 # no compliant version
IS_CM_UYVY_PACKED      =     (IS_SET_CM_UYVY | IS_CM_FORMAT_PACKED)                    #  occupies 16 Bit
IS_CM_UYVY_MONO_PACKED =     (IS_SET_CM_UYVY_MONO | IS_CM_FORMAT_PACKED)
IS_CM_UYVY_BAYER_PACKED=     (IS_SET_CM_UYVY_BAYER | IS_CM_FORMAT_PACKED)
IS_CM_CBYCRY_PACKED    =     (IS_SET_CM_CBYCRY | IS_CM_FORMAT_PACKED)                  #  occupies 16 Bit

IS_CM_RGB8_PLANAR      =     (1 | IS_CM_ORDER_RGB | IS_CM_FORMAT_PLANAR)
IS_CM_RGB12_PLANAR     =     1 # no compliant version
IS_CM_RGB16_PLANAR     =     1 # no compliant version


IS_CM_ALL_POSSIBLE      =    0xFFFF
IS_CM_MODE_MASK         =    0x007F

#  ----------------------------------------------------------------------------
#  Hotpixel correction
#  ----------------------------------------------------------------------------

#  Deprecated defines
IS_GET_BPC_MODE               =       0x8000
IS_GET_BPC_THRESHOLD          =       0x8001
IS_GET_BPC_SUPPORTED_MODE     =       0x8002

IS_BPC_DISABLE            =           0
IS_BPC_ENABLE_LEVEL_1     =           1
IS_BPC_ENABLE_LEVEL_2     =           2
IS_BPC_ENABLE_USER        =           4
IS_BPC_ENABLE_SOFTWARE    =      IS_BPC_ENABLE_LEVEL_2
IS_BPC_ENABLE_HARDWARE    =      IS_BPC_ENABLE_LEVEL_1

IS_SET_BADPIXEL_LIST      =           0x01
IS_GET_BADPIXEL_LIST      =           0x02
IS_GET_LIST_SIZE          =           0x03


#  Valid defines
IS_HOTPIXEL_DISABLE_CORRECTION              =    0x0000
IS_HOTPIXEL_ENABLE_SENSOR_CORRECTION        =    0x0001
IS_HOTPIXEL_ENABLE_CAMERA_CORRECTION        =    0x0002
IS_HOTPIXEL_ENABLE_SOFTWARE_USER_CORRECTION =    0x0004

IS_HOTPIXEL_GET_CORRECTION_MODE             =    0x8000
IS_HOTPIXEL_GET_SUPPORTED_CORRECTION_MODES  =    0x8001

IS_HOTPIXEL_GET_SOFTWARE_USER_LIST_EXISTS   =    0x8100
IS_HOTPIXEL_GET_SOFTWARE_USER_LIST_NUMBER   =    0x8101
IS_HOTPIXEL_GET_SOFTWARE_USER_LIST          =    0x8102
IS_HOTPIXEL_SET_SOFTWARE_USER_LIST          =    0x8103
IS_HOTPIXEL_SAVE_SOFTWARE_USER_LIST         =    0x8104
IS_HOTPIXEL_LOAD_SOFTWARE_USER_LIST         =    0x8105

IS_HOTPIXEL_GET_CAMERA_FACTORY_LIST_EXISTS  =    0x8106
IS_HOTPIXEL_GET_CAMERA_FACTORY_LIST_NUMBER  =    0x8107
IS_HOTPIXEL_GET_CAMERA_FACTORY_LIST         =    0x8108

IS_HOTPIXEL_GET_CAMERA_USER_LIST_EXISTS     =    0x8109
IS_HOTPIXEL_GET_CAMERA_USER_LIST_NUMBER     =    0x810A
IS_HOTPIXEL_GET_CAMERA_USER_LIST            =    0x810B
IS_HOTPIXEL_SET_CAMERA_USER_LIST            =    0x810C
IS_HOTPIXEL_GET_CAMERA_USER_LIST_MAX_NUMBER =    0x810D
IS_HOTPIXEL_DELETE_CAMERA_USER_LIST         =    0x810E

IS_HOTPIXEL_GET_MERGED_CAMERA_LIST_NUMBER   =    0x810F
IS_HOTPIXEL_GET_MERGED_CAMERA_LIST          =    0x8110

IS_HOTPIXEL_SAVE_SOFTWARE_USER_LIST_UNICODE =    0x8111
IS_HOTPIXEL_LOAD_SOFTWARE_USER_LIST_UNICODE =    0x8112

#  ----------------------------------------------------------------------------
#  color correction definitions
#  ----------------------------------------------------------------------------
IS_GET_CCOR_MODE              =      0x8000
IS_GET_SUPPORTED_CCOR_MODE    =      0x8001
IS_GET_DEFAULT_CCOR_MODE      =      0x8002
IS_GET_CCOR_FACTOR            =      0x8003
IS_GET_CCOR_FACTOR_MIN        =      0x8004
IS_GET_CCOR_FACTOR_MAX        =      0x8005
IS_GET_CCOR_FACTOR_DEFAULT    =      0x8006

IS_CCOR_DISABLE               =      0x0000
IS_CCOR_ENABLE                =      0x0001
IS_CCOR_ENABLE_NORMAL         =  IS_CCOR_ENABLE
IS_CCOR_ENABLE_BG40_ENHANCED  =      0x0002
IS_CCOR_ENABLE_HQ_ENHANCED    =      0x0004
IS_CCOR_SET_IR_AUTOMATIC      =      0x0080
IS_CCOR_FACTOR                =      0x0100

IS_CCOR_ENABLE_MASK          =   (IS_CCOR_ENABLE_NORMAL | IS_CCOR_ENABLE_BG40_ENHANCED | IS_CCOR_ENABLE_HQ_ENHANCED)


#  ----------------------------------------------------------------------------
#  bayer algorithm modes
#  ----------------------------------------------------------------------------
IS_GET_BAYER_CV_MODE         =       0x8000

IS_SET_BAYER_CV_NORMAL        =      0x0000
IS_SET_BAYER_CV_BETTER       =       0x0001
IS_SET_BAYER_CV_BEST        =        0x0002


#  ----------------------------------------------------------------------------
#  color converter modes
#  ----------------------------------------------------------------------------
IS_CONV_MODE_NONE           =        0x0000
IS_CONV_MODE_SOFTWARE       =        0x0001
IS_CONV_MODE_SOFTWARE_3X3   =        0x0002
IS_CONV_MODE_SOFTWARE_5X5   =        0x0004
IS_CONV_MODE_HARDWARE_3X3   =        0x0008
IS_CONV_MODE_OPENCL_3X3     =        0x0020
IS_CONV_MODE_OPENCL_5X5     =        0x0040

#  ----------------------------------------------------------------------------
#  Edge enhancement
#  ----------------------------------------------------------------------------
IS_GET_EDGE_ENHANCEMENT     =        0x8000

IS_EDGE_EN_DISABLE          =        0
IS_EDGE_EN_STRONG           =        1
IS_EDGE_EN_WEAK             =        2


#  ----------------------------------------------------------------------------
#  white balance modes
#  ----------------------------------------------------------------------------
IS_GET_WB_MODE              =        0x8000

IS_SET_WB_DISABLE           =        0x0000
IS_SET_WB_USER              =        0x0001
IS_SET_WB_AUTO_ENABLE       =        0x0002
IS_SET_WB_AUTO_ENABLE_ONCE  =        0x0004

IS_SET_WB_DAYLIGHT_65       =        0x0101
IS_SET_WB_COOL_WHITE        =        0x0102
IS_SET_WB_U30               =        0x0103
IS_SET_WB_ILLUMINANT_A      =        0x0104
IS_SET_WB_HORIZON           =        0x0105


#  ----------------------------------------------------------------------------
#  flash strobe constants
#  ----------------------------------------------------------------------------
IS_GET_FLASHSTROBE_MODE         =    0x8000
IS_GET_FLASHSTROBE_LINE         =    0x8001
IS_GET_SUPPORTED_FLASH_IO_PORTS =    0x8002

IS_SET_FLASH_OFF         =           0
IS_SET_FLASH_ON          =           1
IS_SET_FLASH_LO_ACTIVE   =       IS_SET_FLASH_ON
IS_SET_FLASH_HI_ACTIVE   =           2
IS_SET_FLASH_HIGH        =           3
IS_SET_FLASH_LOW         =           4
IS_SET_FLASH_LO_ACTIVE_FREERUN  =    5
IS_SET_FLASH_HI_ACTIVE_FREERUN  =    6
IS_SET_FLASH_IO_1        =           0x0010
IS_SET_FLASH_IO_2        =           0x0020
IS_SET_FLASH_IO_3        =           0x0040
IS_SET_FLASH_IO_4        =           0x0080
IS_FLASH_IO_PORT_MASK    =       (IS_SET_FLASH_IO_1 | IS_SET_FLASH_IO_2 | IS_SET_FLASH_IO_3 | IS_SET_FLASH_IO_4)

IS_GET_FLASH_DELAY        =          -1
IS_GET_FLASH_DURATION     =          -2
IS_GET_MAX_FLASH_DELAY    =          -3
IS_GET_MAX_FLASH_DURATION =          -4
IS_GET_MIN_FLASH_DELAY    =          -5
IS_GET_MIN_FLASH_DURATION =          -6
IS_GET_FLASH_DELAY_GRANULARITY =     -7
IS_GET_FLASH_DURATION_GRANULARITY =  -8

#  ----------------------------------------------------------------------------
#  Digital IO constants
#  ----------------------------------------------------------------------------
IS_GET_IO                   =        0x8000
IS_GET_IO_MASK              =        0x8000
IS_GET_INPUT_MASK           =        0x8001
IS_GET_OUTPUT_MASK          =        0x8002
IS_GET_SUPPORTED_IO_PORTS   =        0x8004


#  ----------------------------------------------------------------------------
#  EEPROM defines
#  ----------------------------------------------------------------------------
IS_EEPROM_MIN_USER_ADDRESS    =      0
IS_EEPROM_MAX_USER_ADDRESS    =      63
IS_EEPROM_MAX_USER_SPACE      =      64


#  ----------------------------------------------------------------------------
#  error report modes
#  ----------------------------------------------------------------------------
IS_GET_ERR_REP_MODE         =        0x8000
IS_ENABLE_ERR_REP           =        1
IS_DISABLE_ERR_REP          =        0


#  ----------------------------------------------------------------------------
#  display mode selectors
#  ----------------------------------------------------------------------------
IS_GET_DISPLAY_MODE         =        0x8000
IS_GET_DISPLAY_SIZE_X       =        0x8000
IS_GET_DISPLAY_SIZE_Y       =        0x8001
IS_GET_DISPLAY_POS_X        =        0x8000
IS_GET_DISPLAY_POS_Y        =        0x8001

IS_SET_DM_DIB               =        1
IS_SET_DM_DIRECTDRAW        =        2
IS_SET_DM_DIRECT3D          =        4
IS_SET_DM_OPENGL            =        8

IS_SET_DM_ALLOW_SYSMEM      =        0x40
IS_SET_DM_ALLOW_PRIMARY     =        0x80

#  -- overlay display mode ---
IS_GET_DD_OVERLAY_SCALE     =        0x8000

IS_SET_DM_ALLOW_OVERLAY     =        0x100
IS_SET_DM_ALLOW_SCALING     =        0x200
IS_SET_DM_ALLOW_FIELDSKIP   =        0x400
IS_SET_DM_MONO              =        0x800
IS_SET_DM_BAYER             =        0x1000
IS_SET_DM_YCBCR             =        0x4000

#  -- backbuffer display mode ---
IS_SET_DM_BACKBUFFER        =        0x2000


#  ----------------------------------------------------------------------------
#  DirectRenderer commands
#  ----------------------------------------------------------------------------
DR_GET_OVERLAY_DC            =           1
DR_GET_MAX_OVERLAY_SIZE      =           2
DR_GET_OVERLAY_KEY_COLOR     =           3
DR_RELEASE_OVERLAY_DC        =           4
DR_SHOW_OVERLAY              =           5
DR_HIDE_OVERLAY              =           6
DR_SET_OVERLAY_SIZE          =           7
DR_SET_OVERLAY_POSITION      =           8
DR_SET_OVERLAY_KEY_COLOR     =           9
DR_SET_HWND                  =           10
DR_ENABLE_SCALING            =           11
DR_DISABLE_SCALING           =           12
DR_CLEAR_OVERLAY             =           13
DR_ENABLE_SEMI_TRANSPARENT_OVERLAY =     14
DR_DISABLE_SEMI_TRANSPARENT_OVERLAY=     15
DR_CHECK_COMPATIBILITY       =           16
DR_SET_VSYNC_OFF             =           17
DR_SET_VSYNC_AUTO            =           18
DR_SET_USER_SYNC             =           19
DR_GET_USER_SYNC_POSITION_RANGE     =    20
DR_LOAD_OVERLAY_FROM_FILE    =           21
DR_STEAL_NEXT_FRAME          =           22
DR_SET_STEAL_FORMAT          =           23
DR_GET_STEAL_FORMAT          =           24
DR_ENABLE_IMAGE_SCALING      =           25
DR_GET_OVERLAY_SIZE          =           26
DR_CHECK_COLOR_MODE_SUPPORT  =           27
DR_GET_OVERLAY_DATA         =           28
DR_UPDATE_OVERLAY_DATA  =               29
DR_GET_SUPPORTED         =               30

#  ----------------------------------------------------------------------------
#  DirectDraw keying color constants
#  ----------------------------------------------------------------------------
IS_GET_KC_RED          =             0x8000
IS_GET_KC_GREEN        =             0x8001
IS_GET_KC_BLUE         =             0x8002
IS_GET_KC_RGB          =             0x8003
IS_GET_KC_INDEX        =             0x8004
IS_GET_KEYOFFSET_X     =             0x8000
IS_GET_KEYOFFSET_Y     =             0x8001

#  RGB-triple for default key-color in 15,16,24,32 bit mode
IS_SET_KC_DEFAULT       =            0xFF00FF   #  0xbbggrr
#  color index for default key-color in 8bit palette mode
IS_SET_KC_DEFAULT_8     =            253


#  ----------------------------------------------------------------------------
#  Memoryboard
#  ----------------------------------------------------------------------------
IS_MEMORY_GET_COUNT      =           0x8000
IS_MEMORY_GET_DELAY      =           0x8001
IS_MEMORY_MODE_DISABLE   =           0x0000
IS_MEMORY_USE_TRIGGER    =           0xFFFF


#  ----------------------------------------------------------------------------
#  Test image modes
#  ----------------------------------------------------------------------------
IS_GET_TEST_IMAGE         =          0x8000

IS_SET_TEST_IMAGE_DISABLED   =       0x0000
IS_SET_TEST_IMAGE_MEMORY_1   =       0x0001
IS_SET_TEST_IMAGE_MEMORY_2   =       0x0002
IS_SET_TEST_IMAGE_MEMORY_3   =       0x0003


#  ----------------------------------------------------------------------------
#  Led settings
#  ----------------------------------------------------------------------------
IS_SET_LED_OFF         =             0
IS_SET_LED_ON          =             1
IS_SET_LED_TOGGLE      =             2
IS_GET_LED             =             0x8000


#  ----------------------------------------------------------------------------
#  save options
#  ----------------------------------------------------------------------------
IS_SAVE_USE_ACTUAL_IMAGE_SIZE  =     0x00010000

#  ----------------------------------------------------------------------------
#  renumeration modes
#  ----------------------------------------------------------------------------
IS_RENUM_BY_CAMERA        =          0
IS_RENUM_BY_HOST          =          1

#  ----------------------------------------------------------------------------
#  event constants
#  ----------------------------------------------------------------------------
IS_SET_EVENT_ODD               =         0
IS_SET_EVENT_EVEN              =         1
IS_SET_EVENT_FRAME             =         2
IS_SET_EVENT_EXTTRIG           =         3
IS_SET_EVENT_VSYNC             =         4
IS_SET_EVENT_SEQ               =         5
IS_SET_EVENT_STEAL             =         6
IS_SET_EVENT_VPRES             =         7
IS_SET_EVENT_TRANSFER_FAILED   =         8
IS_SET_EVENT_CAPTURE_STATUS    =         8
IS_SET_EVENT_DEVICE_RECONNECTED=         9
IS_SET_EVENT_MEMORY_MODE_FINISH=         10
IS_SET_EVENT_FRAME_RECEIVED    =         11
IS_SET_EVENT_WB_FINISHED       =         12
IS_SET_EVENT_AUTOBRIGHTNESS_FINISHED=    13
IS_SET_EVENT_OVERLAY_DATA_LOST     =     16
IS_SET_EVENT_CAMERA_MEMORY         =     17
IS_SET_EVENT_CONNECTIONSPEED_CHANGED =   18

IS_SET_EVENT_REMOVE            =         128
IS_SET_EVENT_REMOVAL           =         129
IS_SET_EVENT_NEW_DEVICE        =         130
IS_SET_EVENT_STATUS_CHANGED    =         131


#  ----------------------------------------------------------------------------
#  Window message defines
#  ----------------------------------------------------------------------------
WM_USER                     =      0x400
IS_UC480_MESSAGE            =      (WM_USER + 0x0100)
IS_FRAME                    =      0x0000
IS_SEQUENCE                 =      0x0001
IS_TRIGGER                  =      0x0002
IS_TRANSFER_FAILED          =      0x0003
IS_CAPTURE_STATUS           =      0x0003
IS_DEVICE_RECONNECTED       =      0x0004
IS_MEMORY_MODE_FINISH       =      0x0005
IS_FRAME_RECEIVED           =      0x0006
IS_GENERIC_ERROR            =      0x0007
IS_STEAL_VIDEO              =      0x0008
IS_WB_FINISHED              =      0x0009
IS_AUTOBRIGHTNESS_FINISHED  =      0x000A
IS_OVERLAY_DATA_LOST        =      0x000B
IS_CAMERA_MEMORY            =      0x000C
IS_CONNECTIONSPEED_CHANGED  =      0x000D

IS_DEVICE_REMOVED           =      0x1000
IS_DEVICE_REMOVAL           =      0x1001
IS_NEW_DEVICE               =      0x1002
IS_DEVICE_STATUS_CHANGED    =      0x1003


#  ----------------------------------------------------------------------------
#  camera id constants
#  ----------------------------------------------------------------------------
IS_GET_CAMERA_ID           =         0x8000


#  ----------------------------------------------------------------------------
#  camera info constants
#  ----------------------------------------------------------------------------
IS_GET_STATUS             =          0x8000

IS_EXT_TRIGGER_EVENT_CNT    =        0
IS_FIFO_OVR_CNT             =        1
IS_SEQUENCE_CNT             =        2
IS_LAST_FRAME_FIFO_OVR      =        3
IS_SEQUENCE_SIZE            =        4
IS_VIDEO_PRESENT            =        5
IS_STEAL_FINISHED           =        6
IS_STORE_FILE_PATH          =        7
IS_LUMA_BANDWIDTH_FILTER    =        8
IS_BOARD_REVISION           =        9
IS_MIRROR_BITMAP_UPDOWN     =        10
IS_BUS_OVR_CNT              =        11
IS_STEAL_ERROR_CNT          =        12
IS_LOW_COLOR_REMOVAL        =        13
IS_CHROMA_COMB_FILTER       =        14
IS_CHROMA_AGC               =        15
IS_WATCHDOG_ON_BOARD        =        16
IS_PASSTHROUGH_ON_BOARD     =        17
IS_EXTERNAL_VREF_MODE       =        18
IS_WAIT_TIMEOUT             =        19
IS_TRIGGER_MISSED           =        20
IS_LAST_CAPTURE_ERROR       =        21
IS_PARAMETER_SET_1          =        22
IS_PARAMETER_SET_2          =        23
IS_STANDBY                  =        24
IS_STANDBY_SUPPORTED        =        25
IS_QUEUED_IMAGE_EVENT_CNT   =        26
IS_PARAMETER_EXT            =        27


#  ----------------------------------------------------------------------------
#  interface type defines
#  ----------------------------------------------------------------------------
IS_INTERFACE_TYPE_USB      =         0x40
IS_INTERFACE_TYPE_USB3     =         0x60
IS_INTERFACE_TYPE_ETH      =         0x80

#  ----------------------------------------------------------------------------
#  board type defines
#  ----------------------------------------------------------------------------
IS_BOARD_TYPE_FALCON         =       1
IS_BOARD_TYPE_EAGLE          =       2
IS_BOARD_TYPE_FALCON2        =       3
IS_BOARD_TYPE_FALCON_PLUS    =       7
IS_BOARD_TYPE_FALCON_QUATTRO =       9
IS_BOARD_TYPE_FALCON_DUO     =       10
IS_BOARD_TYPE_EAGLE_QUATTRO  =       11
IS_BOARD_TYPE_EAGLE_DUO      =       12
IS_BOARD_TYPE_UC480_USB      =        (IS_INTERFACE_TYPE_USB + 0)      #  0x40
IS_BOARD_TYPE_UC480_USB_SE   =        IS_BOARD_TYPE_UC480_USB          #  0x40
IS_BOARD_TYPE_UC480_USB_RE   =        IS_BOARD_TYPE_UC480_USB          #  0x40
IS_BOARD_TYPE_UC480_USB_ME   =        (IS_INTERFACE_TYPE_USB + 0x01)   #  0x41
IS_BOARD_TYPE_UC480_USB_LE   =        (IS_INTERFACE_TYPE_USB + 0x02)   #  0x42
IS_BOARD_TYPE_UC480_USB_XS   =        (IS_INTERFACE_TYPE_USB + 0x03)   #  0x43
IS_BOARD_TYPE_UC480_USB_ML   =        (IS_INTERFACE_TYPE_USB + 0x05)   #  0x45

IS_BOARD_TYPE_UC480_USB3_CP  =        (IS_INTERFACE_TYPE_USB3 + 0x04)  #  0x64

IS_BOARD_TYPE_UC480_ETH      =        IS_INTERFACE_TYPE_ETH            #  0x80
IS_BOARD_TYPE_UC480_ETH_HE   =        IS_BOARD_TYPE_UC480_ETH          #  0x80
IS_BOARD_TYPE_UC480_ETH_SE   =        (IS_INTERFACE_TYPE_ETH + 0x01)   #  0x81
IS_BOARD_TYPE_UC480_ETH_RE   =        IS_BOARD_TYPE_UC480_ETH_SE       #  0x81
IS_BOARD_TYPE_UC480_ETH_CP   =        IS_BOARD_TYPE_UC480_ETH + 0x04   #  0x84

#  ----------------------------------------------------------------------------
#  camera type defines
#  ----------------------------------------------------------------------------
IS_CAMERA_TYPE_UC480_USB      =   IS_BOARD_TYPE_UC480_USB_SE
IS_CAMERA_TYPE_UC480_USB_SE   =   IS_BOARD_TYPE_UC480_USB_SE
IS_CAMERA_TYPE_UC480_USB_RE   =   IS_BOARD_TYPE_UC480_USB_RE
IS_CAMERA_TYPE_UC480_USB_ME   =   IS_BOARD_TYPE_UC480_USB_ME
IS_CAMERA_TYPE_UC480_USB_LE   =   IS_BOARD_TYPE_UC480_USB_LE
IS_CAMERA_TYPE_UC480_USB_ML   =   IS_BOARD_TYPE_UC480_USB_ML

IS_CAMERA_TYPE_UC480_USB3_CP  =   IS_BOARD_TYPE_UC480_USB3_CP

IS_CAMERA_TYPE_UC480_ETH      =   IS_BOARD_TYPE_UC480_ETH_HE
IS_CAMERA_TYPE_UC480_ETH_HE   =   IS_BOARD_TYPE_UC480_ETH_HE
IS_CAMERA_TYPE_UC480_ETH_SE   =   IS_BOARD_TYPE_UC480_ETH_SE
IS_CAMERA_TYPE_UC480_ETH_RE   =   IS_BOARD_TYPE_UC480_ETH_RE
IS_CAMERA_TYPE_UC480_ETH_CP   =   IS_BOARD_TYPE_UC480_ETH_CP

#  ----------------------------------------------------------------------------
#  readable operation system defines
#  ----------------------------------------------------------------------------
IS_OS_UNDETERMINED      =            0
IS_OS_WIN95             =            1
IS_OS_WINNT40           =            2
IS_OS_WIN98             =            3
IS_OS_WIN2000           =            4
IS_OS_WINXP             =            5
IS_OS_WINME             =            6
IS_OS_WINNET            =            7
IS_OS_WINSERVER2003     =            8
IS_OS_WINVISTA          =            9
IS_OS_LINUX24           =            10
IS_OS_LINUX26           =            11
IS_OS_WIN7              =            12
IS_OS_WIN8              =            13


#  ----------------------------------------------------------------------------
#  Bus speed
#  ----------------------------------------------------------------------------
IS_USB_10                 =          0x0001 #   1,5 Mb/s
IS_USB_11                 =          0x0002 #    12 Mb/s
IS_USB_20                 =          0x0004 #   480 Mb/s
IS_USB_30                 =          0x0008 #  4000 Mb/s
IS_ETHERNET_10            =          0x0080 #    10 Mb/s
IS_ETHERNET_100           =          0x0100 #   100 Mb/s
IS_ETHERNET_1000          =          0x0200 #  1000 Mb/s
IS_ETHERNET_10000         =          0x0400 # 10000 Mb/s

IS_USB_LOW_SPEED          =          1
IS_USB_FULL_SPEED         =          12
IS_USB_HIGH_SPEED         =          480
IS_USB_SUPER_SPEED        =          4000
IS_ETHERNET_10Base        =          10
IS_ETHERNET_100Base       =          100
IS_ETHERNET_1000Base      =          1000
IS_ETHERNET_10GBase       =          10000

#  ----------------------------------------------------------------------------
#  HDR
#  ----------------------------------------------------------------------------
IS_HDR_NOT_SUPPORTED      =          0
IS_HDR_KNEEPOINTS         =          1
IS_DISABLE_HDR            =          0
IS_ENABLE_HDR             =          1


#  ----------------------------------------------------------------------------
#  Test images
#  ----------------------------------------------------------------------------
IS_TEST_IMAGE_NONE                   =       0x00000000
IS_TEST_IMAGE_WHITE                  =       0x00000001
IS_TEST_IMAGE_BLACK                  =       0x00000002
IS_TEST_IMAGE_HORIZONTAL_GREYSCALE   =       0x00000004
IS_TEST_IMAGE_VERTICAL_GREYSCALE     =       0x00000008
IS_TEST_IMAGE_DIAGONAL_GREYSCALE     =       0x00000010
IS_TEST_IMAGE_WEDGE_GRAY             =       0x00000020
IS_TEST_IMAGE_WEDGE_COLOR            =       0x00000040
IS_TEST_IMAGE_ANIMATED_WEDGE_GRAY    =       0x00000080

IS_TEST_IMAGE_ANIMATED_WEDGE_COLOR   =       0x00000100
IS_TEST_IMAGE_MONO_BARS              =       0x00000200
IS_TEST_IMAGE_COLOR_BARS1            =       0x00000400
IS_TEST_IMAGE_COLOR_BARS2            =       0x00000800
IS_TEST_IMAGE_GREYSCALE1             =       0x00001000
IS_TEST_IMAGE_GREY_AND_COLOR_BARS    =       0x00002000
IS_TEST_IMAGE_MOVING_GREY_AND_COLOR_BARS =   0x00004000
IS_TEST_IMAGE_ANIMATED_LINE           =      0x00008000

IS_TEST_IMAGE_ALTERNATE_PATTERN        =     0x00010000
IS_TEST_IMAGE_VARIABLE_GREY            =     0x00020000
IS_TEST_IMAGE_MONOCHROME_HORIZONTAL_BARS =   0x00040000
IS_TEST_IMAGE_MONOCHROME_VERTICAL_BARS  =    0x00080000
IS_TEST_IMAGE_CURSOR_H                =      0x00100000
IS_TEST_IMAGE_CURSOR_V                =      0x00200000
IS_TEST_IMAGE_COLDPIXEL_GRID          =      0x00400000
IS_TEST_IMAGE_HOTPIXEL_GRID           =      0x00800000

IS_TEST_IMAGE_VARIABLE_RED_PART       =      0x01000000
IS_TEST_IMAGE_VARIABLE_GREEN_PART     =      0x02000000
IS_TEST_IMAGE_VARIABLE_BLUE_PART      =      0x04000000
IS_TEST_IMAGE_SHADING_IMAGE           =      0x08000000
IS_TEST_IMAGE_WEDGE_GRAY_SENSOR       =      0x10000000
#                                                   0x20000000
#                                                   0x40000000
#                                                   0x80000000


#  ----------------------------------------------------------------------------
#  Sensor scaler
#  ----------------------------------------------------------------------------
IS_ENABLE_SENSOR_SCALER     =        1
IS_ENABLE_ANTI_ALIASING     =        2


#  ----------------------------------------------------------------------------
#  Timeouts
#  ----------------------------------------------------------------------------
IS_TRIGGER_TIMEOUT         =         0


#  ----------------------------------------------------------------------------
#  Auto pixel clock modes
#  ----------------------------------------------------------------------------
IS_BEST_PCLK_RUN_ONCE      =         0

#  ----------------------------------------------------------------------------
#  sequence flags
#  ----------------------------------------------------------------------------
IS_LOCK_LAST_BUFFER          =      0x8002
IS_GET_ALLOC_ID_OF_THIS_BUF  =       0x8004
IS_GET_ALLOC_ID_OF_LAST_BUF  =       0x8008
IS_USE_ALLOC_ID              =       0x8000
IS_USE_CURRENT_IMG_SIZE      =       0xC000

#  ------------------------------------------
#  Memory information flags
#  ------------------------------------------
IS_GET_D3D_MEM             =         0x8000

#  ----------------------------------------------------------------------------
#  Image files types
#  ----------------------------------------------------------------------------
IS_IMG_BMP              =            0
IS_IMG_JPG              =            1
IS_IMG_PNG              =            2
IS_IMG_RAW              =            4
IS_IMG_TIF              =            8

#  ----------------------------------------------------------------------------
#  I2C defines
#  nRegisterAddr | IS_I2C_16_BIT_REGISTER
#  ----------------------------------------------------------------------------
IS_I2C_16_BIT_REGISTER      =        0x10000000
IS_I2C_0_BIT_REGISTER       =        0x20000000

#  nDeviceAddr | IS_I2C_DONT_WAIT
IS_I2C_DONT_WAIT            =        0x00800000


#  ----------------------------------------------------------------------------
#  DirectDraw steal video constants   (Falcon)
#  ----------------------------------------------------------------------------
IS_INIT_STEAL_VIDEO             =    1
IS_EXIT_STEAL_VIDEO             =    2
IS_INIT_STEAL_VIDEO_MANUAL      =    3
IS_INIT_STEAL_VIDEO_AUTO        =    4
IS_SET_STEAL_RATIO              =    64
IS_USE_MEM_IMAGE_SIZE           =    128
IS_STEAL_MODES_MASK             =    7
IS_SET_STEAL_COPY               =    0x1000
IS_SET_STEAL_NORMAL             =    0x2000

#  ----------------------------------------------------------------------------
#  AGC modes   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_AGC_MODE              =       0x8000
IS_SET_AGC_OFF               =       0
IS_SET_AGC_ON                =       1


#  ----------------------------------------------------------------------------
#  Gamma modes   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_GAMMA_MODE             =      0x8000
IS_SET_GAMMA_OFF              =      0
IS_SET_GAMMA_ON               =      1


#  ----------------------------------------------------------------------------
#  sync levels   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_SYNC_LEVEL            =       0x8000
IS_SET_SYNC_75               =       0
IS_SET_SYNC_125              =       1


#  ----------------------------------------------------------------------------
#  color bar modes   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_CBARS_MODE      =             0x8000
IS_SET_CBARS_OFF       =             0
IS_SET_CBARS_ON        =             1


#  ----------------------------------------------------------------------------
#  horizontal filter defines   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_HOR_FILTER_MODE      =        0x8000
IS_GET_HOR_FILTER_STEP      =        0x8001

IS_DISABLE_HOR_FILTER       =        0
IS_ENABLE_HOR_FILTER        =        1
def IS_HOR_FILTER_STEP(_s_):
    return (_s_ + 1) << 1
IS_HOR_FILTER_STEP1         =        2
IS_HOR_FILTER_STEP2         =        4
IS_HOR_FILTER_STEP3         =        6


#  ----------------------------------------------------------------------------
#  vertical filter defines   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_VERT_FILTER_MODE    =         0x8000
IS_GET_VERT_FILTER_STEP    =         0x8001

IS_DISABLE_VERT_FILTER     =         0
IS_ENABLE_VERT_FILTER      =         1
def IS_VERT_FILTER_STEP(_s_):
    return (_s_ + 1) << 1
IS_VERT_FILTER_STEP1       =         2
IS_VERT_FILTER_STEP2       =         4
IS_VERT_FILTER_STEP3       =         6


#  ----------------------------------------------------------------------------
#  scaler modes   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_SCALER_MODE   =       float( 1000)
IS_SET_SCALER_OFF    =       float( 0)
IS_SET_SCALER_ON     =       float( 1)

IS_MIN_SCALE_X       =       float(   6.25)
IS_MAX_SCALE_X       =       float( 100.00)
IS_MIN_SCALE_Y       =       float(   6.25)
IS_MAX_SCALE_Y       =       float( 100.00)


#  ----------------------------------------------------------------------------
#  video source selectors   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_VIDEO_IN            =         0x8000
IS_GET_VIDEO_PASSTHROUGH   =         0x8000
IS_GET_VIDEO_IN_TOGGLE     =         0x8001
IS_GET_TOGGLE_INPUT_1      =         0x8000
IS_GET_TOGGLE_INPUT_2      =         0x8001
IS_GET_TOGGLE_INPUT_3      =         0x8002
IS_GET_TOGGLE_INPUT_4      =         0x8003

IS_SET_VIDEO_IN_1          =         0x00
IS_SET_VIDEO_IN_2          =         0x01
IS_SET_VIDEO_IN_S          =         0x02
IS_SET_VIDEO_IN_3          =         0x03
IS_SET_VIDEO_IN_4          =         0x04
IS_SET_VIDEO_IN_1S         =         0x10
IS_SET_VIDEO_IN_2S         =         0x11
IS_SET_VIDEO_IN_3S         =         0x13
IS_SET_VIDEO_IN_4S         =         0x14
IS_SET_VIDEO_IN_EXT        =         0x40
IS_SET_TOGGLE_OFF          =         0xFF
IS_SET_VIDEO_IN_SYNC       =         0x4000


#  ----------------------------------------------------------------------------
#  video crossbar selectors   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_CROSSBAR            =         0x8000

IS_CROSSBAR_1              =         0
IS_CROSSBAR_2              =         1
IS_CROSSBAR_3              =         2
IS_CROSSBAR_4              =         3
IS_CROSSBAR_5              =         4
IS_CROSSBAR_6              =         5
IS_CROSSBAR_7              =         6
IS_CROSSBAR_8              =         7
IS_CROSSBAR_9              =         8
IS_CROSSBAR_10             =         9
IS_CROSSBAR_11             =         10
IS_CROSSBAR_12             =         11
IS_CROSSBAR_13             =         12
IS_CROSSBAR_14             =         13
IS_CROSSBAR_15             =         14
IS_CROSSBAR_16             =         15
IS_SELECT_AS_INPUT         =         128


#  ----------------------------------------------------------------------------
#  video format selectors   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_VIDEO_MODE          =         0x8000

IS_SET_VM_PAL              =         0
IS_SET_VM_NTSC             =         1
IS_SET_VM_SECAM            =         2
IS_SET_VM_AUTO             =         3


#  ----------------------------------------------------------------------------
#  capture modes   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_CAPTURE_MODE         =        0x8000

IS_SET_CM_ODD               =        0x0001
IS_SET_CM_EVEN              =        0x0002
IS_SET_CM_FRAME             =        0x0004
IS_SET_CM_NONINTERLACED     =        0x0008
IS_SET_CM_NEXT_FRAME        =        0x0010
IS_SET_CM_NEXT_FIELD        =        0x0020
IS_SET_CM_BOTHFIELDS        =    (IS_SET_CM_ODD | IS_SET_CM_EVEN | IS_SET_CM_NONINTERLACED)
IS_SET_CM_FRAME_STEREO      =        0x2004


#  ----------------------------------------------------------------------------
#  display update mode constants   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_UPDATE_MODE           =       0x8000
IS_SET_UPDATE_TIMER          =       1
IS_SET_UPDATE_EVENT          =       2


#  ----------------------------------------------------------------------------
#  sync generator mode constants   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_SYNC_GEN        =             0x8000
IS_SET_SYNC_GEN_OFF    =             0
IS_SET_SYNC_GEN_ON     =             1


#  ----------------------------------------------------------------------------
#  decimation modes   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_DECIMATION_MODE   =           0x8000
IS_GET_DECIMATION_NUMBER =           0x8001

IS_DECIMATION_OFF         =          0
IS_DECIMATION_CONSECUTIVE =          1
IS_DECIMATION_DISTRIBUTED =          2


#  ----------------------------------------------------------------------------
#  hardware watchdog defines   (Falcon)
#  ----------------------------------------------------------------------------
IS_GET_WATCHDOG_TIME       =         0x2000
IS_GET_WATCHDOG_RESOLUTION =         0x4000
IS_GET_WATCHDOG_ENABLE     =         0x8000

IS_WATCHDOG_MINUTES        =         0
IS_WATCHDOG_SECONDS        =         0x8000
IS_DISABLE_WATCHDOG        =         0
IS_ENABLE_WATCHDOG         =         1
IS_RETRIGGER_WATCHDOG          =     2
IS_ENABLE_AUTO_DEACTIVATION    =     4
IS_DISABLE_AUTO_DEACTIVATION   =     8
IS_WATCHDOG_RESERVED           =     0x1000


#  ----------------------------------------------------------------------------
#  typedefs
#  ----------------------------------------------------------------------------
HCAM = wt.DWORD

#  ----------------------------------------------------------------------------
#  invalid values for device handles
#  ----------------------------------------------------------------------------
IS_INVALID_HCAM = 0


class BOARDINFO(ctypes.Structure):
    """
    :var ctypes.c_char[12] SerNo: Serial number of sensor chip.
    :var ctypes.c_char[20] ID: Camera ID.
    :var ctypes.c_char[10] Version:
    :var ctypes.c_char[12] Date:
    :var ctypes.c_ubyte Select:
    :var ctypes.c_ubyte Type:
    :var ctypes.c_char[8] Reserved:
    """
    _fields_ = [("SerNo", ctypes.c_char * 12),
                ("ID", ctypes.c_char * 20),
                ("Version", ctypes.c_char * 10),
                ("Date", ctypes.c_char * 12),
                ("Select", ctypes.c_ubyte),
                ("Type", ctypes.c_ubyte),
                ("Reserved", ctypes.c_char * 8)]

#  ----------------------------------------------------------------------------
#  info struct
#  ----------------------------------------------------------------------------
FALCINFO  = BOARDINFO
PFALCINFO = ctypes.POINTER(BOARDINFO)
CAMINFO   = BOARDINFO
PCAMINFO  = ctypes.POINTER(BOARDINFO)

class SENSORINFO(ctypes.Structure):
    """
    :var WORD SensorID:
    :var ctypes.c_char[32] strSensorName:
    :var BYTE nColorMode:
    :var DWORD nMaxWidth:
    :var DWORD nMaxHeight:
    :var BOOL bMasterGain:
    :var BOOL bRGain:
    :var BOOL bGGain:
    :var BOOL bBGain:
    :var WORD wPixelSize:
    :var ctypes.c_char[14] Reserved:
    """
    _fields_ = [("SensorID", wt.WORD),
                ("strSensorName", ctypes.c_char * 32),
                ("nColorMode", wt.BYTE),
                ("nMaxWidth", wt.DWORD),
                ("nMaxHeight", wt.DWORD),
                ("bMasterGain", wt.BOOL),
                ("bRGain", wt.BOOL),
                ("bGGain", wt.BOOL),
                ("bBGain", wt.BOOL),
                ("wPixelSize", wt.WORD),
                ("Reserved", ctypes.c_char * 14)]

class REVISIONINFO(ctypes.Structure):
    """
    :var WORD size:
    :var WORD Sensor:
    :var WORD Cypress:
    :var WORD Blackfin:
    :var WORD DspFirmware:
    :var WORD USB_Board:
    :var WORD Sensor_Board:
    :var WORD Processing_Board:
    :var WORD Memory_Board:
    :var WORD Housing:
    :var WORD Filter:
    :var WORD Timing_Board:
    :var WORD Product:
    :var WORD Power_Board:
    :var WORD Power_Board:
    :var WORD Logic_Board:
    :var WORD FX3:
    :var WORD FPGA:
    :var ctypes.c_char[92] Reserved:
    """
    _fields_ = [("size", wt.WORD),
                ("Sensor", wt.WORD),
                ("Cypress", wt.WORD),
                ("Blackfin", wt.DWORD),
                ("DspFirmware", wt.WORD),
                ("USB_Board", wt.WORD),
                ("Sensor_Board", wt.WORD),
                ("Processing_Board", wt.WORD),
                ("Memory_Board", wt.WORD),
                ("Housing", wt.WORD),
                ("Filter", wt.WORD),
                ("Timing_Board", wt.WORD),

                ("Product", wt.WORD),
                ("Power_Board", wt.WORD),
                ("Logic_Board", wt.WORD),
                ("FX3", wt.WORD),
                ("FPGA", wt.WORD),
                ("Reserved", ctypes.c_char * 92)]

#  ----------------------------------------------------------------------------
#  Capture errors
#  ----------------------------------------------------------------------------
IS_CAPERR_API_NO_DEST_MEM=              0xa2
IS_CAPERR_API_CONVERSION_FAILED=        0xa3
IS_CAPERR_API_IMAGE_LOCKED=             0xa5
IS_CAPERR_DRV_OUT_OF_BUFFERS=           0xb2
IS_CAPERR_DRV_DEVICE_NOT_READY=         0xb4
IS_CAPERR_USB_TRANSFER_FAILED=          0xc7
IS_CAPERR_DEV_TIMEOUT=                  0xd6
IS_CAPERR_ETH_BUFFER_OVERRUN=           0xe4
IS_CAPERR_ETH_MISSED_IMAGES=            0xe5

class UC480_CAPTURE_ERROR_INFO(ctypes.Structure):
    """
    :var DWORD dwCapErrCnt_Total:
    :var BYTE[60] reserved:
    :var DWORD[256] adwCapErrCnt_Detail:
    """
    _fields_ = [("dwCapErrCnt_Total", wt.DWORD),
                ("reserved", wt.BYTE * 60),
                ("adwCapErrCnt_Detail", wt.DWORD * 256)]    #: Attributes

IS_CAP_STATUS_API_NO_DEST_MEM       =   0xa2
IS_CAP_STATUS_API_CONVERSION_FAILED =   0xa3
IS_CAP_STATUS_API_IMAGE_LOCKED      =   0xa5
IS_CAP_STATUS_DRV_OUT_OF_BUFFERS    =   0xb2
IS_CAP_STATUS_DRV_DEVICE_NOT_READY  =   0xb4
IS_CAP_STATUS_USB_TRANSFER_FAILED   =   0xc7
IS_CAP_STATUS_DEV_TIMEOUT           =   0xd6
IS_CAP_STATUS_ETH_BUFFER_OVERRUN    =   0xe4
IS_CAP_STATUS_ETH_MISSED_IMAGES     =   0xe5

class UC480_CAPTURE_STATUS_INFO(ctypes.Structure):
    """
    :var DWORD dwCapStatusCnt_Total:
    :var BYTE[60] reserved:
    :var DWORD[256] adwCapStatusCnt_Detail:
    """
    _fields_ = [("dwCapStatusCnt_Total", wt.DWORD),
                ("reserved", wt.BYTE * 60),
                ("adwCapStatusCnt_Detail", wt.DWORD * 256)]

IS_CAPTURE_STATUS_INFO_CMD_RESET = 1
IS_CAPTURE_STATUS_INFO_CMD_GET   = 2

class UC480_CAMERA_INFO(ctypes.Structure):
    """
    :var DWORD dwCameraID:
    :var DWORD dwDeviceID:
    :var DWORD dwSensorID:
    :var DWORD dwInUse:
    :var ctypes.c_char[16] SerNo:
    :var ctypes.c_char[16] Model:
    :var DWORD dwStatus:
    :var DWORD[15] dwReserved:
    """
    _fields_ = [("dwCameraID", wt.DWORD),
                ("dwDeviceID", wt.DWORD),
                ("dwSensorID", wt.DWORD),
                ("dwInUse", wt.DWORD),
                ("SerNo", ctypes.c_char * 16),
                ("Model", ctypes.c_char * 16),
                ("dwStatus", wt.DWORD),
                ("dwReserved", wt.DWORD * 15)]

#  usage of the list:
#  1. call the DLL with .dwCount = 0
#  2. DLL returns .dwCount = N  (N = number of available cameras)
#  3. call DLL with .dwCount = N and a pointer to UC480_CAMERA_LIST with
#     and array of UC480_CAMERA_INFO[N]
#  4. DLL will fill in the array with the camera infos and
#     will update the .dwCount member with the actual number of cameras
#     because there may be a change in number of cameras between step 2 and 3
#  5. check if there's a difference in actual .dwCount and formerly
#     reported value of N and call DLL again with an updated array size

# class UC480_CAMERA_LIST(ctypes.Structure):
    # _fields_ = [("dwCount", wt.ULONG),
                # ("uci", ctypes.POINTER(UC480_CAMERA_INFO))]

def create_camera_list(dwCount):
    """Returns an instance of the UC480_CAMERA_LIST structure having the properly scaled UC480_CAMERA_INFO array.

    :param ULONG dwCount: Number of camera info structures requested.
    :returns: UC480_CAMERA_LIST

    :var ULONG dwCount: Size of uci.
    :var UC480_CAMERA_INFO[dwCount] uci: List of camera info structures.
    """
    class UC480_CAMERA_LIST(ctypes.Structure):
        _fields_ = [("dwCount", wt.ULONG),
                    ("uci", UC480_CAMERA_INFO * dwCount)]
    a_list = UC480_CAMERA_LIST()
    a_list.dwCount = dwCount
    return a_list

#  ----------------------------------------------------------------------------
#  the  following defines are the status bits of the dwStatus member of
#  the UC480_CAMERA_INFO structure
FIRMWARE_DOWNLOAD_NOT_SUPPORTED       =          0x00000001
INTERFACE_SPEED_NOT_SUPPORTED         =          0x00000002
INVALID_SENSOR_DETECTED               =          0x00000004
AUTHORIZATION_FAILED                  =          0x00000008
DEVSTS_INCLUDED_STARTER_FIRMWARE_INCOMPATIBLE =  0x00000010

#  the following macro determines the availability of the camera based
#  on the status flags
def IS_CAMERA_AVAILABLE(_s_):
    return (((_s_ & FIRMWARE_DOWNLOAD_NOT_SUPPORTED) == 0)
            and ((_s_ & INTERFACE_SPEED_NOT_SUPPORTED) == 0)
            and ((_s_ & INVALID_SENSOR_DETECTED) == 0)
            and ((_s_ & AUTHORIZATION_FAILED) == 0))

#  ----------------------------------------------------------------------------
#  auto feature structs and definitions
#  ----------------------------------------------------------------------------
AC_SHUTTER              =    0x00000001
AC_GAIN                =     0x00000002
AC_WHITEBAL            =     0x00000004
AC_WB_RED_CHANNEL      =     0x00000008
AC_WB_GREEN_CHANNEL    =     0x00000010
AC_WB_BLUE_CHANNEL     =     0x00000020
AC_FRAMERATE           =     0x00000040
AC_SENSOR_SHUTTER      =     0x00000080
AC_SENSOR_GAIN         =     0x00000100
AC_SENSOR_GAIN_SHUTTER =     0x00000200
AC_SENSOR_FRAMERATE    =     0x00000400
AC_SENSOR_WB           =     0x00000800
AC_SENSOR_AUTO_REFERENCE =   0x00001000
AC_SENSOR_AUTO_SPEED     =   0x00002000
AC_SENSOR_AUTO_HYSTERESIS=   0x00004000
AC_SENSOR_AUTO_SKIPFRAMES=   0x00008000

ACS_ADJUSTING          =     0x00000001
ACS_FINISHED           =     0x00000002
ACS_DISABLED           =     0x00000004


class AUTO_BRIGHT_STATUS(ctypes.Structure):
    """
    :var DWORD curValue:
    :var ctypes.c_long curError:
    :var DWORD curController:
    :var DWORD curCtrlStatus:
    """
    _fields_ = [("curValue", wt.DWORD),
                ("curError", ctypes.c_long),
                ("curController", wt.DWORD),
                ("curCtrlStatus", wt.DWORD)]

class AUTO_WB_CHANNNEL_STATUS(ctypes.Structure):
    """
    :var DWORD curValue:
    :var ctypes.c_long curError:
    :var DWORD curCtrlStatus:
    """
    _fields_ = [("curValue", wt.DWORD),
                ("curError", ctypes.c_long),
                ("curCtrlStatus", wt.DWORD)]

class AUTO_WB_STATUS(ctypes.Structure):
    """
    :var AUTO_WB_CHANNNEL_STATUS RedChannel:
    :var AUTO_WB_CHANNNEL_STATUS GreenChannel:
    :var AUTO_WB_CHANNNEL_STATUS BlueChannel:
    :var DWORD curController:
    """
    _fields_ = [("RedChannel", AUTO_WB_CHANNNEL_STATUS),
                ("GreenChannel", AUTO_WB_CHANNNEL_STATUS),
                ("BlueChannel", AUTO_WB_CHANNNEL_STATUS),
                ("curController", wt.DWORD)]

class UC480_AUTO_INFO(ctypes.Structure):
    """
    :var DWORD AutoAbility:
    :var AUTO_BRIGHT_STATUS sBrightCtrlStatus:
    :var AUTO_WB_STATUS sWBCtrlStatus:
    :var DWORD AShutterPhotomCaps:
    :var DWORD AGainPhotomCaps:
    :var DWORD AAntiFlickerCaps:
    :var DWORD SensorWBModeCaps:
    :var DWORD[8] reserved:
    """
    _fields_ = [("AutoAbility", wt.DWORD),
                ("sBrightCtrlStatus", AUTO_BRIGHT_STATUS),
                ("sWBCtrlStatus", AUTO_WB_STATUS),
                ("AShutterPhotomCaps", wt.DWORD),
                ("AGainPhotomCaps", wt.DWORD),
                ("AAntiFlickerCaps", wt.DWORD),
                ("SensorWBModeCaps", wt.DWORD),
                ("reserved", wt.DWORD * 8)]

class UC480_AUTO_INFO(ctypes.Structure):
    """
    :var ctypes.c_uint nSize:
    :var ctypes.c_void_p hDC:
    :var ctypes.c_uint nCx:
    :var ctypes.c_uint nCy:
    """
    _fields_ = [("nSize", ctypes.c_uint),
                ("hDC", ctypes.c_void_p),
                ("nCx", ctypes.c_uint),
                ("nCy", ctypes.c_uint)]

class KNEEPOINT(ctypes.Structure):
    """
    :var ctypes.c_double x:
    :var ctypes.c_double y:
    """
    _fields_ = [("x", ctypes.c_double),
                ("y", ctypes.c_double)]

class KNEEPOINTARRAY(ctypes.Structure):
    """
    :var ctypes.c_int NumberOfUsedKneepoints:
    :var KNEEPOINT[10] Kneepoint:
    """
    _fields_ = [("NumberOfUsedKneepoints", ctypes.c_int),
                ("Kneepoint", KNEEPOINT * 10)]

class KNEEPOINTINFO(ctypes.Structure):
    """
    :var ctypes.c_int NumberOfSupportedKneepoints:
    :var ctypes.c_int NumberOfUsedKneepoints:
    :var ctypes.c_double MinValueX:
    :var ctypes.c_double MaxValueX:
    :var ctypes.c_double MinValueY:
    :var ctypes.c_double MaxValueY:
    :var KNEEPOINT[10] DefaultKneepoint:
    :var ctypes.c_int[10] Reserved:
    """
    _fields_ = [("NumberOfSupportedKneepoints", ctypes.c_int),
                ("NumberOfUsedKneepoints", ctypes.c_int),
                ("MinValueX", ctypes.c_double),
                ("MaxValueX", ctypes.c_double),
                ("MinValueY", ctypes.c_double),
                ("MaxValueY", ctypes.c_double),
                ("DefaultKneepoint", KNEEPOINT * 10),
                ("Reserved", ctypes.c_int * 10)]


IS_SE_STARTER_FW_UPLOAD =   0x00000001 # !< get estimated duration of GigE SE starter firmware upload in milliseconds
IS_CP_STARTER_FW_UPLOAD =   0x00000002 # !< get estimated duration of GigE CP starter firmware upload in milliseconds
IS_STARTER_FW_UPLOAD    =   0x00000004  # !< get estimated duration of starter firmware upload in milliseconds using hCam to

class SENSORSCALERINFO(ctypes.Structure):
    """
    :var ctypes.c_int nCurrMode:
    :var ctypes.c_int nNumberOfSteps:
    :var ctypes.c_double dblFactorIncrement:
    :var ctypes.c_double dblMinFactor:
    :var ctypes.c_double dblMaxFactor:
    :var ctypes.c_double dblCurrFactor:
    :var ctypes.c_int nSupportedModes:
    :var ctypes.c_byte[84] bReserved:
    """
    _fields_ = [("nCurrMode", ctypes.c_int),
                ("nNumberOfSteps", ctypes.c_int),
                ("dblFactorIncrement", ctypes.c_double),
                ("dblMinFactor", ctypes.c_double),
                ("dblMaxFactor", ctypes.c_double),
                ("dblCurrFactor", ctypes.c_double),
                ("nSupportedModes", ctypes.c_int),
                ("bReserved", ctypes.c_byte * 84)]

class UC480TIME(ctypes.Structure):
    """
    :var WORD wYear:
    :var WORD wMonth:
    :var WORD wDay:
    :var WORD wHour:
    :var WORD wMinute:
    :var WORD wSecond:
    :var WORD wMilliseconds:
    :var BYTE[10] byReserved:
    """
    _fields_ = [("wYear", wt.WORD),
                ("wMonth", wt.WORD),
                ("wDay", wt.WORD),
                ("wHour", wt.WORD),
                ("wMinute", wt.WORD),
                ("wSecond", wt.WORD),
                ("wMilliseconds", wt.WORD),
                ("byReserved", wt.BYTE * 10)]


class UC480IMAGEINFO(ctypes.Structure):
    """
    :var DWORD dwFlags:
    :var BYTE[4] byReserved1:
    :var ctypes.c_ulonglong u64TimestampDevice:
    :var UC480TIME TimestampSystem:
    :var DWORD dwIoStatus:
    :var WORD wAOIIndex:
    :var WORD wAOICycle:
    :var ctypes.c_ulonglong u64FrameNumber:
    :var DWORD dwImageBuffers:
    :var DWORD dwImageBuffersInUse:
    :var DWORD dwReserved3:
    :var DWORD dwImageHeight:
    :var DWORD dwImageWidth:
    """
    _fields_ = [("dwFlags", wt.DWORD),
                ("byReserved1", wt.BYTE * 4),
                ("u64TimestampDevice", ctypes.c_ulonglong),
                ("TimestampSystem", UC480TIME),
                ("dwIoStatus", wt.DWORD),
                ("wAOIIndex", wt.WORD),
                ("wAOICycle", wt.WORD),
                ("u64FrameNumber", ctypes.c_ulonglong),
                ("dwImageBuffers", wt.DWORD),
                ("dwImageBuffersInUse", wt.DWORD),
                ("dwReserved3", wt.DWORD),
                ("dwImageHeight", wt.DWORD),
                ("dwImageWidth", wt.DWORD)]

#  ----------------------------------------------------------------------------
#  new functions and datatypes only valid for uc480 ETH
#  ----------------------------------------------------------------------------

class UC480_ETH_ADDR_IPV4_by(ctypes.Structure):
    """
    :var BYTE by1:
    :var BYTE by2:
    :var BYTE by3:
    :var BYTE by4:
    """
    _fields_ = [("by1", wt.BYTE),
                ("by2", wt.BYTE),
                ("by3", wt.BYTE),
                ("by4", wt.BYTE)]

class UC480_ETH_ADDR_IPV4(ctypes.Structure):
    """
    :var UC480_ETH_ADDR_IPV4_by by:
    :var DWORD dwAddr:
    """
    _fields_ = [("by", UC480_ETH_ADDR_IPV4_by),
                ("dwAddr", wt.DWORD)]

class UC480_ETH_ADDR_MAC(ctypes.Structure):
    """
    :var BYTE[6] abyOctet:
    """
    _fields_ = [("abyOctet", wt.BYTE * 6)]

class UC480_ETH_IP_CONFIGURATION(ctypes.Structure):
    """
    :var UC480_ETH_ADDR_IPV4 ipAddress:
    :var UC480_ETH_ADDR_IPV4 ipSubnetmask:
    :var BYTE reserved:
    """
    _fields_ = [("ipAddress", UC480_ETH_ADDR_IPV4),
                ("ipSubnetmask", UC480_ETH_ADDR_IPV4),
                ("reserved", wt.BYTE)]


IS_ETH_DEVSTATUS_READY_TO_OPERATE=            0x00000001 # !< device is ready to operate
IS_ETH_DEVSTATUS_TESTING_IP_CURRENT=          0x00000002 # !< device is (arp-)probing its current ip
IS_ETH_DEVSTATUS_TESTING_IP_PERSISTENT=       0x00000004 # !< device is (arp-)probing its persistent ip
IS_ETH_DEVSTATUS_TESTING_IP_RANGE=            0x00000008 # !< device is (arp-)probing the autocfg ip range

IS_ETH_DEVSTATUS_INAPPLICABLE_IP_CURRENT=     0x00000010 # !< current ip is inapplicable
IS_ETH_DEVSTATUS_INAPPLICABLE_IP_PERSISTENT=  0x00000020 # !< persistent ip is inapplicable
IS_ETH_DEVSTATUS_INAPPLICABLE_IP_RANGE=       0x00000040 # !< autocfg ip range is inapplicable

IS_ETH_DEVSTATUS_UNPAIRED=                    0x00000100 # !< device is unpaired
IS_ETH_DEVSTATUS_PAIRING_IN_PROGRESS=         0x00000200 # !< device is being paired
IS_ETH_DEVSTATUS_PAIRED=                      0x00000400 # !< device is paired

IS_ETH_DEVSTATUS_FORCE_100MBPS=               0x00001000 # !< device phy is configured to 100 Mbps
IS_ETH_DEVSTATUS_NO_COMPORT=                  0x00002000 # !< device does not support uc480 eth comport

IS_ETH_DEVSTATUS_RECEIVING_FW_STARTER=        0x00010000 # !< device is receiving the starter firmware
IS_ETH_DEVSTATUS_RECEIVING_FW_RUNTIME=        0x00020000 # !< device is receiving the runtime firmware
IS_ETH_DEVSTATUS_INAPPLICABLE_FW_RUNTIME=     0x00040000 # !< runtime firmware is inapplicable
IS_ETH_DEVSTATUS_INAPPLICABLE_FW_STARTER=     0x00080000 # !< starter firmware is inapplicable

IS_ETH_DEVSTATUS_REBOOTING_FW_RUNTIME=        0x00100000 # !< device is rebooting to runtime firmware
IS_ETH_DEVSTATUS_REBOOTING_FW_STARTER=        0x00200000 # !< device is rebooting to starter firmware
IS_ETH_DEVSTATUS_REBOOTING_FW_FAILSAFE=       0x00400000 # !< device is rebooting to failsafe firmware

IS_ETH_DEVSTATUS_RUNTIME_FW_ERR0=             0x80000000 # !< checksum error runtime firmware

#  heartbeat info transmitted periodically by a device
#  contained in UC480_ETH_DEVICE_INFO
class UC480_ETH_DEVICE_INFO_HEARTBEAT(ctypes.Structure):
    """
    :var BYTE[12] abySerialNumber:
    :var BYTE byDeviceType:
    :var BYTE byCameraID:
    :var WORD wSensorID:
    :var WORD wSizeImgMem_MB:
    :var BYTE[2] reserved_1:
    :var DWORD dwVerStarterFirmware:
    :var DWORD dwVerRuntimeFirmware:
    :var DWORD dwStatus:
    :var BYTE[4] reserved_2:
    :var WORD wTemperature:
    :var WORD wLinkSpeed_Mb:
    :var UC480_ETH_ADDR_MAC macDevice:
    :var WORD wComportOffset:
    :var UC480_ETH_IP_CONFIGURATION ipcfgPersistentIpCfg:
    :var UC480_ETH_IP_CONFIGURATION ipcfgCurrentIpCfg:
    :var UC480_ETH_ADDR_MAC macPairedHost:
    :var BYTE[2] reserved_4:
    :var UC480_ETH_ADDR_IPV4 ipPairedHostIp:
    :var UC480_ETH_ADDR_IPV4 ipAutoCfgIpRangeBegin:
    :var UC480_ETH_ADDR_IPV4 ipAutoCfgIpRangeEnd:
    :var BYTE[8] abyUserSpace:
    :var BYTE[84] reserved_5:
    :var BYTE[64] reserved_6:
    """
    _fields_ = [("abySerialNumber", wt.BYTE * 12),
                ("byDeviceType", wt.BYTE),
                ("byCameraID", wt.BYTE),
                ("wSensorID", wt.WORD),
                ("wSizeImgMem_MB", wt.WORD),
                ("reserved_1", wt.BYTE * 2),
                ("dwVerStarterFirmware", wt.DWORD),
                ("dwVerRuntimeFirmware", wt.DWORD),
                ("dwStatus", wt.DWORD),
                ("reserved_2", wt.BYTE * 4),
                ("wTemperature", wt.WORD),
                ("wLinkSpeed_Mb", wt.WORD),
                ("macDevice", UC480_ETH_ADDR_MAC),
                ("wComportOffset", wt.WORD),
                ("ipcfgPersistentIpCfg", UC480_ETH_IP_CONFIGURATION),
                ("ipcfgCurrentIpCfg", UC480_ETH_IP_CONFIGURATION),
                ("macPairedHost", UC480_ETH_ADDR_MAC),
                ("reserved_4", wt.BYTE * 2),
                ("ipPairedHostIp", UC480_ETH_ADDR_IPV4),
                ("ipAutoCfgIpRangeBegin", UC480_ETH_ADDR_IPV4),
                ("ipAutoCfgIpRangeEnd", UC480_ETH_ADDR_IPV4),
                ("abyUserSpace", wt.BYTE * 8),
                ("reserved_5", wt.BYTE * 84),
                ("reserved_6", wt.BYTE * 64)]

IS_ETH_CTRLSTATUS_AVAILABLE=              0x00000001 # !< device is available TO US
IS_ETH_CTRLSTATUS_ACCESSIBLE1=            0x00000002 # !< device is accessible BY US, i.e. directly 'unicastable'
IS_ETH_CTRLSTATUS_ACCESSIBLE2=            0x00000004 # !< device is accessible BY US, i.e. not on persistent ip and adapters ip autocfg range is valid

IS_ETH_CTRLSTATUS_PERSISTENT_IP_USED=     0x00000010 # !< device is running on persistent ip configuration
IS_ETH_CTRLSTATUS_COMPATIBLE=             0x00000020 # !< device is compatible TO US
IS_ETH_CTRLSTATUS_ADAPTER_ON_DHCP=        0x00000040 # !< adapter is configured to use dhcp
IS_ETH_CTRLSTATUS_ADAPTER_SETUP_OK =      0x00000080 # !< adapter's setup is ok with respect to uc480 needs

IS_ETH_CTRLSTATUS_UNPAIRING_IN_PROGRESS=  0x00000100 # !< device is being unpaired FROM US
IS_ETH_CTRLSTATUS_PAIRING_IN_PROGRESS=    0x00000200 # !< device is being paired TO US

IS_ETH_CTRLSTATUS_PAIRED=                 0x00001000 # !< device is paired TO US
IS_ETH_CTRLSTATUS_OPENED =                0x00004000 # !< device is opened BY SELF

IS_ETH_CTRLSTATUS_FW_UPLOAD_STARTER=      0x00010000 # !< device is receiving the starter firmware
IS_ETH_CTRLSTATUS_FW_UPLOAD_RUNTIME=      0x00020000 # !< device is receiving the runtime firmware

IS_ETH_CTRLSTATUS_REBOOTING=              0x00100000 # !< device is rebooting

IS_ETH_CTRLSTATUS_BOOTBOOST_ENABLED =     0x01000000 # !< boot-boosting is enabled for this device
IS_ETH_CTRLSTATUS_BOOTBOOST_ACTIVE =      0x02000000 # !< boot-boosting is active for this device
IS_ETH_CTRLSTATUS_INITIALIZED=            0x08000000 # !< device object is initialized

IS_ETH_CTRLSTATUS_TO_BE_DELETED=          0x40000000 # !< device object is being deleted
IS_ETH_CTRLSTATUS_TO_BE_REMOVED=          0x80000000 # !< device object is being removed

class UC480_ETH_DEVICE_INFO_CONTROL(ctypes.Structure):
    """
    :var DWORD dwDeviceID:
    :var DWORD dwControlStatus:
    :var BYTE[80] reserved_1:
    :var BYTE[64] reserved_2:
    """
    _fields_ = [("dwDeviceID", wt.DWORD),
                ("dwControlStatus", wt.DWORD),
                ("reserved_1", wt.BYTE * 80),
                ("reserved_2", wt.BYTE * 64)]

class UC480_ETH_ETHERNET_CONFIGURATION(ctypes.Structure):
    """
    :var UC480_ETH_IP_CONFIGURATION ipcfg:
    :var UC480_ETH_ADDR_MAC mac:
    """
    _fields_ = [("ipcfg", UC480_ETH_IP_CONFIGURATION),
                ("mac", UC480_ETH_ADDR_MAC)]

class UC480_ETH_AUTOCFG_IP_SETUP(ctypes.Structure):
    """
    :var UC480_ETH_ADDR_IPV4 ipAutoCfgIpRangeBegin:
    :var UC480_ETH_ADDR_IPV4 ipAutoCfgIpRangeEnd:
    :var BYTE[4] reserved:
    """
    _fields_ = [("ipAutoCfgIpRangeBegin", UC480_ETH_ADDR_IPV4),
                ("ipAutoCfgIpRangeEnd", UC480_ETH_ADDR_IPV4),
                ("reserved", wt.BYTE * 4)]

#  values for incoming packets filter setup
IS_ETH_PCKTFLT_PASSALL=       0  # !< pass all packets to OS
IS_ETH_PCKTFLT_BLOCKUEGET=    1  # !< block UEGET packets to the OS
IS_ETH_PCKTFLT_BLOCKALL=      2  # !< block all packets to the OS

#  values for link speed setup
IS_ETH_LINKSPEED_100MB=       100    # !< 100 MBits
IS_ETH_LINKSPEED_1000MB=      1000    # !< 1000 MBits

#  control info for a device's network adapter
#  contained in UC480_ETH_DEVICE_INFO
class UC480_ETH_ADAPTER_INFO(ctypes.Structure):
    """
    :var DWORD dwAdapterID:
    :var DWORD dwDeviceLinkspeed:
    :var UC480_ETH_ETHERNET_CONFIGURATION ethcfg:
    :var BYTE[2] reserved_2:
    :var BOOL bIsEnabledDHCP:
    :var UC480_ETH_AUTOCFG_IP_SETUP autoCfgIp:
    :var BOOL bIsValidAutoCfgIpRange:
    :var DWORD dwCntDevicesKnown:
    :var DWORD dwCntDevicesPaired:
    :var WORD wPacketFilter:
    :var BYTE[38] reserved_3:
    :var BYTE[64] reserved_4:
    """
    _fields_ = [("dwAdapterID", wt.DWORD),
                ("dwDeviceLinkspeed", wt.DWORD),
                ("ethcfg", UC480_ETH_ETHERNET_CONFIGURATION),
                ("reserved_2", wt.BYTE * 2),
                ("bIsEnabledDHCP", wt.BOOL),
                ("autoCfgIp", UC480_ETH_AUTOCFG_IP_SETUP),
                ("bIsValidAutoCfgIpRange", wt.BOOL),
                ("dwCntDevicesKnown", wt.DWORD),
                ("dwCntDevicesPaired", wt.DWORD),
                ("wPacketFilter", wt.WORD),
                ("reserved_3", wt.BYTE * 38),
                ("reserved_4", wt.BYTE * 64)]

#  driver info
#  contained in UC480_ETH_DEVICE_INFO
class UC480_ETH_DRIVER_INFO(ctypes.Structure):
    """
    :var DWORD dwMinVerStarterFirmware:
    :var DWORD dwMaxVerStarterFirmware:
    :var BYTE[8] reserved_1:
    :var BYTE[64] reserved_2:
    """
    _fields_ = [("dwMinVerStarterFirmware", wt.DWORD),
                ("dwMaxVerStarterFirmware", wt.DWORD),
                ("reserved_1", wt.BYTE * 8),
                ("reserved_2", wt.BYTE * 64)]

#  use is_GetEthDeviceInfo() to obtain this data.
class UC480_ETH_DEVICE_INFO(ctypes.Structure):
    """
    :var UC480_ETH_DEVICE_INFO_HEARTBEAT infoDevHeartbeat:
    :var UC480_ETH_DEVICE_INFO_CONTROL infoDevControl:
    :var UC480_ETH_ADAPTER_INFO infoAdapter:
    :var UC480_ETH_DRIVER_INFO infoDriver:
    """
    _fields_ = [("infoDevHeartbeat", UC480_ETH_DEVICE_INFO_HEARTBEAT),
                ("infoDevControl", UC480_ETH_DEVICE_INFO_CONTROL),
                ("infoAdapter", UC480_ETH_ADAPTER_INFO),
                ("infoDriver", UC480_ETH_DRIVER_INFO)]

class UC480_COMPORT_CONFIGURATION(ctypes.Structure):
    """
    :var WORD wComportNumber:
    """
    _fields_ = [("wComportNumber", wt.WORD)]

class IS_DEVICE_INFO_HEARTBEAT(ctypes.Structure):
    """
    :var BYTE[24] reserved_1:
    :var DWORD dwRuntimeFirmwareVersion:
    :var BYTE[8] reserved_2:
    :var WORD wTemperature:
    :var WORD wLinkSpeed_Mb:
    :var BYTE[6] reserved_3:
    :var WORD wComportOffset:
    :var BYTE[200] reserved:
    """
    _fields_ = [("reserved_1", wt.BYTE * 24),
                ("dwRuntimeFirmwareVersion", wt.DWORD),
                ("reserved_2", wt.BYTE * 8),
                ("wTemperature", wt.WORD),
                ("wLinkSpeed_Mb", wt.WORD),
                ("reserved_3", wt.BYTE * 6),
                ("wComportOffset", wt.WORD),
                ("reserved", wt.BYTE * 200)]

class IS_DEVICE_INFO_CONTROL(ctypes.Structure):
    """
    :var DWORD dwDeviceId:
    :var BYTE[146] reserved:
    """
    _fields_ = [("dwDeviceId", wt.DWORD),
                ("reserved", wt.BYTE * 148)]

class IS_DEVICE_INFO(ctypes.Structure):
    """
    :var IS_DEVICE_INFO_HEARTBEAT infoDevHeartbeat:
    :var IS_DEVICE_INFO_CONTROL infoDevControl:
    :var BYTE[240] reserved:
    """
    _fields_ = [("infoDevHeartbeat", IS_DEVICE_INFO_HEARTBEAT),
                ("infoDevControl", IS_DEVICE_INFO_CONTROL),
                ("reserved", wt.BYTE * 240)]

IS_DEVICE_INFO_CMD_GET_DEVICE_INFO  = 0x02010001

class OPENGL_DISPLAY(ctypes.Structure):
    """
    :var ctypes.c_int nWindowID:
    :var ctypes.c_void_p pDisplay:
    """
    _fields_ = [("nWindowID", ctypes.c_int),
                ("pDisplay", ctypes.c_void_p)]

IMGFRMT_CMD_GET_NUM_ENTRIES              = 1  #  Get the number of supported image formats.
                                         #    pParam hast to be a Pointer to IS_U32. If  -1 is reported, the device
                                         #    supports continuous AOI settings (maybe with fixed increments)
IMGFRMT_CMD_GET_LIST                     = 2  #  Get a array of IMAGE_FORMAT_ELEMENTs.
IMGFRMT_CMD_SET_FORMAT                   = 3  #  Select a image format
IMGFRMT_CMD_GET_ARBITRARY_AOI_SUPPORTED  = 4  #  Does the device supports the setting of an arbitrary AOI.
IMGFRMT_CMD_GET_FORMAT_INFO              = 5  #  Get IMAGE_FORMAT_INFO for a given formatID

#  no trigger
CAPTMODE_FREERUN                    = 0x00000001
CAPTMODE_SINGLE                     = 0x00000002

#  software trigger modes
CAPTMODE_TRIGGER_SOFT_SINGLE        = 0x00000010
CAPTMODE_TRIGGER_SOFT_CONTINUOUS    = 0x00000020

#  hardware trigger modes
CAPTMODE_TRIGGER_HW_SINGLE          = 0x00000100
CAPTMODE_TRIGGER_HW_CONTINUOUS      = 0x00000200

class IMAGE_FORMAT_INFO(ctypes.Structure):
    """
    :var INT nFormatID:
    :var UINT nWidth:
    :var UINT nHeight:
    :var INT nX0:
    :var INT nY0:
    :var UINT nSupportedCaptureModes:
    :var UINT nBinningMode:
    :var UINT nSubsamplingMode:
    :var ctypes.c_char[64] strFormatName:
    :var ctypes.c_double dSensorScalerFactor:
    :var UINT[22] nReserved:
    """
    _fields_ = [("nFormatID", wt.INT),
                ("nWidth", wt.UINT),
                ("nHeight", wt.UINT),
                ("nX0", wt.INT),
                ("nY0", wt.INT),
                ("nSupportedCaptureModes", wt.UINT),
                ("nBinningMode", wt.UINT),
                ("nSubsamplingMode", wt.UINT),
                ("strFormatName", ctypes.c_char * 64),
                ("dSensorScalerFactor", ctypes.c_double),
                ("nReserved", wt.UINT * 22)]

# class IMAGE_FORMAT_LIST(ctypes.Structure):
    # _fields_ = [("nSizeOfListEntry", wt.UINT),
                # ("nNumListElements", wt.UINT),
                # ("nReserved", wt.UINT * 4),
                # ("FormatInfo", ctypes.POINTER(IMAGE_FORMAT_INFO))]
def create_image_format_list(nNumListElements):
    """Returns an instance of the IMAGE_FORMAT_LIST structure having the properly scaled *FormatInfo* array.

    :param ULONG nNumListElements: Number of format info structures requested.
    :returns: IMAGE_FORMAT_LIST

    :var UINT nSizeOfListEntry:
    :var UINT nNumListElements:
    :var UINT[4] nReserved:
    :var IMAGE_FORMAT_INFO[nNumListElements] FormatInfo:
    """
    class IMAGE_FORMAT_LIST(ctypes.Structure):
        _fields_ = [("nSizeOfListEntry", wt.UINT),
                    ("nNumListElements", wt.UINT),
                    ("nReserved", wt.UINT * 4),
                    ("FormatInfo", IMAGE_FORMAT_INFO * nNumListElements)]
    a_list = IMAGE_FORMAT_LIST()
    a_list.nNumListElements = nNumListElements
    return a_list

FDT_CAP_INVALID             = 0
FDT_CAP_SUPPORTED           = 0x00000001 #  Face detection supported.
FDT_CAP_SEARCH_ANGLE        = 0x00000002 #  Search angle.
FDT_CAP_SEARCH_AOI          = 0x00000004 #  Search AOI.
FDT_CAP_INFO_POSX           = 0x00000010 #  Query horizontal position (center) of detected face.
FDT_CAP_INFO_POSY           = 0x00000020 #  Query vertical position(center) of detected face.
FDT_CAP_INFO_WIDTH          = 0x00000040 #  Query width of detected face.
FDT_CAP_INFO_HEIGHT         = 0x00000080 #  Query height of detected face.
FDT_CAP_INFO_ANGLE          = 0x00000100 #  Query angle of detected face.
FDT_CAP_INFO_POSTURE        = 0x00000200 #  Query posture of detected face.
FDT_CAP_INFO_FACENUMBER     = 0x00000400 #  Query number of detected faces.
FDT_CAP_INFO_OVL            = 0x00000800 #  Overlay: Mark the detected face in the image.
FDT_CAP_INFO_NUM_OVL        = 0x00001000 #  Overlay: Limit the maximum number of overlays in one image.
FDT_CAP_INFO_OVL_LINEWIDTH  = 0x00002000 #  Overlay line width.

class FDT_INFO_EL(ctypes.Structure):
    """
    :var INT nFacePosX:
    :var INT nFacePosY:
    :var INT nFaceWidth:
    :var INT nFaceHeight:
    :var INT nAngle:
    :var UINT nPosture:
    :var UC480TIME TimestampSystem:
    :var ctypes.c_ulonglong nReserved:
    :var UINT[4] nReserved2:
    """
    _fields_ = [("nFacePosX", wt.INT),
                ("nFacePosY", wt.INT),
                ("nFaceWidth", wt.INT),
                ("nFaceHeight", wt.INT),
                ("nAngle", wt.INT),
                ("nPosture", wt.UINT),
                ("TimestampSystem", UC480TIME),
                ("nReserved", ctypes.c_ulonglong),
                ("nReserved2", wt.UINT * 4)]

# class FDT_INFO_LIST(ctypes.Structure):
    # _fields_ = [("nSizeOfListEntry", wt.UINT),
                # ("nNumDetectedFaces", wt.UINT),
                # ("nNumListElements", wt.UINT),
                # ("nReserved", wt.UINT * 4),
                # ("FaceEntry", ctypes.POINTER(FDT_INFO_EL))]
def create_fdt_info_list(nNumListElements):
    """Returns an instance of the FDT_INFO_LIST structure having the properly scaled *FaceEntry* array.

    :param ULONG nNumListElements: Number of face entry structures requested.
    :returns: FDT_INFO_LIST

    :var UINT nSizeOfListEntry:
    :var UINT nNumDetectedFaces:
    :var UINT nNumListElements:
    :var UINT[4] nReserved:
    :var FDT_INFO_EL[nNumListElements] FaceEntry:
    """
    class FDT_INFO_LIST(ctypes.Structure):
        _fields_ = [("nSizeOfListEntry", wt.UINT),
                    ("nNumDetectedFaces", wt.UINT),
                    ("nNumListElements", wt.UINT),
                    ("nReserved", wt.UINT * 4),
                    ("FaceEntry", FDT_INFO_EL * nNumListElements)]
    a_list = FDT_INFO_LIST()
    a_list.nNumListElements = nNumListElements
    return a_list

FDT_CMD_GET_CAPABILITIES        = 0    #  Get the capabilities for face detection.
FDT_CMD_SET_DISABLE             = 1    #  Disable face detection.
FDT_CMD_SET_ENABLE              = 2    #  Enable face detection.
FDT_CMD_SET_SEARCH_ANGLE        = 3    #  Set the search angle.
FDT_CMD_GET_SEARCH_ANGLE        = 4    #  Get the search angle parameter.
FDT_CMD_SET_SEARCH_ANGLE_ENABLE = 5    #  Enable search angle.
FDT_CMD_SET_SEARCH_ANGLE_DISABLE= 6    #  Enable search angle.
FDT_CMD_GET_SEARCH_ANGLE_ENABLE = 7    #  Get the current setting of search angle enable.
FDT_CMD_SET_SEARCH_AOI          = 8    #  Set the search AOI.
FDT_CMD_GET_SEARCH_AOI          = 9    #  Get the search AOI.
FDT_CMD_GET_FACE_LIST           = 10   #  Get a list with detected faces.
FDT_CMD_GET_NUMBER_FACES        = 11   #  Get the number of detected faces.
FDT_CMD_SET_SUSPEND             = 12   #  Keep the face detection result of that moment.
FDT_CMD_SET_RESUME              = 13   #  Continue with the face detection.
FDT_CMD_GET_MAX_NUM_FACES       = 14   #  Get the maximum number of faces that can be detected once.
FDT_CMD_SET_INFO_MAX_NUM_OVL    = 15   #  Set the maximum number of overlays displayed.
FDT_CMD_GET_INFO_MAX_NUM_OVL    = 16   #  Get the setting 'maximum number of overlays displayed'.
FDT_CMD_SET_INFO_OVL_LINE_WIDTH = 17   #  Set the overlay line width.
FDT_CMD_GET_INFO_OVL_LINE_WIDTH = 18   #  Get the overlay line width.
FDT_CMD_GET_ENABLE              = 19   #  Face detection enabled?.
FDT_CMD_GET_SUSPEND             = 20    #  Face detection suspended?.

FOC_CAP_INVALID             = 0
FOC_CAP_AUTOFOCUS_SUPPORTED = 0x00000001   #  Auto focus supported.
FOC_CAP_MANUAL_SUPPORTED    = 0x00000002   #  Manual focus supported.
FOC_CAP_GET_DISTANCE        = 0x00000004   #  Support for query the distance of the focused object.
FOC_CAP_SET_AUTOFOCUS_RANGE = 0x00000008    #  Support for setting focus ranges.

FOC_RANGE_NORMAL            = 0x00000001   #  Normal focus range(without Macro).
FOC_RANGE_ALLRANGE          = 0x00000002   #  Allrange (macro to Infinity).
FOC_RANGE_MACRO             = 0x00000004    #  Macro (only macro).

FOC_CMD_GET_CAPABILITIES        = 0   #  Get focus capabilities.
FOC_CMD_SET_DISABLE_AUTOFOCUS   = 1    #  Disable autofocus.
FOC_CMD_SET_ENABLE_AUTOFOCUS    = 2    #  Enable autofocus.
FOC_CMD_GET_AUTOFOCUS_ENABLE    = 3    #  Autofocus enabled?.
FOC_CMD_SET_AUTOFOCUS_RANGE     = 4    #  Preset autofocus range.
FOC_CMD_GET_AUTOFOCUS_RANGE     = 5    #  Get preset of autofocus range.
FOC_CMD_GET_DISTANCE            = 6    #  Get distance to focused object.
FOC_CMD_SET_MANUAL_FOCUS        = 7    #  Set manual focus.
FOC_CMD_GET_MANUAL_FOCUS        = 8    #  Get the value for manual focus.
FOC_CMD_GET_MANUAL_FOCUS_MIN    = 9    #  Get the minimum manual focus value.
FOC_CMD_GET_MANUAL_FOCUS_MAX    = 10   #  Get the maximum manual focus value.
FOC_CMD_GET_MANUAL_FOCUS_INC    = 11    #  Get the increment of the manual focus value.

IMGSTAB_CAP_INVALID                         = 0
IMGSTAB_CAP_IMAGE_STABILIZATION_SUPPORTED   = 0x00000001    #  Image stabilization supported.

IMGSTAB_CMD_GET_CAPABILITIES        = 0    #  Get the capabilities for image stabilization.
IMGSTAB_CMD_SET_DISABLE                 = 1    #  Disable image stabilization.
IMGSTAB_CMD_SET_ENABLE                  = 2    #  Enable image stabilization.
IMGSTAB_CMD_GET_ENABLE              = 3     #  Image stabilization enabled?

SCENE_CMD_GET_SUPPORTED_PRESETS = 1#  Get the supported scene presets
SCENE_CMD_SET_PRESET            = 2#  Set the scene preset
SCENE_CMD_GET_PRESET            = 3#  Get the current sensor scene preset
SCENE_CMD_GET_DEFAULT_PRESET    = 4 #  Get the default sensor scene preset

SCENE_INVALID             = 0
SCENE_SENSOR_AUTOMATIC    = 0x00000001
SCENE_SENSOR_PORTRAIT     = 0x00000002
SCENE_SENSOR_SUNNY        = 0x00000004
SCENE_SENSOR_ENTERTAINMENT        = 0x00000008
SCENE_SENSOR_NIGHT        = 0x00000010
SCENE_SENSOR_SPORTS       = 0x00000040
SCENE_SENSOR_LANDSCAPE    = 0x00000080

ZOOM_CMD_GET_CAPABILITIES               = 0#  Get the zoom capabilities.
ZOOM_CMD_DIGITAL_GET_NUM_LIST_ENTRIES   = 1#  Get the number of list entries.
ZOOM_CMD_DIGITAL_GET_LIST               = 2#  Get a list of supported zoom factors.
ZOOM_CMD_DIGITAL_SET_VALUE              = 3#  Set the digital zoom factor zoom factors.
ZOOM_CMD_DIGITAL_GET_VALUE              = 4 #  Get a current digital zoom factor.

ZOOM_CAP_INVALID        = 0
ZOOM_CAP_DIGITAL_ZOOM   = 0x00001

SHARPNESS_CMD_GET_CAPABILITIES          = 0 #  Get the sharpness capabilities
SHARPNESS_CMD_GET_VALUE                 = 1 #  Get the current sharpness value
SHARPNESS_CMD_GET_MIN_VALUE             = 2 #  Get the minimum sharpness value
SHARPNESS_CMD_GET_MAX_VALUE             = 3 #  Get the maximum sharpness value
SHARPNESS_CMD_GET_INCREMENT             = 4 #  Get the sharpness increment
SHARPNESS_CMD_GET_DEFAULT_VALUE         = 5 #  Get the default sharpness value
SHARPNESS_CMD_SET_VALUE                 = 6  #  Set the sharpness value

SHARPNESS_CAP_INVALID                   = 0x0000
SHARPNESS_CAP_SHARPNESS_SUPPORTED       = 0x0001

SATURATION_CMD_GET_CAPABILITIES         = 0 #  Get the saturation capabilities
SATURATION_CMD_GET_VALUE                = 1 #  Get the current saturation value
SATURATION_CMD_GET_MIN_VALUE            = 2 #  Get the minimum saturation value
SATURATION_CMD_GET_MAX_VALUE            = 3 #  Get the maximum saturation value
SATURATION_CMD_GET_INCREMENT            = 4 #  Get the saturation increment
SATURATION_CMD_GET_DEFAULT              = 5 #  Get the default saturation value
SATURATION_CMD_SET_VALUE                = 6  #  Set the saturation value


SATURATION_CAP_INVALID                  = 0x0000
SATURATION_CAP_SATURATION_SUPPORTED     = 0x0001

TRIGGER_DEBOUNCE_MODE_NONE              = 0x0000
TRIGGER_DEBOUNCE_MODE_FALLING_EDGE      = 0x0001
TRIGGER_DEBOUNCE_MODE_RISING_EDGE       = 0x0002
TRIGGER_DEBOUNCE_MODE_BOTH_EDGES        = 0x0004
TRIGGER_DEBOUNCE_MODE_AUTOMATIC         = 0x0008

TRIGGER_DEBOUNCE_CMD_SET_MODE                   = 0 #  Set a new trigger debounce mode
TRIGGER_DEBOUNCE_CMD_SET_DELAY_TIME             = 1 #  Set a new trigger debounce delay time
TRIGGER_DEBOUNCE_CMD_GET_SUPPORTED_MODES        = 2 #  Get the supported modes
TRIGGER_DEBOUNCE_CMD_GET_MODE                   = 3 #  Get the current trigger debounce mode
TRIGGER_DEBOUNCE_CMD_GET_DELAY_TIME             = 4 #  Get the current trigger debounce delay time
TRIGGER_DEBOUNCE_CMD_GET_DELAY_TIME_MIN         = 5 #  Get the minimum value for the trigger debounce delay time
TRIGGER_DEBOUNCE_CMD_GET_DELAY_TIME_MAX         = 6 #  Get the maximum value for the trigger debounce delay time
TRIGGER_DEBOUNCE_CMD_GET_DELAY_TIME_INC         = 7 #  Get the increment of the trigger debounce delay time
TRIGGER_DEBOUNCE_CMD_GET_MODE_DEFAULT           = 8 #  Get the default trigger debounce mode
TRIGGER_DEBOUNCE_CMD_GET_DELAY_TIME_DEFAULT     = 9 #  Get the default trigger debounce delay time

RGB_COLOR_MODEL_SRGB_D50        = 0x0001
RGB_COLOR_MODEL_SRGB_D65        = 0x0002
RGB_COLOR_MODEL_CIE_RGB_E       = 0x0004
RGB_COLOR_MODEL_ECI_RGB_D50     = 0x0008
RGB_COLOR_MODEL_ADOBE_RGB_D65   = 0x0010

COLOR_TEMPERATURE_CMD_SET_TEMPERATURE                   = 0 #  Set a new color temperature
COLOR_TEMPERATURE_CMD_SET_RGB_COLOR_MODEL               = 1 #  Set a new RGB color model
COLOR_TEMPERATURE_CMD_GET_SUPPORTED_RGB_COLOR_MODELS    = 2 #  Get the supported RGB color models
COLOR_TEMPERATURE_CMD_GET_TEMPERATURE                   = 3 #  Get the current color temperature
COLOR_TEMPERATURE_CMD_GET_RGB_COLOR_MODEL               = 4 #  Get the current RGB color model
COLOR_TEMPERATURE_CMD_GET_TEMPERATURE_MIN               = 5 #  Get the minimum value for the color temperature
COLOR_TEMPERATURE_CMD_GET_TEMPERATURE_MAX               = 6 #  Get the maximum value for the color temperature
COLOR_TEMPERATURE_CMD_GET_TEMPERATURE_INC               = 7 #  Get the increment of the color temperature
COLOR_TEMPERATURE_CMD_GET_TEMPERATURE_DEFAULT           = 8 #  Get the default color temperature
COLOR_TEMPERATURE_CMD_GET_RGB_COLOR_MODEL_DEFAULT       = 9  #  Get the default RGB color model

class IS_POINT_2D(ctypes.Structure):
    """
    :var INT s32X:
    :var INT s32Y:
    """
    _fields_ = [("s32X", wt.INT),
                ("s32Y", wt.INT)]

class IS_SIZE_2D(ctypes.Structure):
    """
    :var INT s32Width:
    :var INT s23Height:
    """
    _fields_ = [("s32Width", wt.INT),
                ("s32Height", wt.INT)]

class IS_RECT(ctypes.Structure):
    """
    :var INT s32X:
    :var INT s32Y:
    :var INT s32Width:
    :var INT s23Height:
    """
    _fields_ = [("s32X", wt.INT),
                ("s32Y", wt.INT),
                ("s32Width", wt.INT),
                ("s32Height", wt.INT)]

class AOI_SEQUENCE_PARAMS(ctypes.Structure):
    """
    :var INT s32AOIIndex:
    :var INT s32NumberOfCycleRepetitions:
    :var INT s32X:
    :var INT s32Y:
    :var ctypes.c_double dblExposure:
    :var INT s32Gain:
    :var INT s32BinningMode:
    :var INT s32SubsamplingMode:
    :var INT s32DetachImageParameters:
    :var ctypes.c_double dblScalerFactor:
    :var BYTE[64] byReserved:
    """
    _fields_ = [("s32AOIIndex", wt.INT),
                ("s32NumberOfCycleRepetitions", wt.INT),
                ("s32X", wt.INT),
                ("s32Y", wt.INT),
                ("dblExposure", ctypes.c_double),
                ("s32Gain", wt.INT),
                ("s32BinningMode", wt.INT),
                ("s32SubsamplingMode", wt.INT),
                ("s32DetachImageParameters", wt.INT),
                ("dblScalerFactor", ctypes.c_double),
                ("byReserved", wt.BYTE * 64)]

IS_DEVICE_FEATURE_CMD_GET_SUPPORTED_FEATURES               = 1
IS_DEVICE_FEATURE_CMD_SET_LINESCAN_MODE                    = 2
IS_DEVICE_FEATURE_CMD_GET_LINESCAN_MODE                    = 3
IS_DEVICE_FEATURE_CMD_SET_LINESCAN_NUMBER                  = 4
IS_DEVICE_FEATURE_CMD_GET_LINESCAN_NUMBER                  = 5
IS_DEVICE_FEATURE_CMD_SET_SHUTTER_MODE                     = 6
IS_DEVICE_FEATURE_CMD_GET_SHUTTER_MODE                     = 7
IS_DEVICE_FEATURE_CMD_SET_PREFER_XS_HS_MODE                = 8
IS_DEVICE_FEATURE_CMD_GET_PREFER_XS_HS_MODE                = 9
IS_DEVICE_FEATURE_CMD_GET_DEFAULT_PREFER_XS_HS_MODE        = 10
IS_DEVICE_FEATURE_CMD_GET_LOG_MODE_DEFAULT                 = 11
IS_DEVICE_FEATURE_CMD_GET_LOG_MODE                         = 12
IS_DEVICE_FEATURE_CMD_SET_LOG_MODE                         = 13
IS_DEVICE_FEATURE_CMD_GET_LOG_MODE_MANUAL_VALUE_DEFAULT    = 14
IS_DEVICE_FEATURE_CMD_GET_LOG_MODE_MANUAL_VALUE_RANGE      = 15
IS_DEVICE_FEATURE_CMD_GET_LOG_MODE_MANUAL_VALUE            = 16
IS_DEVICE_FEATURE_CMD_SET_LOG_MODE_MANUAL_VALUE            = 17
IS_DEVICE_FEATURE_CMD_GET_LOG_MODE_MANUAL_GAIN_DEFAULT     = 18
IS_DEVICE_FEATURE_CMD_GET_LOG_MODE_MANUAL_GAIN_RANGE       = 19
IS_DEVICE_FEATURE_CMD_GET_LOG_MODE_MANUAL_GAIN             = 20
IS_DEVICE_FEATURE_CMD_SET_LOG_MODE_MANUAL_GAIN             = 21

IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING                      = 0x00000001
IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_GLOBAL                       = 0x00000002
IS_DEVICE_FEATURE_CAP_LINESCAN_MODE_FAST                        = 0x00000004
IS_DEVICE_FEATURE_CAP_LINESCAN_NUMBER                           = 0x00000008
IS_DEVICE_FEATURE_CAP_PREFER_XS_HS_MODE                         = 0x00000010
IS_DEVICE_FEATURE_CAP_LOG_MODE                                  = 0x00000020
IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_ROLLING_GLOBAL_START         = 0x00000040
IS_DEVICE_FEATURE_CAP_SHUTTER_MODE_GLOBAL_ALTERNATIVE_TIMING    = 0x00000080

IS_LOG_MODE_FACTORY_DEFAULT    = 0
IS_LOG_MODE_OFF                = 1
IS_LOG_MODE_MANUAL             = 2

class RANGE_OF_VALUES_U32(ctypes.Structure):
    """
    :var UINT u32Minimum:
    :var UINT u32Maximum:
    :var UINT u32Increment:
    :var UINT u32Default:
    :var UINT u32Infinite:
    """
    _fields_ = [("u32Minimum", wt.UINT),
                ("u32Maximum", wt.UINT),
                ("u32Increment", wt.UINT),
                ("u32Default", wt.UINT),
                ("u32Infinite", wt.UINT)]

TRANSFER_CAP_IMAGEDELAY                     = 0x01
TRANSFER_CAP_PACKETINTERVAL                 = 0x20

TRANSFER_CMD_QUERY_CAPABILITIES                 = 0
TRANSFER_CMD_SET_IMAGEDELAY_US                  = 1000
TRANSFER_CMD_SET_PACKETINTERVAL_US              = 1005
TRANSFER_CMD_GET_IMAGEDELAY_US                  = 2000
TRANSFER_CMD_GET_PACKETINTERVAL_US              = 2005
TRANSFER_CMD_GETRANGE_IMAGEDELAY_US             = 3000
TRANSFER_CMD_GETRANGE_PACKETINTERVAL_US         = 3005
TRANSFER_CMD_SET_IMAGE_DESTINATION              = 5000
TRANSFER_CMD_GET_IMAGE_DESTINATION              = 5001
TRANSFER_CMD_GET_IMAGE_DESTINATION_CAPABILITIES = 5002

IS_TRANSFER_DESTINATION_DEVICE_MEMORY   = 1
IS_TRANSFER_DESTINATION_USER_MEMORY     = 2

IS_BOOTBOOST_ID = wt.BYTE

IS_BOOTBOOST_ID_MIN   =  1
IS_BOOTBOOST_ID_MAX   =  254
IS_BOOTBOOST_ID_NONE  =  0
IS_BOOTBOOST_ID_ALL   =  255

# class IS_BOOTBOOST_IDLIST(ctypes.Structure):
    # _fields_ = [("u32NumberOfEntries", wt.DWORD),
                # ("aList", ctypes.POINTER(IS_BOOTBOOST_ID))]
def create_bootboost_idlist(numberOfEntries):
    """Returns an instance of the IS_BOOTBOOST_IDLIST structure having the properly scaled *aList* array.

    :param ULONG numberOfEntries: Number of aList structures requested.
    :returns: IS_BOOTBOOST_IDLIST

    :var DWORD u32NumberOfEntries:
    :var IS_BOOTBOOST_ID[numberOfEntries] aList:
    """
    class IS_BOOTBOOST_IDLIST(ctypes.Structure):
        _fields_ = [("u32NumberOfEntries", wt.DWORD),
                    ("aList", IS_BOOTBOOST_ID * numberOfEntries)]
    a_list = IS_BOOTBOOST_IDLIST()
    a_list.u32NumberOfEntries = numberOfEntries
    return a_list

IS_BOOTBOOST_IDLIST_HEADERSIZE  = (ctypes.sizeof(wt.DWORD))
IS_BOOTBOOST_IDLIST_ELEMENTSIZE = (ctypes.sizeof(IS_BOOTBOOST_ID))

IS_BOOTBOOST_CMD_ENABLE             = 0x00010001
IS_BOOTBOOST_CMD_DISABLE            = 0x00010011
IS_BOOTBOOST_CMD_GET_ENABLED        = 0x20010021
IS_BOOTBOOST_CMD_ADD_ID             = 0x10100001
IS_BOOTBOOST_CMD_SET_IDLIST         = 0x10100005
IS_BOOTBOOST_CMD_REMOVE_ID         = 0x10100011
IS_BOOTBOOST_CMD_CLEAR_IDLIST       = 0x00100015
IS_BOOTBOOST_CMD_GET_IDLIST        = 0x30100021
IS_BOOTBOOST_CMD_GET_IDLIST_SIZE    = 0x20100022

IPCONFIG_CAP_PERSISTENT_IP_SUPPORTED    = 0x01
IPCONFIG_CAP_AUTOCONFIG_IP_SUPPORTED    = 0x04

IPCONFIG_CMD_QUERY_CAPABILITIES         = 0
IPCONFIG_CMD_SET_PERSISTENT_IP          = 0x01010000
IPCONFIG_CMD_SET_AUTOCONFIG_IP          = 0x01040000
IPCONFIG_CMD_SET_AUTOCONFIG_IP_BYDEVICE = 0x01040100
IPCONFIG_CMD_GET_PERSISTENT_IP          = 0x02010000
IPCONFIG_CMD_GET_AUTOCONFIG_IP          = 0x02040000
IPCONFIG_CMD_GET_AUTOCONFIG_IP_BYDEVICE = 0x02040100

IS_CONFIG_CPU_IDLE_STATES_BIT_AC_VALUE         = 0x01 # !< Mains power
IS_CONFIG_CPU_IDLE_STATES_BIT_DC_VALUE         = 0x02 # !< Battery power

IS_CONFIG_OPEN_MP_DISABLE                      = 0
IS_CONFIG_OPEN_MP_ENABLE                       = 1

IS_CONFIG_INITIAL_PARAMETERSET_NONE            = 0
IS_CONFIG_INITIAL_PARAMETERSET_1               = 1
IS_CONFIG_INITIAL_PARAMETERSET_2               = 2

IS_CONFIG_CMD_GET_CAPABILITIES                         = 1 # !< Get supported configuration capabilities (bitmask of CONFIGURATION_CAPS)

IS_CONFIG_CPU_IDLE_STATES_CMD_GET_ENABLE               = 2 # !< Get the current CPU idle states enable state (bitmask of CONFIGURATION_SEL)
IS_CONFIG_CPU_IDLE_STATES_CMD_SET_DISABLE_ON_OPEN      = 4 # !< Disable migration to other CPU idle states (other than C0) if the first USB camera is being opened
IS_CONFIG_CPU_IDLE_STATES_CMD_GET_DISABLE_ON_OPEN      = 5 # !< Get the current setting of the command IS_CPU_IDLE_STATES_CMD_SET_DISABLE_ON_OPEN

IS_CONFIG_OPEN_MP_CMD_GET_ENABLE                       = 6
IS_CONFIG_OPEN_MP_CMD_SET_ENABLE                       = 7
IS_CONFIG_OPEN_MP_CMD_GET_ENABLE_DEFAULT               = 8

IS_CONFIG_INITIAL_PARAMETERSET_CMD_SET                 = 9
IS_CONFIG_INITIAL_PARAMETERSET_CMD_GET                 = 10

IS_CONFIG_CPU_IDLE_STATES_CAP_SUPPORTED                = 0x00000001 # !< CPU idle state commands are supported by the SDK
IS_CONFIG_OPEN_MP_CAP_SUPPORTED                        = 0x00000002 # !< Open MP commands are supported by the SDK
IS_CONFIG_INITIAL_PARAMETERSET_CAP_SUPPORTED           = 0x00000004  # !< Initial parameter set commands are supported by the SDK

IS_EXPOSURE_CMD_GET_CAPS                        = 1
IS_EXPOSURE_CMD_GET_EXPOSURE_DEFAULT            = 2
IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MIN          = 3
IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_MAX          = 4
IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE_INC          = 5
IS_EXPOSURE_CMD_GET_EXPOSURE_RANGE              = 6
IS_EXPOSURE_CMD_GET_EXPOSURE                    = 7
IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE_MIN    = 8
IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE_MAX    = 9
IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE_INC    = 10
IS_EXPOSURE_CMD_GET_FINE_INCREMENT_RANGE        = 11
IS_EXPOSURE_CMD_SET_EXPOSURE                    = 12
IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE_MIN     = 13
IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE_MAX     = 14
IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE_INC     = 15
IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_RANGE         = 16
IS_EXPOSURE_CMD_GET_LONG_EXPOSURE_ENABLE        = 17
IS_EXPOSURE_CMD_SET_LONG_EXPOSURE_ENABLE        = 18
IS_EXPOSURE_CMD_GET_DUAL_EXPOSURE_RATIO         = 19
IS_EXPOSURE_CMD_SET_DUAL_EXPOSURE_RATIO         = 20

IS_EXPOSURE_CAP_EXPOSURE                        = 0x00000001
IS_EXPOSURE_CAP_FINE_INCREMENT                  = 0x00000002
IS_EXPOSURE_CAP_LONG_EXPOSURE                   = 0x00000004
IS_EXPOSURE_CAP_DUAL_EXPOSURE                   = 0x00000008

IS_TRIGGER_CMD_GET_BURST_SIZE_SUPPORTED     = 1
IS_TRIGGER_CMD_GET_BURST_SIZE_RANGE         = 2
IS_TRIGGER_CMD_GET_BURST_SIZE               = 3
IS_TRIGGER_CMD_SET_BURST_SIZE               = 4

class IO_FLASH_PARAMS(ctypes.Structure):
    """
    :var INT s32Delay:
    :var UINT u32Duration:
    """
    _fields_ = [("s32Delay", wt.INT),
                ("u32Duration", wt.UINT)]

class IO_PWM_PARAMS(ctypes.Structure):
    """
    :var ctypes.c_double dblFrequency_Hz:
    :var ctypes.c_double dblDutyCycle:
    """
    _fields_ = [("dblFrequency_Hz", ctypes.c_double),
                ("dblDutyCycle", ctypes.c_double)]

class IO_GPIO_CONFIGURATION(ctypes.Structure):
    """
    :var UINT u32Gpio:
    :var UINT u32Caps:
    :var UINT u32Configuration:
    :var UINT u32State:
    :var UINT[12] u32Reserved:
    """
    _fields_ = [("u32Gpio", wt.UINT),
                ("u32Caps", wt.UINT),
                ("u32Configuration", wt.UINT),
                ("u32State", wt.UINT),
                ("u32Reserved", wt.UINT * 12)]

IO_LED_STATE_1                    =  0
IO_LED_STATE_2                    =  1

IO_FLASH_MODE_OFF                 =  0
IO_FLASH_MODE_TRIGGER_LO_ACTIVE   =  1
IO_FLASH_MODE_TRIGGER_HI_ACTIVE   =  2
IO_FLASH_MODE_CONSTANT_HIGH       =  3
IO_FLASH_MODE_CONSTANT_LOW        =  4
IO_FLASH_MODE_FREERUN_LO_ACTIVE   =  5
IO_FLASH_MODE_FREERUN_HI_ACTIVE   =  6

IS_FLASH_MODE_PWM                 =  0x8000
IO_FLASH_MODE_GPIO_1              =  0x0010
IO_FLASH_MODE_GPIO_2              =  0x0020
IO_FLASH_MODE_GPIO_3              =  0x0040
IO_FLASH_MODE_GPIO_4              =  0x0080
IO_FLASH_GPIO_PORT_MASK           =  (IO_FLASH_MODE_GPIO_1 | IO_FLASH_MODE_GPIO_2 | IO_FLASH_MODE_GPIO_3 | IO_FLASH_MODE_GPIO_4)

IO_GPIO_1                         =  0x0001
IO_GPIO_2                         =  0x0002
IO_GPIO_3                         =  0x0004
IO_GPIO_4                         =  0x0008

IS_GPIO_INPUT                     =  0x0001
IS_GPIO_OUTPUT                    =  0x0002
IS_GPIO_FLASH                     =  0x0004
IS_GPIO_PWM                       =  0x0008
IS_GPIO_COMPORT_RX                =  0x0010
IS_GPIO_COMPORT_TX                =  0x0020


IS_IO_CMD_GPIOS_GET_SUPPORTED               = 1
IS_IO_CMD_GPIOS_GET_SUPPORTED_INPUTS        = 2
IS_IO_CMD_GPIOS_GET_SUPPORTED_OUTPUTS       = 3
IS_IO_CMD_GPIOS_GET_DIRECTION               = 4
IS_IO_CMD_GPIOS_SET_DIRECTION               = 5
IS_IO_CMD_GPIOS_GET_STATE                   = 6
IS_IO_CMD_GPIOS_SET_STATE                   = 7
IS_IO_CMD_LED_GET_STATE                     = 8
IS_IO_CMD_LED_SET_STATE                     = 9
IS_IO_CMD_LED_TOGGLE_STATE                  = 10
IS_IO_CMD_FLASH_GET_GLOBAL_PARAMS           = 11
IS_IO_CMD_FLASH_APPLY_GLOBAL_PARAMS         = 12
IS_IO_CMD_FLASH_GET_SUPPORTED_GPIOS         = 13
IS_IO_CMD_FLASH_GET_PARAMS_MIN              = 14
IS_IO_CMD_FLASH_GET_PARAMS_MAX              = 15
IS_IO_CMD_FLASH_GET_PARAMS_INC              = 16
IS_IO_CMD_FLASH_GET_PARAMS                  = 17
IS_IO_CMD_FLASH_SET_PARAMS                  = 18
IS_IO_CMD_FLASH_GET_MODE                    = 19
IS_IO_CMD_FLASH_SET_MODE                    = 20
IS_IO_CMD_PWM_GET_SUPPORTED_GPIOS           = 21
IS_IO_CMD_PWM_GET_PARAMS_MIN                = 22
IS_IO_CMD_PWM_GET_PARAMS_MAX                = 23
IS_IO_CMD_PWM_GET_PARAMS_INC                = 24
IS_IO_CMD_PWM_GET_PARAMS                    = 25
IS_IO_CMD_PWM_SET_PARAMS                    = 26
IS_IO_CMD_PWM_GET_MODE                      = 27
IS_IO_CMD_PWM_SET_MODE                      = 28
IS_IO_CMD_GPIOS_GET_CONFIGURATION           = 29
IS_IO_CMD_GPIOS_SET_CONFIGURATION           = 30
IS_IO_CMD_FLASH_GET_GPIO_PARAMS_MIN         = 31
IS_IO_CMD_FLASH_SET_GPIO_PARAMS             = 32

IS_AWB_CMD_GET_SUPPORTED_TYPES              = 1
IS_AWB_CMD_GET_TYPE                         = 2
IS_AWB_CMD_SET_TYPE                         = 3
IS_AWB_CMD_GET_ENABLE                       = 4
IS_AWB_CMD_SET_ENABLE                       = 5
IS_AWB_CMD_GET_SUPPORTED_RGB_COLOR_MODELS   = 6
IS_AWB_CMD_GET_RGB_COLOR_MODEL              = 7
IS_AWB_CMD_SET_RGB_COLOR_MODEL              = 8

IS_AWB_GREYWORLD           =     0x0001
IS_AWB_COLOR_TEMPERATURE   =     0x0002

IS_AUTOPARAMETER_DISABLE    =         0
IS_AUTOPARAMETER_ENABLE      =        1
IS_AUTOPARAMETER_ENABLE_RUNONCE =     2

class BUFFER_CONVERSION_PARAMS(ctypes.Structure):
    """
    :var ctypes.c_char_p pSourceBuffer:
    :var ctypes.c_char_p pDestBuffer:
    :var INT nDestPixelFormat:
    :var INT nDestPixelConverter:
    :var INT nDestGamma:
    :var INT nDestEdgeEnhancement:
    :var INT nDestColorCorrectionMode:
    :var INT nDestSaturationU:
    :var INT nDestSaturationV:
    :var BYTE[32] reserved:
    """
    _fields_ = [("pSourceBuffer", ctypes.c_char_p),
                ("pDestBuffer", ctypes.c_char_p),
                ("nDestPixelFormat", wt.INT),
                ("nDestPixelConverter", wt.INT),
                ("nDestGamma", wt.INT),
                ("nDestEdgeEnhancement", wt.INT),
                ("nDestColorCorrectionMode", wt.INT),
                ("nDestSaturationU", wt.INT),
                ("nDestSaturationV", wt.INT),
                ("reserved", wt.BYTE * 32)]


IS_CONVERT_CMD_APPLY_PARAMS_AND_CONVERT_BUFFER = 1

IS_PARAMETERSET_CMD_LOAD_EEPROM               = 1
IS_PARAMETERSET_CMD_LOAD_FILE                 = 2
IS_PARAMETERSET_CMD_SAVE_EEPROM               = 3
IS_PARAMETERSET_CMD_SAVE_FILE                 = 4
IS_PARAMETERSET_CMD_GET_NUMBER_SUPPORTED      = 5

IS_EDGE_ENHANCEMENT_CMD_GET_RANGE   = 1
IS_EDGE_ENHANCEMENT_CMD_GET_DEFAULT = 2
IS_EDGE_ENHANCEMENT_CMD_GET         = 3
IS_EDGE_ENHANCEMENT_CMD_SET         = 4

IS_PIXELCLOCK_CMD_GET_NUMBER    = 1
IS_PIXELCLOCK_CMD_GET_LIST      = 2
IS_PIXELCLOCK_CMD_GET_RANGE     = 3
IS_PIXELCLOCK_CMD_GET_DEFAULT   = 4
IS_PIXELCLOCK_CMD_GET           = 5
IS_PIXELCLOCK_CMD_SET           = 6

class IMAGE_FILE_PARAMS(ctypes.Structure):
    """
    :var ctypes.c_wchar_p pwchFileName:
    :var UINT nFileType:
    :var UINT nQuality:
    :var ctypes.POINTER(ctypes.c_char_p) ppcImageMem:
    :var ctypes.POINTER(wt.UINT) pnImageID:
    :var BYTE[32] reserved:
    """
    _fields_ = [("pwchFileName", ctypes.c_wchar_p),
                ("nFileType", wt.UINT),
                ("nQuality", wt.UINT),
                ("ppcImageMem", ctypes.POINTER(ctypes.c_char_p)),
                ("pnImageID", ctypes.POINTER(wt.UINT)),
                ("reserved", wt.BYTE * 32)]

IS_IMAGE_FILE_CMD_LOAD    = 1
IS_IMAGE_FILE_CMD_SAVE    = 2

class IS_RANGE_S32(ctypes.Structure):
    """
    :var INT s32Min:
    :var INT s32Max:
    :var INT s32Inc:
    """
    _fields_ = [("s32Min", wt.INT),
                ("s32Max", wt.INT),
                ("s32Inc", wt.INT)]

IS_AUTO_BLACKLEVEL_OFF = 0
IS_AUTO_BLACKLEVEL_ON  = 1

IS_BLACKLEVEL_CAP_SET_AUTO_BLACKLEVEL   = 1
IS_BLACKLEVEL_CAP_SET_OFFSET            = 2

IS_BLACKLEVEL_CMD_GET_CAPS           = 1
IS_BLACKLEVEL_CMD_GET_MODE_DEFAULT   = 2
IS_BLACKLEVEL_CMD_GET_MODE           = 3
IS_BLACKLEVEL_CMD_SET_MODE           = 4
IS_BLACKLEVEL_CMD_GET_OFFSET_DEFAULT = 5
IS_BLACKLEVEL_CMD_GET_OFFSET_RANGE   = 6
IS_BLACKLEVEL_CMD_GET_OFFSET         = 7
IS_BLACKLEVEL_CMD_SET_OFFSET         = 8

class MEASURE_SHARPNESS_AOI_INFO(ctypes.Structure):
    """
    :var UINT u32NumberAOI:
    :var UINT u32SharpnessValue:
    :var IS_RECT rcAOI:
    """
    _fields_ = [("u32NumberAOI", wt.UINT),
                ("u32SharpnessValue", wt.UINT),
                ("rcAOI", IS_RECT)]

IS_MEASURE_CMD_SHARPNESS_AOI_SET        = 1
IS_MEASURE_CMD_SHARPNESS_AOI_INQUIRE    = 2
IS_MEASURE_CMD_SHARPNESS_AOI_SET_PRESET = 3

IS_MEASURE_SHARPNESS_AOI_PRESET_1 = 1

IS_IMGBUF_DEVMEM_CMD_GET_AVAILABLE_ITERATIONS      = 1
IS_IMGBUF_DEVMEM_CMD_GET_ITERATION_INFO            = 2
IS_IMGBUF_DEVMEM_CMD_TRANSFER_IMAGE                = 3
IS_IMGBUF_DEVMEM_CMD_RELEASE_ITERATIONS            = 4

class ID_RANGE(ctypes.Structure):
    """
    :var UINT u32First:
    :var UINT u32Last:
    """
    _fields_ = [("u32First", wt.UINT),
                ("u32Last", wt.UINT)]

class IMGBUF_ITERATION_INFO(ctypes.Structure):
    """
    :var UINT u32IterationID:
    :var ID_RANGE rangeImageID:
    :var BYTE[52] bReserved:
    """
    _fields_ = [("u32IterationID", wt.UINT),
                ("rangeImageID", ID_RANGE),
                ("bReserved", wt.BYTE * 52)]

class IMGBUF_ITERATION_INFO(ctypes.Structure):
    """
    :var UINT u32IterationID:
    :var UINT u32ImageID:
    """
    _fields_ = [("u32IterationID", wt.UINT),
                ("u32ImageID", wt.UINT)]
