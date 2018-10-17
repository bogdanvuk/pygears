from pygears.conf.registry import PluginBase


def test_subclasses_registry():
    class Plugin1(PluginBase):
        pass

    class Plugin2(PluginBase):
        pass

    assert Plugin1 in PluginBase.subclasses
    assert Plugin2 in PluginBase.subclasses
    assert Plugin1 in Plugin1.subclasses
    assert Plugin2 in Plugin1.subclasses


def test_key_registry():
    class Plugin1(PluginBase):
        @classmethod
        def bind(cls):
            cls.registry['key11'] = {'cfg1': 'val1'}
            cls.registry['key12'] = {'cfg2': 'val2'}

    class Plugin2(PluginBase):
        @classmethod
        def bind(cls):
            cls.registry['key21'] = {'cfg1': 'val1'}
            cls.registry['key22'] = {'cfg2': 'val2'}

    assert PluginBase.registry['key11']['cfg1'] == 'val1'
    assert PluginBase.registry['key12']['cfg2'] == 'val2'

    assert Plugin1.registry['key21']['cfg1'] == 'val1'
    assert Plugin1.registry['key22']['cfg2'] == 'val2'
