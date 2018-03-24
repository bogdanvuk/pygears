from .util import doublewrap
from .hier_node import NamedHierNode
from .infer_ftypes import infer_ftypes, TypeMatchError
from .intf import Intf
from pygears.registry import registry, PluginBase, bind
from .partial import Definition
import inspect
from functools import wraps


def clear():
    bind('HierRoot', NamedHierNode(''))
    bind('CurrentHier', registry('HierRoot'))


class TooManyArguments(Exception):
    pass


class ModuleTypeNotSpecified(Exception):
    pass


class ModuleArgsNotSpecified(Exception):
    pass


class Port:
    def __init__(self, gear, index, basename, producer=None, consumer=None):
        self.gear = gear
        self.index = index
        self.producer = producer
        self.consumer = consumer
        self.basename = basename

    @property
    def dtype(self):
        if self.producer is not None:
            return self.producer.dtype
        else:
            return self.consumer.dtype


class InPort(Port):
    pass


class OutPort(Port):
    pass


class GearBase(NamedHierNode):
    def __new__(cls, func, meta_kwds, *args, name=None, **kwds):

        if name is None:
            name = func.__name__

        alternatives = meta_kwds.get('alternatives', [])
        # enablement = meta_kwds.pop('enablement', [])

        kwds_comb = meta_kwds.copy()
        kwds_comb.update(kwds)

        errors = []
        try:
            gear = super().__new__(cls)
            gear.__init__(func, *args, name=name, **kwds_comb)
            enablement = gear.params.pop('enablement')

            if not enablement:
                raise TypeMatchError('Enablement condition failed')

            return gear.resolve()
        except TypeMatchError as e:
            gear.remove()
            errors.append(e)
            if not alternatives:
                raise e

        for cls in alternatives:
            try:
                return cls(*args, name=name, **kwds)
            except TypeMatchError as e:
                pass
        else:
            raise errors[0]

    def __init__(self, func, *args, name=None, intfs=[], outnames=[], **kwds):
        super().__init__(name, registry('CurrentHier'))
        self.func = func
        self.outnames = outnames
        self.intfs = intfs.copy()

        self.args = args
        self.resolved = False

        argspec = inspect.getfullargspec(func)
        self.argnames = argspec.args
        self.varargsname = argspec.varargs
        self.annotations = argspec.annotations
        self.kwdnames = argspec.kwonlyargs

        self.params = argspec.kwonlydefaults
        if self.params is None:
            self.params = {}

        # Add defaults from GearMetaParams registry
        for k, v in registry('GearMetaParams').items():
            if k not in self.params:
                self.params[k] = v

        self.params.update(kwds)

        self.dtype_templates = [
            self.annotations[a] if a in self.annotations else f'{{{a}}}'
            for a in self.argnames
        ]

        if (len(self.args) < len(self.argnames)) or (
                not self.varargsname and (len(self.args) > len(args))):
            balance = "few" if (len(self.args) < len(
                self.argnames)) else "many"

            raise TooManyArguments(
                f"Too {balance} arguments for the module {self.name} provided."
            )

        self._handle_return_annot()
        self._expand_varargs()
        self.in_ports = [
            InPort(self, i, name) for i, name in enumerate(self.argnames)
        ]

        for i, a in enumerate(self.args):
            if not self._type_is_specified(a.dtype):
                raise ModuleArgsNotSpecified(
                    f"Input arg {i} for module {self.name} has"
                    f" unresolved type {repr(a)}")

            try:
                a.connect(self.in_ports[i])
            except AttributeError:
                raise ModuleArgsNotSpecified(
                    f"Input arg {i} for module {self.name} was not"
                    f" resolved to interface, instead {repr(a)} received")

        self.infered_dtypes, self.params = self.infer_params_and_ftypes()

    def _handle_return_annot(self):
        if "return" in self.annotations:
            ret_anot = self.annotations["return"]
            if isinstance(ret_anot, dict):
                self.outnames = tuple(ret_anot.keys())
                self.dtype_templates.append(tuple(ret_anot.values()))
            else:
                self.dtype_templates.append(ret_anot)
        else:
            self.dtype_templates.append('{ret}')

    def _expand_varargs(self):
        if self.varargsname:
            vararg_type_list = []
            if self.varargsname in self.annotations:
                vararg_type = self.annotations[self.varargsname]
            else:
                vararg_type = "{{" + self.varargsname + "{0}}}"
            # Append the types of the self.varargsname
            for i, a in enumerate(self.args[len(self.argnames):]):
                if isinstance(vararg_type, str):
                    # If vararg_type is a template string, it can be made
                    # dependent on the arguments position
                    type_tmpl_i = vararg_type.format(i)
                else:
                    # Vararg is not a template and should be passed as is
                    type_tmpl_i = vararg_type

                vararg_type_list.append(type_tmpl_i)
                self.dtype_templates.insert(-1, type_tmpl_i)
                self.argnames.append(f'{self.varargsname}{i}')

            self.params[self.varargsname] = f'[{", ".join(vararg_type_list)}]'

    @property
    def definition(self):
        return self.params['definition']

    def set_ftype(self, ft, i):
        self.dtype_templates[i] = ft

    def _type_is_specified(self, t):
        try:
            return t.is_specified()
        except Exception as e:
            if t is None:
                return True
            else:
                return False

    def is_specified(self):
        for i in self.intfs:
            if not self._type_is_specified(i.dtype):
                return False
        else:
            return True

    def get_arg_types(self):
        return tuple(a.dtype for a in self.args)

    def get_type(self):
        if len(self.intfs) > 1:
            return tuple(i.dtype for i in self.intfs)
        elif len(self.intfs) == 1:
            return self.intfs[0].dtype
        else:
            return None

    def infer_params_and_ftypes(self):
        arg_types = [i.dtype for i in self.args]
        try:
            return infer_ftypes(
                self.dtype_templates, arg_types, params=self.params)
        except TypeMatchError as e:
            raise TypeMatchError(f'{str(e)}, of the module {self.name}')

    def resolve(self):
        func_ret = self.resolve_func()

        if func_ret:
            out_dtype = tuple(r.dtype for r in func_ret)
        elif not isinstance(self.infered_dtypes[-1], tuple):
            out_dtype = (self.infered_dtypes[-1], )
        else:
            out_dtype = self.infered_dtypes[-1]

        if (len(self.outnames) == 0) and (len(out_dtype) == 1):
            self.outnames.append('dout')
        else:
            for i in range(len(self.outnames), len(out_dtype)):
                self.outnames.append(f'dout{i}')

        self.out_ports = [
            OutPort(self, i, name) for i, name in enumerate(self.outnames)
        ]

        for i, r in enumerate(func_ret):
            r.connect(self.out_ports[i])

        if not self.intfs:
            self.intfs = [Intf(dt) for dt in out_dtype]

        assert len(self.intfs) == len(out_dtype)
        for intf, port in zip(self.intfs, self.out_ports):
            intf.source(port)

        if not self.is_specified():
            raise ModuleTypeNotSpecified(
                f"Output type of the module {self.name}"
                f" could not be resolved, and resulted in {repr(out_dtype)}")

        if len(self.intfs) > 1:
            return tuple(self.intfs)
        elif len(self.intfs) == 1:
            return self.intfs[0]
        else:
            return None


class Gear(GearBase):
    def resolve_func(self):
        return tuple()


class Hier(GearBase):
    def resolve_func(self):
        func_args = [Intf(a.dtype) for a in self.args]
        for arg, port in zip(func_args, self.in_ports):
            arg.source(port)

        func_kwds = {
            k: self.params[k]
            for k in self.kwdnames if k in self.params
        }

        bind('CurrentHier', self)
        ret = self.func(*func_args, **func_kwds)
        bind('CurrentHier', self.parent)

        if ret is None:
            ret = tuple()
        elif not isinstance(ret, tuple):
            ret = (ret, )

        return ret


def func_module(cls, func, **meta_kwds):
    @wraps(func)
    def wrapper(*args, **kwds):
        meta_kwds['definition'] = wrapper.definition
        return cls(func, meta_kwds, *args, **kwds)

    return wrapper


@doublewrap
def gear(func, *args, gear_cls=Gear, **kwds):
    return Definition(func_module(gear_cls, func, *args, **kwds))


@doublewrap
def hier(func, *args, **kwds):
    return Definition(func_module(Hier, func, *args, **kwds))


class HierRootPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['HierRoot'] = NamedHierNode('')
        cls.registry['CurrentHier'] = cls.registry['HierRoot']
        cls.registry['GearMetaParams'] = {
            'alternatives': [],
            'enablement': True
        }
