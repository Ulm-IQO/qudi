#%%
from ctypes import CDLL, WinDLL
from ctypes import *
import os
import ctypes
# %%
this_dir = os.path.dirname(__file__)
prev_dir = os.getcwd()
os.chdir(this_dir)
rot_dll = CDLL("Thorlabs.Elliptec.ELLO_DLL.dll")
os.chdir(prev_dir)
# %%
is_connected = ctypes.WINFUNCTYPE(ctypes.c_void_p)
# %%
f = is_connected(("IsConnected", rot_dll))
# %%
rot_dll._DEVGET_INFORMATION
# %%
from serial import Serial, EIGHTBITS,STOPBITS_ONE,PARITY_NONE
# %%
s = Serial('COM5', baudrate=9600, bytesize=EIGHTBITS, stopbits=STOPBITS_ONE,parity= PARITY_NONE, timeout=2)
# %%
s.read(2)
# %%
s.close()
# %%
s.name
#%%
s.write(b'0in')
# %%
s.read(33)
# %%
s.write(b'0gs')
# %%
s.read(8)
# %%
s.write(b'0fw')
# %%
s.read(32)
# %%
s.write(b'0gp')
# %%
pos = s.read(32)
# %%
int("00002000", 16)

# %%
int("00007FFE", 16)
# %%
262144 / 32766
# %%

# %%
4294967295/ 262144
# %%
"".join(filter(lambda x: x not in "brn\\'", str(pos)))[3:]
# %%
def move_abs(to_angle):
    to_pos10 = to_angle * int((262144/ 360))
    print(to_pos10)
    to_pos16 = str(hex(to_pos10))[2:].upper().zfill(8)
    command = ("0ma" + to_pos16).encode('ascii')
    print(command)
    s.write(command)
# %%
def get_pos():
    s.write(b'0gp')
    pos16 = s.read(32)
    pos10 = int("".join(filter(lambda x: x not in "brn\\'", str(pos16)))[3:], 16)
    #revelation = 262144
    angle = 360 * pos10 / 262144
    return angle
# %%
get_pos()
# %%
move_abs(90)
# %%
my_hexdata = "00007FFE"

scale = 16 ## equals to hexadecimal

num_of_bits = 8

bin(int(my_hexdata, scale))[2:].zfill(num_of_bits)
# %%
