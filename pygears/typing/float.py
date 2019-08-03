from pygears.typing.number import NumberType


class FloatType(NumberType):
    @property
    def specified(self):
        return True


class Float(float, metaclass=FloatType):
    pass
