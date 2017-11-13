from machinekit import hal
from machinekit import rtapi as rt
from machinekit import config as c

from fdm.config import base


def hardware_read():
    hal.addf('hpg.capture-position', 'servo-thread')
    hal.addf('bb_gpio.read', 'servo-thread')


def hardware_write():
    hal.addf('hpg.update', 'servo-thread')
    hal.addf('bb_gpio.write', 'servo-thread')


def init_hardware():
    watchList = []

    # load low-level drivers
    rt.loadrt('hal_bb_gpio', output_pins='807,808,810,819,828,840,841', input_pins='809,831,832,833,835,837,838')
    prubin = '%s/%s' % (c.Config().EMC2_RTLIB_DIR, c.find('PRUCONF', 'PRUBIN'))
    rt.loadrt(c.find('PRUCONF', 'DRIVER'),
              pru=1, num_stepgens=4, num_pwmgens=3,
              prucode=prubin, halname='hpg')

    # Python user-mode HAL module to read ADC value and generate a thermostat output for PWM
    defaultThermistor = 'semitec_103GT_2'
    hal.loadusr('hal_temp_bbb',
                name='temp',
                interval=0.10,
                filter_size=5,
                cape_board='CRAMPS',
		r_pu=2185, # measured value of my 2.2k pullup resistor
                channels='04:%s,05:%s'
                % (c.find('HBP', 'THERMISTOR', defaultThermistor),
                   c.find('EXTRUDER_0', 'THERMISTOR', defaultThermistor)),
                wait_name='temp')
    watchList.append(['temp', 0.2])

    base.usrcomp_status('temp', 'temp-hw', thread='servo-thread')
    base.usrcomp_watchdog(watchList, 'estop-reset', thread='servo-thread',
                          errorSignal='watchdog-error')


def setup_hardware(thread):
    # PWM
    hal.Pin('hpg.pwmgen.00.pwm_period').set(100000000)  # 1000Hz
    hal.Pin('hpg.pwmgen.00.out.00.pin').set(836)  # J4 HBP
    hal.Pin('hpg.pwmgen.00.out.01.pin').set(845)  # J2 E0
    hal.Pin('hpg.pwmgen.00.out.02.pin').set(846)  # J3 F0
    # HBP
    hal.Pin('hpg.pwmgen.00.out.00.enable').set(True)
    hal.Pin('hpg.pwmgen.00.out.00.value').link('hbp-temp-pwm')
    # configure extruders
    offset = 1
    for n in range(0, 1):
        hal.Pin('hpg.pwmgen.00.out.%02i.enable' % (n + offset)).set(True)
        hal.Pin('hpg.pwmgen.00.out.%02i.value' % (n + offset)).link('e%i-temp-pwm' % n)
    # configure fans
    offset = 2
    for n in range(0, 1):
        hal.Pin('hpg.pwmgen.00.out.%02i.enable' % (n + offset)).link('f%i-pwm-enable' % n)
        hal.Pin('hpg.pwmgen.00.out.%02i.value' % (n + offset)).link('f%i-pwm' % n)
        hal.Signal('f%i-pwm-enable' % n).set(True)

    # configure hotend cooling fan
    #hal.Pin('hpg.pwmgen.00.out.05.enable').link('exp0-pwm-enable')
    #hal.Pin('hpg.pwmgen.00.out.05.value').set(1.0)
    #hal.Pin('hpg.pwmgen.00.out.05.value').link('exp0-pwm')
    # configure leds
    # none

    # GPIO
    hal.Pin('bb_gpio.p8.in-31').link('limit-0-home')   # X
    #hal.Pin('bb_gpio.p8.in-31').link('limit-0-max')    # X
    hal.Pin('bb_gpio.p8.in-35').link('limit-1-home')   # Y
    #hal.Pin('bb_gpio.p8.in-35').link('limit-1-max')    # Y
    hal.Pin('bb_gpio.p8.in-38').link('limit-2-home')   # Z
    #hal.Pin('bb_gpio.p8.in-38').link('limit-2-max')    # Z
    # probe ...

    # Adjust as needed for your switch polarity
    hal.Pin('bb_gpio.p8.in-31.invert').set(False)
    #hal.Pin('bb_gpio.p8.in-32.invert').set(False)
    hal.Pin('bb_gpio.p8.in-35.invert').set(False)
    #hal.Pin('bb_gpio.p8.in-33.invert').set(False)
    hal.Pin('bb_gpio.p8.in-38.invert').set(False)
    #hal.Pin('bb_gpio.p8.in-37.invert').set(False)

    # ADC
    hal.Pin('temp.ch-05.value').link('hbp-temp-meas')
    hal.Pin('temp.ch-04.value').link('e0-temp-meas')
    #hal.Pin('temp.ch-05.value').link('e1-temp-meas')

    # Stepper
    hal.Pin('hpg.stepgen.00.steppin').set(843)
    hal.Pin('hpg.stepgen.00.dirpin').set(844)
    hal.Pin('hpg.stepgen.01.steppin').set(842)
    hal.Pin('hpg.stepgen.01.dirpin').set(839)
    hal.Pin('hpg.stepgen.02.steppin').set(827)
    hal.Pin('hpg.stepgen.02.dirpin').set(829)
    hal.Pin('hpg.stepgen.03.steppin').set(830)
    hal.Pin('hpg.stepgen.03.dirpin').set(834)

    # axis enable signals
    hal.Pin('bb_gpio.p8.out-41').link('emcmot-0-enable')
    hal.Pin('bb_gpio.p8.out-41.invert').set(True)
    hal.Pin('bb_gpio.p8.out-40').link('emcmot-1-enable')
    hal.Pin('bb_gpio.p8.out-40.invert').set(True)
    hal.Pin('bb_gpio.p8.out-28').link('emcmot-2-enable')
    hal.Pin('bb_gpio.p8.out-28.invert').set(True)
    hal.Pin('bb_gpio.p8.out-19').link('emcmot-3-enable')
    hal.Pin('bb_gpio.p8.out-19.invert').set(True)

    # Machine power 
    hal.Pin('bb_gpio.p8.out-08').link('estop-loop')
    hal.Pin('bb_gpio.p8.in-09').link('estop-in')
    #hal.Pin('bb_gpio.p8.in-09.invert').set(True)
    hal.Pin('bb_gpio.p8.out-07').link('estop-out')
    #hal.Pin('bb_gpio.p8.out-07.invert').set(True)

    # Tie machine power signal to the BeBoPr LED
    # Feel free to tie any other signal you like to the LED
    hal.Pin('bb_gpio.p8.out-10').link('emcmot-0-enable')


def setup_exp(name):
    hal.newsig('%s-pwm' % name, hal.HAL_FLOAT, init=0.0)
    hal.newsig('%s-pwm-enable' % name, hal.HAL_BIT, init=False)
