"""
A ``Device`` is an abstraction of any kind of laborary equipment, or anything
can be treated like an equipment, e.g. a vitual analyzer.

The data of device takes form of parameters, therefore a device can be treated
as a container of parameters. Note that the devices are not only form of
parameter containers.

A device instance can have child devices. For instance, a oscilloscope contains
more than one channels generally, and each channel can abstracted into a child
device of oscilloscope.
"""

from typing import (
    Any,
    Dict,
    Optional,
)
from softlab.tu.helpers import Delegated
from softlab.tu.parameter import Parameter

class Device(Delegated):
    """
    Device base class
    
    A device has a non-empty name, and contains any count of parameters and
    child devices. By inheriting ``Delegated``, any parameter and child device
    can be accessed directly as an attribute of device.
    """

    def __init__(self, name: str) -> None:
        """
        Initialization

        Args:
            name --- device name, non-empty string
        """
        name = str(name)
        if len(name) == 0:
            raise ValueError('Empty device name')
        self._name = name
        self._parameters: Dict[str, Parameter] = {}
        self.add_delegate_attr_dict('_parameters')
        self._devices: Dict[str, Device] = {}
        self.add_delegate_attr_dict('_devices')
        self._parent: Optional[Device] = None

    @property
    def name(self) -> str:
        """Get device name"""
        return self._name
    
    @name.setter
    def name(self, name: str) -> None:
        """Change device name"""
        name = str(name)
        if len(name) == 0:
            raise ValueError('Empty device name')
        self._name = name

    @property
    def parent(self) -> Optional["Device"]:
        """Get parent device"""
        return self._parent
    
    @parent.setter
    def parent(self, parent: Optional["Device"]) -> None:
        """Set parent device, only valid for a different device or None"""
        if parent is None or isinstance(parent, Device):
            if parent == self:
                raise ValueError(f'A device {self} can not be its own parent')
            self._parent = parent
        else:
            raise ValueError(f'Invalid parent device {parent}')

    def __repr__(self) -> str:
        return f'{type(self)}/{self.name}'
    
    def snapshot(self) -> Dict[str, Any]:
        """Get snapshot of device information"""
        return {
            'name': self.name,
            'parameters': dict(map(
                lambda key: (key, self._parameters[key].snapshot()),
                self._parameters,
            )),
            'children': dict(map(
                lambda key: (key, self._devices[key].snapshot()),
                self._devices,
            ))
        }

    def parameter(self, key: str) -> Optional[Parameter]:
        """
        Get parameter with given key

        Args:
            key --- parameter key

        Returns:
            the parameter instance, None if non-exist
        """
        if key in self._parameters:
            return self._parameters[key]
        return None

    def child(self, key: str) -> Optional["Device"]:
        """
        Get child device with given key

        Args:
            key --- child device key

        Returns:
            the device instance, None if non-exist
        """
        if key in self._devices:
            return self._devices[key]
        return None

    def add_parameter(self, para: Parameter, visible: bool = True) -> None:
        """
        Add a parameter into device

        Args:
            para --- parameter instance, its name as its key should not be used
                     in existing parameter dict and child device dict
            visible --- whether the parameter is visible from outside, if not,
                        its key put into omitting attribute names
        """
        if not isinstance(para, Parameter): # check
            raise TypeError(f'Invalid parameter type {type(para)}')
        key = para.name # use parameter name as key
        if key in self._parameters or key in self._devices:
            raise ValueError(f'Parameter with key {key} has exist')
        self._parameters[key] = para # update
        para.owner = self
        if not visible:
            self.add_omit_delegate_attrs(key) # invisible parameter

    def add_child(self, child: "Device", visible: bool = True) -> None:
        """
        Add a child device into device
        
        Args:
            child --- child device instance, its name as its key should not be
                      used in existing parameter dict and child device dict
            visible --- whether the child is visible from outside, if not,
                        its key put into omitting attribute names
        """
        if not isinstance(child, Device): # check
            raise TypeError(f'Invalid child device type {type(child)}')
        key = child.name # use device name as key
        if key in self._devices or key in self._parameters:
            raise ValueError(f'Child device with key {key} has exist')
        self._devices[key] = child # update
        child.parent = self
        if not visible:
            self.add_omit_delegate_attrs(key) # invisible child device

    def rm_parameter(self, key: str) -> Optional[Parameter]:
        """Remove parameter from device and return it (None if non-exist)"""
        para = self._parameters.pop(key, None)
        if isinstance(para, Parameter):
            para.owner = None
        return para

    def rm_child(self, key: str) -> Optional["Device"]:
        """Remove child from device and return it (None if non-exist)"""
        child = self._devices.pop(key, None)
        if isinstance(child, Device):
            child.parent = None
        return child
    
class DeviceBuilder():
    """
    Builder to gerenate specific device.
    
    Different builders differ due to their different models.
    """

    def __init__(self, model: str) -> None:
        """
        Initialization
        
        Args:
            model --- builder model
        """
        model = str(model)
        if len(model) == 0:
            raise ValueError('Empty device builder model')
        self._model = model

    @property
    def model(self) -> str:
        """Get builder model"""
        return self._model

    def __repr__(self) -> str:
        return f'<DeviceBuilder>{self.model}'
    
    def build(self, name: str, **kwargs) -> Device:
        """
        Generate a device, implemented in sub classes

        Args:
            name --- device name
            kwargs --- key specific arguments to create device
        
        Returns:
            a device corresponding to such builder
        """
        raise NotImplementedError
    
_device_builders: Dict[str, DeviceBuilder] = {}
"""Global dictionary of device builders"""

def register_device_builder(builder: DeviceBuilder) -> None:
    """Register device builder"""
    if not isinstance(builder, DeviceBuilder):
        raise TypeError(f'Invalid device builder type {type(builder)}')
    if builder.model in _device_builders:
        raise ValueError(f'Device builder with model {builder.model} has exist')
    _device_builders[builder.model] = builder

def get_device_builder(model: str) -> Optional[DeviceBuilder]:
    """Get device builder with given ``model``, return None if non-exist"""
    return _device_builders.get(model, None)

if __name__ == '__main__':
    import pprint
    from softlab.jin import ValNumber
    dev = Device('demo')
    for para in [
        Parameter('para0', ValNumber(0.0, 10.0), init_value=3.14),
        Parameter('para1', ValNumber(-10.0, 10.0), init_value=3.14),
        Parameter('para2', ValNumber(-5.0, 5.0), init_value=3.14),
    ]:
        dev.add_parameter(para)
    for child in [
        Device('child0'), Device('child1')
    ]:
        dev.add_child(child)
    dev.child0.add_parameter(Parameter('para3', ValNumber(0.0, 1.0)))
    pprint.pprint(dev.snapshot())
    print(f'Parameter values: {dev.para0()}, {dev.para1()}, '
          f'{dev.para2()}, {dev.child0.para3()}')
    dev.para0(7.8)
    dev.para1(-7.8)
    dev.para2(-0.123344)
    dev.child0.para3(0.5)
    print('After setting')
    print(f'Parameter values: {dev.para0()}, {dev.para1()}, '
          f'{dev.para2()}, {dev.child0.para3()}')
    
    class _BuilderDemo(DeviceBuilder):
        def __init__(self) -> None:
            super().__init__('demo')

        def build(self, name: str, **_) -> Device:
            dev = Device(name)
            dev.add_parameter(
                Parameter('percentage', ValNumber(0.0, 100.0), init_value=3.14))
            return dev
        
    builder = _BuilderDemo() # create a demo builder
    print(f'Create demo builder {builder}')
    dev2 = builder.build('built')
    print(f'Use builder to generate a device')
    pprint.pprint(dev2.snapshot())
    print('Register the builder')
    register_device_builder(builder)
    print(f'Get builder with model {builder.model}: '
          f'{get_device_builder(builder.model)}')
    print(f'Get builder with model 123: {get_device_builder("123")}')
