#!python3

# *********************************************************
# Script to decode and plot an M8190A/M8195A waveform binary
# Usage: deliver path to channel file as argument to this
# program (eg. in Pycharm: Run->Edit Conf->Parameters)
# *********************************************************

# =========================================================
# Import Modules
# =========================================================
import sys
import os
import struct
import scipy.interpolate
import numpy as np
import matplotlib

matplotlib.use('Qt5Agg')  # allows interactive mode in Pycharm
import matplotlib.pyplot as plt



def sign_extend(value, bits):
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)

def decode_m8190_val(val_int):
    shiftbits = 16 - dac_resolution  # 2 for marker, dac: 12 -> 2, dac: 14 -> 4

    val_int = np.asarray(val_int).astype('uint16')

    bit_marker = 0x1 & val_int
    bit_sync = 0x2 & val_int >> 1

    analog_binary = (0xFFFC & val_int) >>  shiftbits
    #print("Debug: Analog bit {:#016b}".format(analog_binary))
    # sign extend to correctly fit 14 bit of 2s complement into 16 bit int
    int_analog = np.int16(sign_extend(analog_binary, 14))

    return np.asarray(int_analog, dtype=np.int16), np.asarray(bit_marker, dtype=np.bool), np.asarray(bit_sync, dtype=np.bool)

def decode_m8195_val(val_int, channel="a_ch1"):

    val_int = np.asarray(val_int).astype('uint16')

    if channel == "a_ch1":
        val = (val_int & 0x00FF)
    elif channel == 'd_ch1':
        val = (val_int >> 8 & 0x1)
    elif channel == "d_ch2":
        val = (val_int >> 8 & 0x2) >> 1
    else:
        raise NotImplementedError

    val_int = np.asarray(val).astype('int8')

    return val_int

def analog_int_to_normalized_float(val_int):
    bitsize = int(2 ** dac_resolution)
    min_intval = -bitsize / 2
    max_intval = bitsize / 2 - 1

    mapper = scipy.interpolate.interp1d([min_intval, max_intval], [-1.0,1.0])
    return mapper(val_int).astype('float')

# shaddows Tk_file
def get_filename_no_extension(filename):
    return os.path.splitext(filename)[0]

def get_extension(filename):
    return os.path.splitext(filename)[1]

def split_path_to_folder(path):
    # https://stackoverflow.com/questions/3167154/how-to-split-a-dos-path-into-its-components-in-python
    folders = []
    while 1:
        path, folder = os.path.split(path)

        if folder != "":
            folders.append(folder)
        else:
            if path != "":
                folders.append(path)

            break

    folders.reverse()
    return folders


def strip_ch_str(path):
    path = path.replace("_ch1", "")
    path = path.replace("_ch2", "")

    return path

def get_waveform_files(fname, mode='bin'):
    if mode == 'bin':
        # eg. AWG8190
        path_ch1 = strip_ch_str(path) + "_ch1" + ".bin"
        path_ch2 = strip_ch_str(path) + "_ch2" + ".bin"
    elif mode == 'bin8':
        # AWG8195: all in one file
        path_ch1 = strip_ch_str(path) + "_ch1" + ".bin8"
        path_ch2 = None
    else:
        raise ValueError("Unknown loading mode: {}".format(mode))

    print("Loading waveforms file1: {}, file2: {}. Mode: {}".format(path_ch1, path_ch2, mode))

    return path_ch1, path_ch2

def load_waveform_files(fname, mode='bin'):
    path_ch1, path_ch2 = get_waveform_files(fname, mode)
    try:
        bin_ch1 = open(path_ch1, "rb")
    except:
        bin_ch1 = None
    try:
        bin_ch2 = open(path_ch2, "rb")
    except:
        bin_ch2 = None

    return bin_ch1, bin_ch2


def _decode_from_int16(int_array, mode="bin", channel_config=None):

    n_data = len(int_array)
    print("Debug: Starting decoding {} int16 values.".format(n_data))

    t_us = 1e6 * np.asarray(range(n_data)) / sampling_rate

    # SLOOOOW:
    #res = [_decode_two_bytes(val16, mode, channel_config) for val16 in np.asarray(int_array).astype('uint16')]

    int_array = np.asarray(int_array).astype('uint16')

    if mode == 'bin':
        int_analog, bit_marker, bit_sync = decode_m8190_val(int_array)
    elif mode == 'bin8':
        if channel_config == 'marker':
            int_analog = decode_m8195_val(int_array, 'a_ch1')
            # marker sync only exist for M8190A
            bit_marker = decode_m8195_val(int_array, 'd_ch1')
            bit_sync = decode_m8195_val(int_array, 'd_ch2')
        else:
            raise NotImplementedError
    else:
        raise ValueError("Ubnknown mode: {}".format(mode))


    """
    wave_analog_int = [el[0] for el in res]
    wave_analog = [analog_int_to_normalized_float(el) for el in wave_analog_int]
    wave_sample_marker = [el[1] for el in res]
    wave_sync_marker = [el[2] for el in res]
    """
    wave_analog_int = int_analog
    wave_analog = analog_int_to_normalized_float(wave_analog_int)
    wave_sample_marker = bit_marker
    wave_sync_marker = bit_sync

    print("Debug: Decode done.")

    return t_us, wave_analog, wave_analog_int, wave_sample_marker, wave_sync_marker


def _decode_two_bytes(val_int16, mode='bin', channel_config=None):
    # typtical file has a lot of 0s, break here for performance
    if val_int16 == 0:
        return 0, 0, 0

    if mode == 'bin':
        analog, marker, sync = decode_m8190_val(val_int16)
    elif mode == 'bin8':
        if channel_config == 'marker':
            analog = decode_m8195_val(val_int16, 'a_ch1')
            # marker sync only exist for M8190A
            marker = decode_m8195_val(val_int16, 'd_ch1')
            sync = decode_m8195_val(val_int16, 'd_ch2')
        else:
            raise NotImplementedError
    else:
        raise ValueError("Unknown decoding mode: {}".format(mode))

    return analog, marker, sync

def _decode(bin_input, mode="bin", channel_config=None):

    n_bytes = 2

    bin_input.seek(0, os.SEEK_END)
    n_data = int(bin_input.tell() / n_bytes)  # 2 bytes per value
    bin_input.seek(0, os.SEEK_SET)  # move to beginning of file again

    t_us = 1e6 * np.asarray(range(n_data)) / sampling_rate
    wave_analog = np.zeros((n_data), dtype=float)
    wave_analog_int = np.zeros((n_data), dtype=np.int16)
    wave_sample_marker = np.zeros((n_data), dtype=bool)
    wave_sync_marker = np.zeros((n_data), dtype=bool)


    # Todo: Speed up by reading into buffer, instead of looping
    for i in range(n_data):
        try:
            (val_int,) = struct.unpack('H', bin_input.read(n_bytes))
            analog, marker, sync = _decode_two_bytes(val_int, mode, channel_config=channel_config)
            wave_analog[i] = analog_int_to_normalized_float(analog)
            wave_analog_int[i] = analog
            wave_sample_marker[i] = marker
            wave_sync_marker[i] = sync

        except Exception as e:
            print("Error: Breaking due to unexpected end of file at i= {}".format(i))
            print("Error: {}".format(str(e)))
            break

    return t_us, wave_analog, wave_analog_int, wave_sample_marker, wave_sync_marker


def decode_int16_to_wave(int_array, mode='bin', channel_config=None):
    if mode == 'bin':
        if channel_config is not None:
            print("Warning: ignoring specified channel {}".format(channel_config))
        return _decode_from_int16(int_array, mode=mode)
    elif mode == 'bin8':
        return _decode_from_int16(int_array, mode=mode, channel_config='marker')
    else:
        raise ValueError("Unknown decoding mode: {}".format(mode))

def decode_bin_to_wave(bin_input, mode='bin', channel_config=None):
    if mode == 'bin':
        if channel_config is not None:
            print("Warning: ignoring specified channel {}".format(channel_config))
        return _decode(bin_input, mode=mode)
    elif mode == 'bin8':
        return _decode(bin_input, mode=mode, channel_config='marker')
    else:
        raise ValueError("Unknown decoding mode: {}".format(mode))




dac_resolution = 14
sampling_rate = 8e9
time_it = False
# =========================================================
# Main Program
# =========================================================

if len(sys.argv) != 2:
    sys.stderr.write("Usage: python %s <binary_data_file>\n" % sys.argv[0])
    sys.exit()

print("Settings: Sampling Rate: {}; DAC res (M8190A only): {} bit".format(sampling_rate,
                                     Y                                     dac_resolution))

path = get_filename_no_extension(sys.argv[1])
ext = get_extension(sys.argv[1])[1:]

import datetime
start_fast = datetime.datetime.now()

path_ch1, path_ch2 = get_waveform_files(path, mode=ext)
data_ch1 = np.fromfile(path_ch1, dtype=np.uint16, count=-1)
try:
    data_ch2 = np.fromfile(path_ch2, dtype=np.uint16, count=-1)
except:
    pass

if ext == 'bin':
    t_us_ch1, w_analog_ch1, w_analog_int_ch1, w_sample_marker_ch1, w_sync_marker_ch1 = decode_int16_to_wave(data_ch1, mode=ext)
    t_us_ch2, w_analog_ch2, w_analog_int_ch2, w_sample_marker_ch2, w_sync_marker_ch2 = decode_int16_to_wave(data_ch2, mode=ext)
elif ext == 'bin8':
    t_us_ch1, w_analog_ch1, _, w_sample_marker_ch1, w_sync_marker_ch1 = decode_int16_to_wave(data_ch1,
                                                                                             mode=ext, channel_config='marker')
else:
    raise NotImplementedError


if time_it:
    stop_fast = datetime.datetime.now()
    start_slow = datetime.datetime.now()

    bin_in_ch1, bin_in_ch2 = load_waveform_files(path, mode=ext)
    if ext == 'bin':
        t_us_ch1, w_analog_ch1, w_analog_int_ch1, w_sample_marker_ch1, w_sync_marker_ch1 = decode_bin_to_wave(bin_in_ch1, mode=ext)
        t_us_ch2, w_analog_ch2, w_analog_int_ch2, w_sample_marker_ch2, w_sync_marker_ch2 = decode_bin_to_wave(bin_in_ch2, mode=ext)
    elif ext == 'bin8':
        t_us_ch1, w_analog_ch1, _, w_sample_marker_ch1, w_sync_marker_ch1 = decode_bin_to_wave(bin_in_ch1,
                                                                                               mode=ext, channel_config='marker')
    else:
        raise NotImplementedError
    stop_slow = datetime.datetime.now()

    print("Debug profiling: Fast: {}, Slow: {}".format(stop_fast-start_fast, stop_slow-start_slow))



# Plotting waveforms
plt.ion()

plt.plot(t_us_ch1, w_analog_ch1, label="Ch1: analog", color="blue")
plt.plot(t_us_ch1, w_sample_marker_ch1 - 2, label="M1: sample", color="orange")
plt.plot(t_us_ch1, w_sync_marker_ch1 - 3, label="M2: sync", color="green")

try:
    plt.plot(t_us_ch2, w_analog_ch2 - 4, label="Ch2: analog", color="blue")
    plt.plot(t_us_ch2, w_sample_marker_ch2 - 5, label="M3: sample", color="orange")
    plt.plot(t_us_ch2, w_sync_marker_ch2 - 6, label="M4: sync", color="green")
except:
    pass    # no a_ch2 for bin8

plt.xlabel("t (us)")
plt.legend()

# lines between channels
plt.axhline(-3, linestyle="--", color='grey')
#plt.axhline(-2, linestyle="--", color='grey')

plt.show(block=False)

keyboardClick=False
print("Any key to exit.")
while keyboardClick != True:
    keyboardClick=plt.waitforbuttonpress()


"""
bin_in_ch1.close()
bin_in_ch2.close()
"""
sys.exit()

