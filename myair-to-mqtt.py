#!/usr/bin/env python3

import argparse
import yaml
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import sys
from pymyair.pymyair import MyAir
from device_advantageair import Device_AdvantageAir
import time
import homie
import schedule
import logging

_version=0.8
_logger = logging.getLogger(__name__)
# default debugging level is:
_debug_level = logging.WARNING
#_debug_level = logging.INFO
#_debug_level = logging.DEBUG

def main():
    global _version
    global _logger
    global _debug_level

    parser = argparse.ArgumentParser(description='Wrapper for Advantage Air to MQTT', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(_version))
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Turn on debugging')
    parser.add_argument('-c', '--conf', dest='config_file', required=True, help='Specify the config file')

    args = parser.parse_args()

    # setup variables from the command line arguments
    debug = args.debug
    # if specified as a parameter, add more debugs
    if debug:
        _debug_level = logging.DEBUG
    config_file_path = args.config_file

    _logger.setLevel(_debug_level)
    # need to figure out how to set debugging on the down stream classes
    # logger is defined in the Homie4 library - specifically device_base.py
    # _debug_level is set in the myair-to-mqtt.py code
#    print(logging.root.manager.loggerDict)
#    print(logging.root.manager.loggerDict['homie.device_base'])
#    logging.getLogger('homie.device_base').setLevel(_debug_level)
#    logging.getLogger('homie').setLevel(_debug_level)
    logging.basicConfig(level=_debug_level)
#    print(logging.root.manager.loggerDict['homie.device_base'])


    FORMATTER = logging.Formatter('%(asctime)s: %(name)s: %(levelname)s: %(message)s')
#    LOG_FILE = '{}.log'.format(__name__)
    LOG_FILE_NAME = '{}.log'.format(os.path.basename(__file__))
    LOG_PATH = os.getenv('LOG_PATH', '/tmp')
    LOG_FILE = os.path.join(LOG_PATH, LOG_FILE_NAME)
    print(LOG_FILE)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    console_handler.setLevel(_debug_level)

    file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", backupCount=5)
    file_handler.setFormatter(FORMATTER)
    file_handler.setLevel(_debug_level)

    _logger.addHandler(console_handler)
    _logger.addHandler(file_handler)

    print('_debug_level == {}'.format(_debug_level))
#    logging.basicConfig(level=_debug_level, handlers=[console_handler, file_handler])

    HOMIE_SETTINGS = {
        'update_interval': 60,
        'implementation': 'MyAir to MQTT {} Homie 4 Version {}'.format(_version, homie.__version__),
        'fw_name': 'MyAir',
        'fw_version':_version,
    }

    # Read the config file
    if os.path.exists(os.path.expanduser(config_file_path)) is False:
        print('ERROR: config file not found - looking for "{}"'.format(os.path.expanduser(config_file_path)))
        sys.exit(1)
    else:
        with open(os.path.expanduser(config_file_path), 'r') as ifp:
            config = yaml.load(ifp, Loader=yaml.SafeLoader)

    mqtt_settings = config['mqtt_settings']
    if debug:
        print(mqtt_settings)
    myair_settings = config['myair_settings']
    if debug:
        print(myair_settings)
    myair_to_mqtt_settings = config['myair_to_mqtt_settings']
    if debug:
        print(myair_to_mqtt_settings)

    ma = MyAir(myair_settings['myair_addr'])
    ma.update()

    _myair_device = Device_AdvantageAir(device_id='advantageair', device_name='AdvantageAir', mqtt_settings=mqtt_settings, myair_device=ma, myair_settings=myair_settings, debug=debug)

    return _myair_device, myair_to_mqtt_settings

if __name__ == "__main__":
    print('starting')
    try:
        myair_device, myair_to_mqtt_settings = main()

        _logger.debug('debug')
        _logger.info('info')
        _logger.warning('warning')
        _logger.error('error')
        _logger.critical('critical')

        _logger.info('setting up schedule - refresh_interval {}'.format(myair_to_mqtt_settings['refresh_interval']))

        schedule.every(myair_to_mqtt_settings['refresh_interval']).seconds.do(myair_device.update)
        while True:
            schedule.run_pending()
            time.sleep(1)

        # this should never happen
        print('exiting')
    except (KeyboardInterrupt, SystemExit):
        print("Quitting")

# vim: expandtab
# END OF FILE
