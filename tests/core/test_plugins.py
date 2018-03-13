from pygears.core import PluginBase


def test_subclasses_registry():
    class Plugin1(PluginBase):
        pass

    class Plugin2(PluginBase):
        pass

    assert PluginBase.subclasses == [Plugin1, Plugin2]
    assert Plugin1.subclasses == [Plugin1, Plugin2]


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
