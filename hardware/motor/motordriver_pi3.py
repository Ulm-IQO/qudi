# ----------------------------------------------------------------------------
#  Motordriver.py: 3. PI, Uni Stuttgart
#  Copyright (C) 2014  Stefan Lasse
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------

import time
import serial

from core.module import Base
from core.configoption import ConfigOption

class Motordriver(Base):
    """ Gives an interface to the Motordriver. """
    _port = ConfigOption('port', 'COM3', missing='warn')
    _active_motor_numbers = ConfigOption('active_motor_numbers', [], missing='warn')
    ON = "1"
    OFF = "0"

    STEPS = "steps"
    DEGREE = "deg"
    PI = "pi"

    CW = "CW"
    CCW = "CCW"
    STOP = "STOP"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ser = serial.Serial(
            port = self._port,
            baudrate = 57600,
            bytesize = serial.EIGHTBITS,
            parity = serial.PARITY_NONE,
            stopbits = serial.STOPBITS_ONE,
            timeout = 5,
            xonxoff = 0,
            rtscts = 0,
            dsrdtr = 0,
            writeTimeout = 5
        )
        self.ser.close()
        # self.ser.open()
        time.sleep(0.5)

    # def __del__(self):
    #     if self.ser.isOpen():
    #         self.ser.close()

    # --------------------------------------------------------------------------
    # helpers
    # --------------------------------------------------------------------------

    # --------------------------------------------------------------------------
    def on_activate(self):
        self.ser.open()
    def on_deactivate(self):
        self.ser.close()

    def __checkMotor(self, motor):
        
        if not isinstance(motor, int):
            print("error: motor number must be an integer.")
            return False
        if (motor > 3) and (motor < 0):
            print("motor number is from 0 to 3")
            return False
        if motor in self._active_motor_numbers:
            return True
        else:
            print("Test if the given motor is active and hooked up to the motor itself.")

    # --------------------------------------------------------------------------
    def __checkUnit(self, unit):
        if unit == self.STEPS or unit == self.DEGREE or unit == self.PI:
            return True
        else:
            return False

    # --------------------------------------------------------------------------
    # low level functionality
    # --------------------------------------------------------------------------

    # --------------------------------------------------------------------------
    def __sendCommand(self, cmd):
        ack = "A"
        maxtries = 0
        self.ser.flushOutput()

        while ord(ack) != 6 and maxtries < 10:
            #print(cmd)
            self.ser.write((cmd + '\n').encode('utf-8'))
            self.ser.flush()
            time.sleep(0.05)
            maxtries += 1
            while self.ser.inWaiting() == 0:
                pass

            if self.ser.inWaiting() > 0:
                ack = self.ser.read(1)

        if maxtries == 9:
            print("error: unable to send command: " + cmd)

        self.ser.flushOutput()
        return

    # --------------------------------------------------------------------------
    def __readResponse(self):
        out = bytes()
        while self.ser.inWaiting() > 0:
            c = self.ser.read(1)
            if c.decode('utf-8') != '\n':
                c = c
                out += c
                print(c.decode('utf-8'))
        self.ser.flushInput()
        print(out.decode('utf-8'))
        return out.decode('utf-8')

    # --------------------------------------------------------------------------
    # command implementation
    # --------------------------------------------------------------------------

    # --------------------------------------------------------------------------
    def reset(self):
        self.__sendCommand("STOPALL")
        self.__sendCommand("*RST")
        return

    # --------------------------------------------------------------------------
    def getIDN(self):
        self.__sendCommand("*IDN?")
        return str(self.__readResponse())

    # --------------------------------------------------------------------------
    def setIDN(self, id):
        if not isinstance(id, basestring):
            print("ID is not a string.")
            return

        if len(id) > 20:
            print("IDN too long. max: 20 characters")
            return

        if len(id) == 0:
            print("IDN too short. min: 1 character")
            return

        self.__sendCommand("*IDN " + id)
        return

    # --------------------------------------------------------------------------
    def moveToAbsolutePosition(self, motor = 0, pos = 0, unit = DEGREE):
        if unit is self.STEPS and not isinstance(pos, int):
            print("err: unit is STEPS, so position must be an integer")
            return

        if pos < 0:
            print("position must be a positive value")
            return

        if self.__checkMotor(motor) and self.__checkUnit(unit):
            cmd = "MOVEABS " + str(motor) + " " + str(pos) + " " + unit
            self.__sendCommand(cmd)
        return

    # --------------------------------------------------------------------------
    def moveRelative(self, motor = 0, pos = 0, unit = DEGREE):
        if unit is self.STEPS and not isinstance(pos, int):
            print("err: unit is STEPS, so position must be an integer")
            return

        if self.__checkMotor(motor) and self.__checkUnit(unit):
            cmd = "MOVEREL " + str(motor) + " " + str(pos) + " " + unit
            self.__sendCommand(cmd)
        return

    # --------------------------------------------------------------------------
    def zeroMotor(self, motor = 0):
        if self.__checkMotor(motor):
            self.__sendCommand("ZERORUN " + str(motor))
        return

    # --------------------------------------------------------------------------
    def turnOnMotor(self, motor = 0):
        if self.__checkMotor(motor):
            self.__sendCommand("ENABLE " + str(motor) + " " + self.ON)
        return

    # --------------------------------------------------------------------------
    def turnOffMotor(self, motor = 0):
        if self.__checkMotor(motor):
            self.__sendCommand("ENABLE " + str(motor) + " " + self.OFF)

    # --------------------------------------------------------------------------
    def getPosition(self, motor = 0, unit = DEGREE):
        if self.__checkMotor(motor) and self.__checkUnit(unit):
            self.__sendCommand("GETPOS " + str(motor) + " " + unit)
            return float(self.__readResponse())
        return

    # --------------------------------------------------------------------------
    def saveCurrentConfiguration(self):
        self.__sendCommand("SAVECONF")
        return

    # --------------------------------------------------------------------------
    def loadSavedConfiguration(self):
        self.__sendCommand("LOADCONF")
        return

    # --------------------------------------------------------------------------
    def isMoving(self, motor = 0):
        if self.__checkMotor(motor):
            self.__sendCommand("ISMOVING " + str(motor))
            resp = self.__readResponse()
            if resp == "1":
                return True
            else:
                return False
        return

    # --------------------------------------------------------------------------
    def getAnalogValue(self, channel = 0):
        if self.__checkMotor(channel):
            self.__sendCommand("GETANALOG " + str(channel))
            return int(self.__readResponse())
        return

    # --------------------------------------------------------------------------
    def getOpticalZeroPosition(self, motor = 0):
        if self.__checkMotor(motor):
            self.__sendCommand("GETZEROPOS " + str(motor))
            return int(self.__readResponse())
        return

    # --------------------------------------------------------------------------
    def getOpticalZeroPosition2(self, motor = 0):
        if self.__checkMotor(motor):
            self.__sendCommand("GETOPTZEROPOS " + str(motor))
            return int(self.__readResponse())
        return

    # --------------------------------------------------------------------------
    def setOpticalZeroPosition(self, motor = 0, position = 1947):
        if not isinstance(position, int):
            print("optical zero position must be given in steps, integer.")
            return

        if self.__checkMotor(motor):
            cmd = "SETZEROPOS " + str(motor) + " " + str(position)
            self.__sendCommand(cmd)
        return


# --------------------------------------------------------------------------

    def setOpticalZeroPosition2(self, motor = 0, position = 0):
        if not isinstance(position, int):
            print("optical zero position must be given in steps, integer.")
            return

        if self.__checkMotor(motor):
            cmd = "SETOPTZEROPOS " + str(motor) + " " + str(position)
            self.__sendCommand(cmd)
        return

    # --------------------------------------------------------------------------
    def getGearRatio(self, motor = 0):
        if self.__checkMotor(motor):
            self.__sendCommand("GETGEARRATIO " + str(motor))
            return float(self.__readResponse())
        return

    # --------------------------------------------------------------------------
    def setGearRatio(self, motor = 0, ratio = 60.0 / 18.0):
        if self.__checkMotor(motor):
            cmd = "SETGEARRATIO " + str(motor) + " " + str(ratio)
            self.__sendCommand(cmd)
        return

    # --------------------------------------------------------------------------
    def getStepsPerFullRotation(self, motor = 0):
        if self.__checkMotor(motor):
            self.__sendCommand("GETFULLROT " + str(motor))
            return int(self.__readResponse())
        return

    # --------------------------------------------------------------------------
    def setStepsPerFullRotation(self, motor = 0, steps = 400):
        if not isinstance(steps, int):
            print("must be given as integer number")
            return

        if steps != 200.0 and steps != 400.0:
            print("steps must be either 200 or 400.")
            return

        if self.__checkMotor(motor):
            cmd = "SETFULLROT " + str(motor) + " " + str(steps)
            self.__sendCommand(cmd)
        return

    # --------------------------------------------------------------------------
    def getSubSteps(self, motor = 0):
        if self.__checkMotor(motor):
            self.__sendCommand("GETSUBSTEPS " + str(motor))
            return int(self.__readResponse())
        return

    # --------------------------------------------------------------------------
    def setSubSteps(self, motor = 0, substeps = 4):
        if not isinstance(substeps, int):
            print("must be given as integer number")
            return

        if substeps != 0 and ((substeps and (substeps - 1)) == 0):
            print("substeps must be a power of two")
            return

        if substeps < 1 or substeps > 16:
            print("substeps must be a positive number")
            return

        if self.__checkMotor(motor):
            cmd = "SETSUBSTEPS " + str(motor) + " " + str(substeps)
            self.__sendCommand(cmd)
        return

    # --------------------------------------------------------------------------
    def getWaitTimeBetweenSteps(self, motor = 0):
        if self.__checkMotor(motor):
            self.__sendCommand("GETWAITTIME " + str(motor))
            return int(self.__readResponse())
        return

    # --------------------------------------------------------------------------
    def setWaitTimeBetweenSteps(self, motor = 0, waittime = 3):
        if not isinstance(waittime, int):
            print("waittime must be given as integer number")
            return

        if waittime < 1:
            print("waittime must be >= 1")
            return

        if self.__checkMotor(motor):
            cmd = "SETWAITTIME " + str(motor) + " " + str(waittime)
            self.__sendCommand(cmd)
        return

    # --------------------------------------------------------------------------
    def setConstAngularVelocity(self, motor = 0, direction = CW, time = 10.0):
        if time < 5.0:
            print("time must be >= 5.0 seconds")
            return

        if self.__checkMotor(motor):
            cmd = "SETCONSTSPEED " + str(motor
                                        ) + " " + direction + " " + str(time)
            self.__sendCommand(cmd)
        return

    # --------------------------------------------------------------------------
    def factoryReset(self):
        self.__sendCommand("FACTORYRESET")
        return

    # --------------------------------------------------------------------------
    def stopAllMovements(self):
        self.__sendCommand("STOPALL")
        return
