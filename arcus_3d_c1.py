import os

from machinekit import rtapi as rt
from machinekit import hal
from machinekit import config as c

from fdm.config import velocity_extrusion as ve
from fdm.config import base
from fdm.config import storage
from fdm.config import motion
import bebopr as hardware

# initialize the RTAPI command client
rt.init_RTAPI()
# loads the ini file passed by linuxcnc
c.load_ini(os.environ['INI_FILE_NAME'])

motion.setup_motion(kinematics='itripodkins')
hal.Pin('itripodkins.Bx').set(c.find('MACHINE', 'TRIPOD_BX'))
hal.Pin('itripodkins.Cx').set(c.find('MACHINE', 'TRIPOD_CX'))
hal.Pin('itripodkins.Cy').set(c.find('MACHINE', 'TRIPOD_CY'))

hardware.init_hardware()
storage.init_storage('storage.ini')

# reading functions
hardware.hardware_read()
hal.addf('motion-command-handler', 'servo-thread')
hal.addf('motion-controller', 'servo-thread')

numFans = c.find('FDM', 'NUM_FANS')
numExtruders = c.find('FDM', 'NUM_EXTRUDERS')
numLights = c.find('FDM', 'NUM_LIGHTS')
hasHbp = c.find('FDM', 'HAS_HBP')

# Axis-of-motion Specific Configs (not the GUI)
ve.velocity_extrusion(extruders=numExtruders, thread='servo-thread')
# XYZ axes
for i in range(3):
    base.setup_stepper(section='AXIS_%i' % i, axisIndex=i, stepgenIndex=i, thread='servo-thread')
# Extruder, velocity controlled
for i in range(0, numExtruders):
    base.setup_stepper(section='EXTRUDER_%i' % i, stepgenIndex=(3 + i),
                       velocitySignal='ve-extrude-vel')

# Extruder Multiplexer
base.setup_extruder_multiplexer(extruders=numExtruders, thread='servo-thread')

# Stepper Multiplexer
multiplexSections = []
for i in range(0, numExtruders):
    multiplexSections.append('EXTRUDER_%i' % i)
base.setup_stepper_multiplexer(stepgenIndex=4, sections=multiplexSections,
                               selSignal='extruder-sel', thread='servo-thread')

# Fans
for i in range(0, numFans):
    base.setup_fan('f%i' % i, thread='servo-thread')

# Temperature Signals
if hasHbp:
    base.create_temperature_control(name='hbp', section='HBP',
                                    hardwareOkSignal='temp-hw-ok',
                                    thread='servo-thread')
for i in range(0, numExtruders):
    hardware.setup_exp('exp%i' % i)
    base.create_temperature_control(name='e%i' % i, section='EXTRUDER_%i' % i,
                                    coolingFan='f%i' % i,
                                    hotendFan='exp%i' % i,
                                    hardwareOkSignal='temp-hw-ok',
                                    thread='servo-thread')

# LEDs
for i in range(0, numLights):
    base.setup_light('l%i' % i, thread='servo-thread')

# Standard I/O - EStop, Enables, Limit Switches, Etc
errorSignals = ['temp-hw-error', 'watchdog-error', 'hbp-error']
for i in range(0, numExtruders):
    errorSignals.append('e%i-error' % i)
#errorSignals = []
base.setup_estop(errorSignals, thread='servo-thread')
base.setup_tool_loopback()
# Probe
base.setup_probe(thread='servo-thread')
# Setup Hardware
hardware.setup_hardware(thread='servo-thread')

# write out functions
hardware.hardware_write()

# read storage.ini
storage.read_storage()

# start haltalk server after everything is initialized
# else binding the remote components on the UI might fail
hal.loadusr('haltalk', wait=True)
