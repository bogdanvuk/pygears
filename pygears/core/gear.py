import copy
import inspect
import functools
import asyncio
import sys

from pygears.registry import PluginBase, bind, registry
from pygears.typing import Any

from .hier_node import NamedHierNode
from .infer_ftypes import TypeMatchError, infer_ftypes, type_is_specified
from .intf import Intf
from .partial import Partial
from .port import InPort, OutPort
from .util import doublewrap

code_map = {}


class TooManyArguments(Exception):
    pass


class GearTypeNotSpecified(Exception):
    pass


class GearArgsNotSpecified(Exception):
    pass


def check_arg_num(argnames, varargsname, args):
    if (len(args) < len(argnames)) or (not varargsname and
                                       (len(args) > len(argnames))):
        balance = "few" if (len(args) < len(argnames)) else "many"

        raise TooManyArguments(f"Too {balance} arguments provided.")


def check_arg_specified(args):
    args_res = []
    const_args_gears = []
    for i, a in enumerate(args):
        if isinstance(a, Partial):
            raise GearArgsNotSpecified(f"Unresolved input arg {i}")

        if not isinstance(a, Intf):
            from pygears.common import const
            try:
                a = const(val=a)
                const_args_gears.append(module().child[-1])
            except GearTypeNotSpecified:
                raise GearArgsNotSpecified(f"Unresolved input arg {i}")

        args_res.append(a)

        if not type_is_specified(a.dtype):
            raise GearArgsNotSpecified(
                f"Input arg {i} has unresolved type {repr(a.dtype)}")

    return tuple(args_res), const_args_gears


class create_hier:
    def __init__(self, gear):
        self.gear = gear

    def __enter__(self):
        bind('CurrentModule', self.gear)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        bind('CurrentModule', self.gear.parent)
        if exception_type is not None:
            self.gear.clear()


class Gear(NamedHierNode):
    def __new__(cls, func, meta_kwds, *args, name=None, __base__=None, **kwds):

        if name is None:
            if __base__ is None:
                name = func.__name__
            else:
                name = __base__.__name__

        kwds_comb = kwds.copy()
        kwds_comb.update(meta_kwds)

        gear = super().__new__(cls)
        try:
            gear.__init__(func, *args, name=name, **kwds_comb)
        except Exception as e:
            gear.remove()
            raise e

        if not gear.params.pop('enablement'):
            gear.remove()
            raise TypeMatchError(
                f'Enablement condition failed for "{gear.name}" alternative'
                f' "{gear.definition.__module__}.{gear.definition.__name__}": '
                f'{meta_kwds["enablement"]}')

        return gear.resolve()

    def __init__(self, func, *args, name=None, intfs=None, outnames=[], **kwds):
        super().__init__(name, registry('CurrentModule'))

        self.in_ports = []
        self.out_ports = []
        self.const_args_gears = []

        self.func = func
        self.__doc__ = func.__doc__

        self.outnames = outnames.copy()
        if intfs is None:
            self.fix_intfs = []
        elif isinstance(intfs, Intf):
            self.fix_intfs = [intfs]
        else:
            self.fix_intfs = intfs.copy()

        self.args = args
        self.resolved = False

        argspec = inspect.getfullargspec(func)
        self.argnames = argspec.args
        self.varargsname = argspec.varargs
        self.annotations = argspec.annotations
        self.kwdnames = argspec.kwonlyargs

        try:
            check_arg_num(self.argnames, self.varargsname, self.args)
        except TooManyArguments as e:
            TooManyArguments(f'{e}, for the module {self.name}')

        try:
            self.args, self.const_args_gears = check_arg_specified(self.args)
        except GearArgsNotSpecified as e:
            raise GearArgsNotSpecified(
                f'{str(e)}, when instantiating {self.name}')

        self.params = {}
        if isinstance(argspec.kwonlydefaults, dict):
            self.params.update(argspec.kwonlydefaults)

        self.params.update(kwds)

        self.params.update({
            a: (self.annotations[a] if a in self.annotations else Any)
            for a in self.argnames
        })

        self._handle_return_annot()
        self._expand_varargs()
        self.in_ports = [
            InPort(self, i, name) for i, name in enumerate(self.argnames)
        ]

        for i, a in enumerate(self.args):
            try:
                a.connect(self.in_ports[i])
            except AttributeError:
                raise GearArgsNotSpecified(
                    f"Input arg {i} for module {self.name} was not"
                    f" resolved to interface, instead {repr(a)} received")

        self.infer_params()

    def _handle_return_annot(self):
        if "return" in self.annotations:
            ret_anot = self.annotations["return"]
            if isinstance(ret_anot, dict):
                self.outnames = tuple(ret_anot.keys())
                self.params['return'] = tuple(ret_anot.values())
            else:
                self.params['return'] = ret_anot
        else:
            self.params['return'] = None

    def _expand_varargs(self):
        if self.varargsname:
            vararg_type_list = []
            if self.varargsname in self.annotations:
                vararg_type = self.annotations[self.varargsname]
            else:
                vararg_type = Any
            # Append the types of the self.varargsname
            for i, a in enumerate(self.args[len(self.argnames):]):
                if isinstance(vararg_type, str):
                    # If vararg_type is a template string, it can be made
                    # dependent on the arguments position
                    type_tmpl_i = vararg_type.format(i).encode()
                else:
                    # Vararg is not a template and should be passed as is
                    type_tmpl_i = vararg_type

                argname = f'{self.varargsname}{i}'

                vararg_type_list.append(argname)
                self.params[argname] = type_tmpl_i
                self.argnames.append(argname)

            self.params[
                self.
                varargsname] = f'({", ".join(vararg_type_list)}, )'.encode()

    def remove(self):
        for p in self.in_ports:
            if p.producer is not None:
                try:
                    p.producer.disconnect(p)
                except ValueError:
                    pass

        for p in self.out_ports:
            if p.producer is not None:
                p.producer.disconnect(p)

        for g in self.const_args_gears:
            g.remove()

        try:
            super().remove()
        except ValueError:
            pass

    @property
    def definition(self):
        return self.params['definition']

    @property
    def dout(self):
        if len(self.intfs) > 1:
            return tuple(p.producer for p in self.out_ports)
        else:
            return self.out_ports[0].producer

    @property
    def tout(self):
        if len(self.intfs) > 1:
            return tuple(i.dtype for i in self.intfs)
        else:
            return self.intfs[0].dtype

    def set_ftype(self, ft, i):
        self.dtype_templates[i] = ft

    def is_specified(self):
        for i in self.intfs:
            if not type_is_specified(i.dtype):
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

    def infer_params(self):
        arg_types = {
            name: arg.dtype
            for name, arg in zip(self.argnames, self.args)
        }

        try:
            self.params = infer_ftypes(
                self.params,
                arg_types,
                namespace=self.func.__globals__,
                allow_incomplete=False)
        except TypeMatchError as e:
            raise TypeMatchError(f'{str(e)}, of the module "{self.name}"')

    def resolve(self):
        for port in self.in_ports:
            Intf(port.dtype).source(port)

        is_async_gen = bool(
            self.func.__code__.co_flags & inspect.CO_ASYNC_GENERATOR)
        func_ret = tuple()
        if (not inspect.iscoroutinefunction(self.func)
                and not inspect.isgeneratorfunction(self.func)
                and not is_async_gen):
            func_ret = self.resolve_func()

        out_dtype = tuple()
        if func_ret:
            out_dtype = tuple(r.dtype for r in func_ret)
        elif self.params['return'] is not None:
            if not isinstance(self.params['return'], tuple):
                out_dtype = (self.params['return'], )
            else:
                out_dtype = self.params['return']

        if (len(self.outnames) == 0) and (len(out_dtype) == 1):
            self.outnames.append('dout')
        else:
            for i in range(len(self.outnames), len(out_dtype)):
                self.outnames.append(f'dout{i}')

        self.out_ports = [
            OutPort(self, i, name) for i, name in enumerate(self.outnames)
        ]

        # Connect internal interfaces
        if func_ret:
            for i, r in enumerate(func_ret):
                r.connect(self.out_ports[i])
        else:
            for dtype, port in zip(out_dtype, self.out_ports):
                Intf(dtype).connect(port)

        # Connect output interfaces
        self.intfs = []
        out_intfs = []
        if isinstance(self.fix_intfs, dict):
            for i, (name, dt) in enumerate(zip(self.outnames, out_dtype)):
                if name in self.fix_intfs:
                    intf = self.fix_intfs[name]
                else:
                    intf = Intf(dt)
                    out_intfs.append(intf)

                self.intfs.append(intf)

        elif self.fix_intfs:
            self.intfs = self.fix_intfs
        else:
            self.intfs = [Intf(dt) for dt in out_dtype]
            out_intfs = self.intfs

        assert len(self.intfs) == len(out_dtype)
        for intf, port in zip(self.intfs, self.out_ports):
            intf.source(port)

        for name, dtype in zip(self.outnames, out_dtype):
            self.params[name] = dtype

        if not self.is_specified():
            raise GearTypeNotSpecified(
                f"Output type of the module {self.name}"
                f" could not be resolved, and resulted in {repr(out_dtype)}")

        for c in self.child:
            for p in c.out_ports:
                intf = p.consumer
                if intf not in self.intfs and not intf.consumers:
                    print(f'Warning: {c.name}.{p.basename} left dangling.')

        if len(out_intfs) > 1:
            return tuple(out_intfs)
        elif len(out_intfs) == 1:
            return out_intfs[0]
        else:
            return None

    def resolve_func(self):
        with create_hier(self):
            func_args = [p.consumer for p in self.in_ports]

            func_kwds = {
                k: self.params[k]
                for k in self.kwdnames if k in self.params
            }

            self.func_locals = {}
            code_map = registry('GearCodeMap')
            code_map[self.func.__code__] = self

            def tracer(frame, event, arg):
                if event == 'return':
                    if frame.f_code in code_map:
                        code_map[
                            frame.f_code].func_locals = frame.f_locals.copy()

            # tracer is activated on next call, return or exception
            if registry('CurrentModule').parent == registry('HierRoot'):
                sys.setprofile(tracer)

            ret = self.func(*func_args, **func_kwds)

            if registry('CurrentModule').parent == registry('HierRoot'):
                sys.setprofile(None)

            for name, val in self.func_locals.items():
                if isinstance(val, Intf):
                    val.var_name = name

        # if not any([isinstance(c, Gear) for c in self.child]):
        #     self.clear()

        if ret is None:
            ret = tuple()
        elif not isinstance(ret, tuple):
            ret = (ret, )

        return ret


def alternative(*base_gear_defs):
    def gear_decorator(gear_def):
        for d in base_gear_defs:
            alternatives = getattr(d.func, 'alternatives', [])
            alternatives.append(gear_def.func)
            d.func.alternatives = alternatives
        return gear_def

    return gear_decorator


@doublewrap
def gear(func, gear_cls=Gear, **meta_kwds):
    from pygears.core.funcutils import FunctionBuilder
    fb = FunctionBuilder.from_func(func)

    # Add defaults from GearExtraParams registry
    for k, v in registry('GearExtraParams').items():
        if k not in fb.kwonlyargs:
            fb.kwonlyargs.append(k)
            fb.kwonlydefaults[k] = copy.copy(v)

    fb.body = (f"return gear_cls(gear_func, meta_kwds, "
               f"{fb.get_invocation_str()})")

    # Add defaults from GearMetaParams registry
    for k, v in registry('GearMetaParams').items():
        if k not in meta_kwds:
            meta_kwds[k] = copy.copy(v)

    execdict = {
        'gear_cls': gear_cls,
        'meta_kwds': meta_kwds,
        'gear_func': func
    }
    execdict.update(func.__globals__)
    execdict_keys = list(execdict.keys())
    execdict_values = list(execdict.values())

    def formatannotation(annotation, base_module=None):
        try:
            return execdict_keys[execdict_values.index(annotation)]
        except ValueError:
            if not isinstance(str, bytes):
                return '"b' + repr(annotation) + '"'
            else:
                return annotation

    gear_func = fb.get_func(
        execdict=execdict, formatannotation=formatannotation)

    functools.update_wrapper(gear_func, func)

    p = Partial(gear_func)
    meta_kwds['definition'] = p
    p.meta_kwds = meta_kwds

    return p


def module():
    return registry('CurrentModule')


class GearPlugin(PluginBase):
    @classmethod
    def bind(cls):
        cls.registry['HierRoot'] = NamedHierNode('')
        cls.registry['CurrentModule'] = cls.registry['HierRoot']
        cls.registry['GearCodeMap'] = {}
        cls.registry['GearMetaParams'] = {'enablement': True}
        cls.registry['GearExtraParams'] = {
            'name': None,
            'intfs': [],
            'outnames': [],
            '__base__': None
        }

    @classmethod
    def reset(cls):
        bind('HierRoot', NamedHierNode(''))
        bind('CurrentModule', cls.registry['HierRoot'])
        bind('GearCodeMap', {})
