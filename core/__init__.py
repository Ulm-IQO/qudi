__version__ = '0.0.1'

import os, sys

# Set up a list of paths to search for configuration files 
# (used if no config is explicitly specified)

# First we check the parent directory of the current module.
# This path is used when running directly from a source checkout
modpath = os.path.dirname(os.path.abspath(__file__))
CONFIGPATH = [
    os.path.normpath(os.path.join(modpath, '..', 'config')),
    ]

# Next check for standard system install locations
if 'linux' in sys.platform or sys.platform == 'darwin':
    CONFIGPATH.append('/etc/qudi')

# Finally, look for an example config..
CONFIGPATH.extend([
    os.path.normpath(os.path.join(modpath, '..', 'config', 'example')),
    os.path.normpath(os.path.join(modpath, 'config', 'example')),
    ])


# If we are using PyQt, ACQ4 requires API version 2 for QString and QVariant. 
# Check for those here..
set_api = True
if 'PyQt4' in sys.modules:
    import sip
    for api in ['QString', 'QVariant']:
        try:
            v = sip.getapi(api)
            if v != 2:
                raise Exception("We require the use of API version 2 for QString and QVariant, but %s=%s. Correct this by calling \"import sip; sip.setapi('QString', 2); sip.setapi('QVariant', 2);\" _before_ importing PyQt4." % (api, v))
            else:
                set_api = False
        except ValueError:
            set_api = True
elif 'PySide' in sys.modules:
    set_api = False

if set_api:
    try:
        import sip
        sip.setapi('QString', 2)
        sip.setapi('QVariant', 2)
    except ImportError:
        pass  # no sip; probably pyside will be imported later..


# Import pyqtgraph, get QApplication instance
import pyqtgraph as pg
pg.setConfigOptions(useWeave=False)
app = pg.mkQApp()


## rename any orphaned .pyc files -- these are probably leftover from 
## a module being moved and may interfere with expected operation.
modDir = os.path.abspath(os.path.split(__file__)[0])
pg.renamePyc(modDir)


## Install a simple message handler for Qt errors:
def messageHandler(msgType, msg):
    import traceback
    print("Qt Error: (traceback follows)")
    print(msg)
    traceback.print_stack()
    try:
        logf = "crash.log"
            
        fh = open(logf, 'a')
        fh.write(msg+'\n')
        fh.write('\n'.join(traceback.format_stack()))
        fh.close()
    except:
        print("Failed to write crash log:")
        traceback.print_exc()
        
    
    if msgType == pg.Qt.QtCore.QtFatalMsg:
        try:
            print("Fatal error occurred; asking manager to quit.")
            global man, app
            man.quit()
            app.processEvents()
        except:
            pass
    
pg.QtCore.qInstallMsgHandler(messageHandler)
