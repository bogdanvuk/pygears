from pygears.typing.base import GenericMeta


class FloatType(GenericMeta):
    @property
    def specified(self):
        return True


class Float(float, metaclass=FloatType):
    pass
