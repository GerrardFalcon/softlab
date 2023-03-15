"""Define ``Station`` class and its corresponding functions"""

from typing import(
    Any,
    Dict,
    Sequence,
    Optional,
)
from datetime import datetime
from softlab.tu.device import (
    Device,
    DeviceBuilder,
    get_device_builder,
)
from softlab.tu.helpers import Delegated

class Station(Delegated):
    """
    Station is an ensemble of devices to perform experiment
    
    Properties:
        name --- station name, given at initialization
        created_at --- datetime when station is created
        devices --- sequence of containing device names

    Public methods:
        add_device --- add a device into station
        rm_device --- remove a device from station
        device --- access a device from station
        build_device --- build a device by using device builder
        snapshot --- return snapshot of station information
    """

    def __init__(self, name: str) -> None:
        """Initialization, ``name`` must be non-empty string"""
        name = str(name)
        if len(name) == 0:
            raise ValueError('Empty station name')
        self._name = name
        self._devices: Dict[str, Device] = {}
        self.add_delegate_attr_dict('_devices')
        self._created_at: datetime = datetime.now()

    @property
    def name(self) -> str:
        """Get name of station"""
        return self._name
    
    @property
    def created_at(self) -> datetime:
        """Get created timestamp"""
        return self._created_at

    @property
    def devices(self) -> Sequence[str]:
        """Get sequence of device names"""
        return self._devices.keys()
    
    def __repr__(self) -> str:
        return f'{type(self)}/{self.name}'
    
    def snapshot(self) -> Dict[str, Any]:
        """Get snapshot of station information"""
        return {
            'name': self.name,
            'created_at': self._created_at.strftime('%Y-%m-%dT%H:%M:%S'),
            'devices': dict(map(
                lambda key: (key, self._devices[key].snapshot()),
                self._devices,
            ))
        }
    
    def add_device(self, device: Device) -> None:
        """Add ``device`` into station"""
        if not isinstance(device, Device):
            raise TypeError(f'Invalid device type {type(device)}')
        if device.name in self._devices:
            raise ValueError(f'Device with name {device.name} has exist')
        self._devices[device.name] = device

    def rm_device(self, device_name: str) -> Optional[Device]:
        """Remove a device with name ``device_name`` from station"""
        return self._devices.pop(str(device_name), None)
    
    def device(self, device_name: str) -> Optional[Device]:
        """Access device with name ``device_name``"""
        return self._devices.get(str(device_name), None)
    
    def build_device(self, model: str, name: str, **kwargs: Any) -> None:
        """Build a device and add into station

        Args:
            model --- builder model
            name --- device name
            kwargs --- arguments to build device
        """
        builder = get_device_builder(model) # get builder
        if not isinstance(builder, DeviceBuilder):
            raise RuntimeError(f'Failed to get builder with model {model}')
        self.add_device(builder.build(name, **kwargs))

_default_station: Station = Station('default')
"""Default station"""

def default_station() -> Station:
    """Get default station"""
    return _default_station

def set_default_station(station: Station) -> None:
    """Set default station"""
    global _default_station
    if not isinstance(station, Station):
        raise TypeError(f'Invalid station type {type(station)}')
    _default_station = station

if __name__ == '__main__':
    from pprint import pprint
    from softlab.tu.parameter import Parameter
    from softlab.tu.device import register_device_builder
    from softlab.jin import ValNumber
    station = default_station()
    print(f'Get default station {station}')
    for i in range(3):
        station.add_device(Device(f'device{i}'))
    station.device('device1').add_parameter(
        Parameter('para', ValNumber(0.0, 1.0), init_value=0.1))
    pprint(station.snapshot())
    print(f'Initial para: {station.device1.para()}')
    station.device1.para(0.5)
    print(f'After setting: {station.device1.para()}')

    set_default_station(Station('demo'))
    print(f'Change default station {default_station()}')
    station = default_station()
    
    class _BuilderDemo(DeviceBuilder):
        def __init__(self) -> None:
            super().__init__('demo')

        def build(self, name: str, **_) -> Device:
            dev = Device(name)
            dev.add_parameter(
                Parameter('percentage', ValNumber(0.0, 100.0), init_value=3.14))
            return dev
    register_device_builder(_BuilderDemo())

    station.build_device('demo', 'demo_device')
    pprint(station.snapshot())
