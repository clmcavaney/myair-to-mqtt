import datetime
import zoneinfo

from homie.device_base import Device_Base
from homie.node.node_base import Node_Base

from homie.node.property.property_setpoint import Property_Setpoint
from homie.node.property.property_temperature import Property_Temperature
from homie.node.property.property_enum import Property_Enum
from homie.node.property.property_string import Property_String
from homie.node.property.property_button import Property_Button
from homie.node.property.property_integer import Property_Integer
from homie.node.property.property_datetime import Property_DateTime


FAN_SPEEDS = ['low', 'medium', 'high']
OPERATION_MODES = ['on', 'off', 'cool', 'heat', 'fan', 'dry']
ZONE_STATES = ['open', 'close']
SYSTEM_MODES = ['on', 'off']

class Node_AdvantageAirZone(Node_Base):
    zone_details = None
    myair_device = None
    debug = None

    def __init__(
        self, device, id, name, type_, zone_details, myair_device, debug=False
    ):
        assert device, 'Homie device required'
        assert id, 'id for node required'
        assert name, 'name for node required'
        assert type_, 'type for node required'

        # can't use self.debug here as the class variable hasn't been initialised at this point
        if debug:
            print('{}: device {} id {} name {} type {}'.format(__class__.__name__, device, id, name, type))
        super().__init__(device, id, name, type_)

        self.zone_details = zone_details
        self.myair_device = myair_device
        self.debug = debug

        self.add_property(
            Property_Setpoint(
                self, id='tempsetpoint', name='Temperature Setpoint', unit='C', set_value=lambda value: self.set_zone_temp_setpoint(value)
            )
        )
        self.add_property(
            Property_Temperature(
                self, id='tempmeasured', name='Temperature Measured', unit='C'
            )
        )
        self.add_property(
            Property_Enum(
                self, id='zone-state', name='Zone State', data_format=','.join(ZONE_STATES), set_value=lambda value: self.set_zone_state(value)
            )
        )

        self.add_property(
            Property_Enum(
                self, id="zone-mode", name="Zone Mode", data_format=','.join(OPERATION_MODES), set_value=lambda value: self.set_zone_mode(value)
            )
        )

        # note: value will be set when zone state is first changed after this device starts
        self.add_property(
            Property_DateTime(
                self, id="zone-state-change-ts", name="Zone State Change Timestamp"
            )
        )


        if debug:
            print('Node_AdvantageAirZone() details: topic:{} controls mode:{}'.format(super().topic, device.get_node('controls').get_property('mode').value))
            print('super(): {}'.format(super()))
            print('self.device: {}'.format(self.device))
            print('Node_AdvantageAirZone() details: alternative method - controls mode:{}'.format(self.device.get_node('controls').get_property('mode').value))

    def set_zone_temp_setpoint(self, value):
        if self.debug:
            print('{}: set_zone_temp_setpoint()'.format(self.__class__.__name__))
            print(self.id)
            print(self.name)
            print('zone_details == {}'.format(self.zone_details))
            print('myair_device == {}'.format(self.myair_device))
        # this is where we would set the temperature of the appropriate zone
        # e.g. setZone(id=3, state='on', set_temp=26)
        # self.myair_device.setZone()
        self.myair_device.setZone(id=self.zone_details['number'], set_temp=value)
        

    def set_zone_state(self, value):
        if self.debug:
            print('{}: set_zone_state() value:{}'.format(self.__class__.__name__, value))
            print(self.name)
        # This is a bit messy - setZone() requires a temperature when just changing the state of the zone (i.e. open or close).  Not sure if this is a limitation in the pymyair wrapper of the AdvantageAir API 
        self.myair_device.setZone(id=self.zone_details['number'], state=value, set_temp=self.zone_details['setTemp'], value=100)
        self.set_zone_state_change_ts(True)

    def set_zone_mode(self, value):
        if self.debug:
            print('{}: set_zone_mode() value:{}'.format(self.__class__.__name__, value))
            print(self.name)
        # Leveraging set_zone_state() logic, but essentially if the mode == off, state will be set to close, otherwise open
        _zone_state = 'open'
        if value == 'off':
            _zone_state = 'close'
        self.myair_device.setZone(id=self.zone_details['number'], state=_zone_state, set_temp=self.zone_details['setTemp'], value=100)

        # Also, if turning a zone state to another function (heat, cool, vent/fan, dry), set the Homie device node (controls) mode, as that is the overarching ... control
        # call the appropriate set_value method from the mode property of the appropate "controls" node
        if value != 'off':
            self.device.get_node('controls').get_property('mode').set_value(value)

    def set_zone_state_change_ts(self, value):
        if self.debug:
            print('{}: set_zone_state_change_ts() value:{}'.format(self.__class__.__name__, value))
            print(self.name)
           
        # value isn't important, when this function is called the ts value just needs to be updated
        self.get_property('zone-state-change-ts').value = datetime.datetime.now(zoneinfo.ZoneInfo("Australia/Melbourne")).strftime('%Y-%m-%dT%H:%M:%S.%f')


class Device_AdvantageAir(Device_Base):
    myair_device = None
    debug = None

    def __init__(
        self, device_id=None, device_name=None, homie_settings=None, mqtt_settings=None, myair_device=None, debug=False, myair_settings=None
    ):
        assert device_id, 'device id required'
        assert device_name, 'device name required'
        assert myair_device, 'myair_device must be supplied'
        assert myair_settings, 'myair_settings must be supplied'

        super().__init__(device_id, device_name, homie_settings, mqtt_settings)

        self.myair_device = myair_device
        self.debug = debug

        # add in nodes and properties of AdvantageAir
        # we have zones
        # - in each zone, we have a set temperature and a measured temperature
        # we have a mode of operation - cool, heat, fan, dry
        # we have a fan speed - low, medium, high
        # at initialisation - we can get the zones to create the nodes required
        # within each node there will be two temperatures - set and measured

        # Controls
        node = Node_Base(self, 'controls', 'Controls', 'controls')
        self.add_node(node)

        node.add_property(
            Property_Enum(node, id="mode", name="Mode", data_format=','.join(OPERATION_MODES), value=myair_device.mode, set_value=lambda value: self.set_mode(value))
        )

        node.add_property(
            Property_Enum(node, id="fan-speed", name="Fan Speed", data_format=','.join(FAN_SPEEDS), value=myair_device.fanspeed, set_value=lambda value: self.set_fan_speed(value))
        )

        node.add_property(
            Property_Integer(node, id="myzone", name="MyZone", value=myair_device.myzone, data_format='1:{}'.format(myair_settings['max_zones']), set_value=lambda value: self.set_myzone(value))
        )

        node.add_property(
            Property_Button(node, id="requestrefresh", name="Request Refresh", settable=True, set_value=lambda value: self.update())
        )

        # note: value will be set when mode state is first changed after this device starts
        node.add_property(
            Property_DateTime(node, id="mode-state-change-ts", name="Mode State Change Timestamp")
        )

        # Zones
        for zone_id, zone_det in myair_device.zones.items():
            if self.debug:
                print('about to create a node - Node_AdvantageAirZone({}, {}, {})'.format(zone_id, zone_det['name'], 'zone'))
            node = Node_AdvantageAirZone(self, zone_id, zone_det['name'], 'zone', zone_det, self.myair_device, debug=self.debug)

            node.get_property('tempsetpoint').value = zone_det['setTemp']
            node.get_property('tempmeasured').value = zone_det['measuredTemp']
            node.get_property('zone-state').value = zone_det['state']
            # this is a combo of the controls mode and the specific zone
            # i.e. if the zone is open then it will be the controls mode, if it is closed then it will be off
            node.get_property('zone-mode').value = myair_device.mode if zone_det['state'] != "close" else "off"

            self.add_node(node)

        # Status
        node = Node_Base(self, 'status', 'Status', 'status')
        self.add_node(node)

        node.add_property(
            Property_String(node, id='systemstatus', name='System Status', value='on' if myair_device.mode in OPERATION_MODES else 'off')
        )

        node.add_property(
            Property_String(node, id='lastupdate', name='Last Update', value=self.get_status_lastupdate_ts())
        )

        self.start()

    def set_mode(self, value):
        if self.debug:
            print('{}: set_mode() value:{}'.format(self.__class__.__name__, value))
        # no need for this, the underlying base class deals with this
        # self.get_node('controls').get_property('mode').value = value
        self.myair_device.mode = value

        # only update the state change timestamp when the mode is changed (aka set)
        self.set_mode_state_change_ts(True)

    def set_fan_speed(self, value):
        if self.debug:
            print('{}: set_fan_speed() value:{}'.format(self.__class__.__name__, value))
        # no need for this, the underlying base class deals with this
        # self.get_node('controls').get_property('fan_speed').value = value
        self.myair_device.fanspeed = value

    def set_myzone(self, value):
        if self.debug:
            print('{}: set_myzone() value:{}'.format(self.__class__.__name__, value))
        # no need for this, the underlying base class deals with this
        # self.get_node('controls').get_property('fan_speed').value = value
        self.myair_device.myzone = value

    def set_mode_state_change_ts(self, value):
        if self.debug:
            print('{}: set_mode_state_change_ts() value:{}'.format(self.__class__.__name__, value))
        
        self.get_node('controls').get_property('mode-state-change-ts').value = datetime.datetime.now(zoneinfo.ZoneInfo("Australia/Melbourne")).strftime('%Y-%m-%dT%H:%M:%S.%f')

    def get_status_lastupdate_ts(self):
        return datetime.datetime.now(zoneinfo.ZoneInfo("Australia/Melbourne")).strftime("%d/%m/%Y %H:%M:%S%z")

    def update(self):
        if self.debug:
            print('{}: update()'.format(self.__class__.__name__))

        self.myair_device.update()

        # Controls
        # mode will be one of OPERATION_MODES + 'off' - therefore, if it says off it's off otherwise it must be on
        current_homie_mode_state = self.get_node('controls').get_property('mode').value
        if current_homie_mode_state != self.myair_device.mode:
            self.set_mode_state_change_ts(True)
        self.get_node('controls').get_property('mode').value = self.myair_device.mode
        self.get_node('controls').get_property('fan-speed').value = self.myair_device.fanspeed
        self.get_node('controls').get_property('myzone').value = self.myair_device.myzone

        # Zones
        for zone_id, zone_det in self.myair_device.zones.items():
            self.get_node(zone_id).get_property('tempsetpoint').value = zone_det['setTemp']
            self.get_node(zone_id).get_property('tempmeasured').value = zone_det['measuredTemp']
            current_homie_zone_state = self.get_node(zone_id).get_property('zone-state').value
            # this will update the zone state change time, if it in fact has changed
            if current_homie_zone_state != zone_det['state']:
                self.get_node(zone_id).set_zone_state_change_ts(True)
            self.get_node(zone_id).get_property('zone-state').value = zone_det['state']
            self.get_node(zone_id).get_property('zone-mode').value = self.myair_device.mode if zone_det['state'] != "close" else "off"

        # Status
        self.get_node('status').get_property('systemstatus').value = 'on' if self.myair_device.mode in OPERATION_MODES else 'off'
        self.get_node('status').get_property('lastupdate').value = self.get_status_lastupdate_ts()

# vim: expandtab
# END OF FILE
