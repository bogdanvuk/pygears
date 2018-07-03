# from pygears.typing.base import TypingMeta, type_repr
# from pygears.typing.uint import Int, Uint

# from .module_def import ModuleDefinition
# from pygears.core.module import Module
# from pygears.di.di import RequiredFeature

# from pygears.typing.match import type_match
# from pygears.typing.base import param_subs

# class SieveError(Exception):
#     pass
from pygears.core.intf import IntfOperPlugin


class PipeIntfOperPlugin(IntfOperPlugin):
    @classmethod
    def bind(cls):
        cls.registry['IntfOperNamespace']['__or__'] = pipe


def pipe(self, other):
    print("Here")
    return self
    # if isinstance(other, (str, TypingMeta)):
    #     return Conv(self, other, name=f'conv_{self.basename}').resolve()
    # else:
    #     return other.__ror__(self)


# def __getitem__(self, index):
#     if isinstance(index, slice):
#         start = index.start
#         if start is None:
#             start = 0

#         end = index.stop
#         if end is None:
#             end = len(self.get_type())

#         name = f'{self.proc.basename}_{start}v{end}'
#     else:
#         start = index
#         if isinstance(index, str):
#             if index not in self.get_type().fields:
#                 raise SieveError(
#                     f'No field named "{index}" in interface of type'
#                     f' {type_repr(self.get_type())}')
#             index = self.get_type().fields.index(index)

#         if index < 0:
#             start = len(self.get_type()) + index + 1
#         name = f'{self.proc.basename}_{start}'

#     return Sieve(self, index, name=name).resolve()

# def __hash__(self):
#     return id(self)

# def __eq__(self, other):
#     return ModuleDefinition(Eq, eq)(self, other)

# def __add__(self, other):
#     return ModuleDefinition(Add, add)(self, other)

# def __mul__(self, other):
#     return ModuleDefinition(Mul, mul)(self, other)

# def __truediv__(self, other):
#     return ModuleDefinition(Div, div)(self, other)

# def __sub__(self, other):
#     return ModuleDefinition(Sub, sub)(self, other)

# def __neg__(self):
#     return Neg(self, name=f'neg_{self.basename}').resolve()

# def __or__(self, other):
#     if isinstance(other, (str, TypingMeta)):
#         return Conv(self, other, name=f'conv_{self.basename}').resolve()
#     else:
#         return other.__ror__(self)

# class Sieve(Module):
#     def __init__(self, din, index, **kwds):
#         self._index = index

#         def sieve(din: '{T}') -> '{T}' + '[{}]'.format(repr(index)):
#             pass

#         super().__init__(sieve, din, **kwds)

#         # self.__call__(din, name=f'{din.basename}_{index}')

# class Oper(Module):
#     def __init__(self, func, din0, din1, **kwds):
#         from pygears.common import const
#         from pygears.util.bitw import bitw

#         if isinstance(din0, int):
#             din0 = const(tout=Uint[bitw(din0)], val=din0)

#         if isinstance(din1, int):
#             din1 = const(tout=Uint[bitw(din1)], val=din1)

#         self._din0 = din0
#         self._din1 = din1

#         # super().__init__(func, din0, din1, **kwds)

#         super().__init__(
#             func,
#             din0,
#             din1,
#             name=f'{func.__name__}_{din0.proc.basename}_{din1.proc.basename}',
#             **kwds)

#     def resolve_types(self):
#         for i, a in enumerate(self.args):
#             if not isinstance(a, Intf):
#                 print("Here")
#                 a = a().resolve()
#             self.params[f'DIN{i}_SIGNED'] = issubclass(a.type, Int)

#         return super().resolve_types()

# def eq(din0: '{TDIN0}', din1: '{TDIN1}') -> Uint[1]:
#     pass

# class Eq(Oper):
#     pass

# def add(din0: '{TDIN0}', din1: '{TDIN1}') -> '{TDIN0}+{TDIN1}':
#     pass

# class Add(Oper):
#     pass

# def sub(din0: '{TDIN0}', din1: '{TDIN1}') -> '{TDIN0}+{TDIN1}':
#     pass

# class Sub(Oper):
#     pass

# def mul(din0: '{TDIN0}', din1: '{TDIN1}') -> '{TDIN0}*{TDIN1}':
#     pass

# class Mul(Oper):
#     pass

# def div(din0: '{TDIN0}', din1: '{TDIN1}') -> '{TDIN0}/{TDIN1}':
#     pass

# class Div(Oper):
#     pass

# # class Mul(Oper):
# #     def __init__(self, din0, din1, **kwds):

# #         super().__init__(din0, din1, mul, **kwds)

# # class Div(Oper):
# #     def __init__(self, din0, din1):
# #         def div(din0: '{TDIN0}', din1: '{TDIN1}') -> '{TDIN0}*{TDIN1}':
# #             pass

# #         super().__init__(din0, din1, div)

# class Neg(Module):
#     def __init__(self, din, **kwds):
#         def neg(din: '{TDIN}') -> '{TDIN}':
#             pass

#         super().__init__(neg, din, **kwds)

# class Conv(Module):
#     def __init__(self, din, cast_type, **kwds):
#         def conv(din: '{T}') -> cast_type:
#             pass

#         super().__init__(conv, din, **kwds)

#     def resolve_types(self):
#         # print(self.args[0].get_type())
#         # print(self.name)
#         # print(self.ftypes)
#         din_type = self.args[0].get_type()
#         # self.ftypes[-1] = self.get_type()

#         if issubclass(self.get_type(),
#                       Int) and (not self.get_type().is_specified()):
#             if issubclass(din_type, Uint):
#                 self.ftypes[-1] = Int[int(din_type) + 1]
#             elif issubclass(din_type, Int):
#                 self.ftypes[-1] = din_type

#         super().resolve_types()

#         if not self.get_type().is_specified():
#             self.params.update(
#                 type_match(din_type, self.get_type(), self.params))
# self.ftypes[-1] = param_subs(self.ftypes[-1], self.params, {})
