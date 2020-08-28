mfl_mode = 'xy8'

mfl_script = "C:/Users/Setup3-PC/Desktop/qudi/logic/mfl_irq_driven.py"
if mfl_mode == 'multi':
    mfl_script = "C:/Users/Setup3-PC/Desktop/qudi/logic/mfl_multi_irq_driven.py"
if mfl_mode == 'hahn_1d':
    mfl_script = "C:/Users/Setup3-PC/Desktop/qudi/logic/mfl_hahn_irq_driven.py"
if mfl_mode == 'na':
    mfl_script = "C:/Users/Setup3-PC/Desktop/qudi/logic/mfl_na_irq_driven.py"
if mfl_mode == 'xy8':
    mfl_script = "C:/Users/Setup3-PC/Desktop/qudi/logic/mfl_xy8_irq_driven.py"
qudi_logic_dir = "C:/Users/Setup3-PC/Desktop/qudi/logic"
cmd = 'python ' + mfl_script

import os
import subprocess

os.chdir(qudi_logic_dir)

success = True
while success:
    retval = 0
    try:
        grepout = subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError as grepexc:
        retval = grepexc.returncode

    if retval != 0:
        print("mfl in seperate thread failed and returned with code {}".format(retval))
        #success = False
        #exit(1)