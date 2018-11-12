import copy
import inspect
import sys
import functools

from pygears.conf import PluginBase, bind, registry, core_log, safe_bind
from pygears.typing import Any

from .intf import Intf
from .partial import Partial
from .infer_ftypes import TypeMatchError, infer_ftypes, type_is_specified
from .port import InPort, OutPort
from .hier_node import NamedHierNode
from .util import doublewrap


class TooManyArguments(Exception):
    pass


class GearTypeNotSpecified(Exception):
    pass


class GearArgsNotSpecified(Exception):
    pass


def get_obj_var_name(frame, obj):
    for var_name, var_obj in frame.f_locals.items():
        if obj is var_obj:
            return var_name
    else:
        None


def find_current_gear_frame():
    import inspect
    code_map = registry('gear/code_map')
    if not code_map:
        return None

    for frame, *_ in inspect.stack():
        if frame.f_code is code_map[-1].func.__code__:
            return frame
    else:
        return None


def check_args_num(argnames, varargsname, args):
    if (len(args) < len(argnames)) or (not varargsname and
                                       (len(args) > len(argnames))):
        balance = "few" if (len(args) < len(argnames)) else "many"

        raise TooManyArguments(f"Too {balance} arguments provided.")


def check_args_specified(args):
    for name, intf in args.items():
        if not isinstance(intf, Intf):
            raise GearArgsNotSpecified(
                f"Unresolved input argument {name}: {repr(intf)}")

        if not type_is_specified(intf.dtype):
            raise GearArgsNotSpecified(
                f"Input argument {name} has unresolved type {repr(intf.dtype)}"
            )


def resolve_gear_name(func, __base__):
    if __base__ is None:
        name = func.__name__
    else:
        name = __base__.__name__

    return name


def infer_const_args(args):
    args_res = {}
    const_args = {}
    for name, intf in args.items():
        if not isinstance(intf, Intf):
            from pygears.common.const import get_literal_type
            try:
                const_args[name] = intf
                intf = Intf(get_literal_type(intf))
            except GearTypeNotSpecified:
                raise GearArgsNotSpecified(f"Unresolved input argument {name}")

        args_res[name] = intf

    return args_res, const_args


def expand_varargs(args, annotations, varargsname, varargs):
    vararg_type_list = []
    if varargsname in annotations:
        vararg_type = annotations[varargsname]
    else:
        vararg_type = Any

    # Append the types of the varargsname
    for i, a in enumerate(varargs):
        if isinstance(vararg_type, str):
            # If vararg_type is a template string, it can be made
            # dependent on the arguments position
            type_tmpl_i = vararg_type.format(i).encode()
        else:
            # Vararg is not a template and should be passed as is
            type_tmpl_i = vararg_type

        argname = f'{varargsname}{i}'

        vararg_type_list.append(argname)
        annotations[argname] = type_tmpl_i
        args[argname] = a

    annotations[varargsname] = f'({", ".join(vararg_type_list)}, )'.encode()


def resolve_return_annotation(annotations):
    outnames = None
    if "return" in annotations:
        ret_anot = annotations["return"]
        if isinstance(ret_anot, dict):
            outnames = tuple(ret_anot.keys())
            annotations['return'] = tuple(ret_anot.values())
    else:
        annotations['return'] = None

    return outnames


def resolve_args(args, argnames, annotations, varargs):
    check_args_num(argnames, varargs, args)
    args_dict = {name: a for name, a in zip(argnames, args)}

    if varargs:
        expand_varargs(args_dict, annotations, varargs, args[len(args_dict):])

    args_dict, const_args = infer_const_args(args_dict)
    check_args_specified(args_dict)

    outnames = resolve_return_annotation(annotations)

    for a in args_dict:
        if a not in annotations:
            annotations[a] = Any

    return args_dict, annotations, const_args, outnames


def infer_params(args, params, context):
    arg_types = {name: arg.dtype for name, arg in args.items()}

    return infer_ftypes(
        params, arg_types, namespace=context, allow_incomplete=False)


class Gear(NamedHierNode):
    def __init__(self, func, args, params):
        super().__init__(params['name'], registry('gear/current_module'))
        self.args = args
        self.params = params
        self.func = func

        self.in_ports = []
        for i, (name, intf) in enumerate(args.items()):
            port = InPort(self, i, name)
            intf.connect(port)
            Intf(port.dtype).source(port)
            self.in_ports.append(port)

    def connect_output(self, out_intfs, out_dtypes):

        dflt_dout_name = registry('gear/naming/default_out_name')
        for i in range(len(self.outnames), len(out_dtypes)):
            if out_intfs and hasattr(out_intfs[i], 'var_name'):
                self.outnames.append(out_intfs[i].var_name)
            else:
                self.outnames.append(
                    dflt_dout_name
                    if len(out_dtypes) == 1 else f'{dflt_dout_name}{i}')

        self.out_ports = [
            OutPort(self, i, name) for i, name in enumerate(self.outnames)
        ]

        # Connect internal interfaces
        if out_intfs:
            for i, r in enumerate(out_intfs):
                r.connect(self.out_ports[i])
        else:
            for dtype, port in zip(out_dtypes, self.out_ports):
                Intf(dtype).connect(port)

        for name, dtype in zip(self.outnames, out_dtypes):
            self.params[name] = dtype

    @property
    def hierarchical(self):
        is_async_gen = bool(
            self.func.__code__.co_flags & inspect.CO_ASYNC_GENERATOR)
        return not (inspect.iscoroutinefunction(self.func)
                    or inspect.isgeneratorfunction(self.func) or is_async_gen)

    @property
    def definition(self):
        return self.params['definition']

    @property
    def outnames(self):
        return self.params['outnames']

    @property
    def tout(self):
        if len(self.out_ports) > 1:
            return tuple(i.dtype for i in self.out_ports)
        else:
            return self.out_ports[0].dtype

    @property
    def dout(self):
        ret = self.out_port_intfs
        if len(ret) == 1:
            return ret[0]

    @property
    def in_port_intfs(self):
        return tuple(p.consumer for p in self.in_ports)

    @property
    def out_port_intfs(self):
        return tuple(p.producer for p in self.out_ports)

    @property
    def inputs(self):
        return tuple(p.producer for p in self.in_ports)

    @property
    def outputs(self):
        return tuple(p.consumer for p in self.out_ports)

    @property
    def explicit_params(self):
        paramspec = inspect.getfullargspec(self.func)
        explicit_param_names = paramspec.kwonlyargs or []

        return {
            name: self.params[name]
            for name in explicit_param_names if name in self.params
        }

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

        try:
            super().remove()
        except ValueError:
            pass


class create_hier:
    def __init__(self, gear):
        self.gear = gear

    def __enter__(self):
        bind('gear/current_module', self.gear)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        bind('gear/current_module', self.gear.parent)
        if exception_type is not None:
            self.gear.clear()


class intf_name_tracer:
    def __init__(self, gear):
        self.func_locals = {}
        self.code_map = registry('gear/code_map')
        self.gear = gear

    def tracer(self, frame, event, arg):
        if event == 'return':
            for cm in self.code_map:
                if frame.f_code is cm.func.__code__:
                    cm.func_locals = frame.f_locals.copy()

    def __enter__(self):
        self.code_map.append(self.gear)

        # tracer is activated on next call, return or exception
        if registry('gear/current_module').parent == registry(
                'gear/hier_root'):
            sys.setprofile(self.tracer)

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if registry('gear/current_module').parent == registry(
                'gear/hier_root'):
            sys.setprofile(None)

        self.code_map.pop()

        if exception_type is not None:
            for name, val in self.func_locals.items():
                if isinstance(val, Intf):
                    val.var_name = name


def resolve_func(gear_inst):
    if not gear_inst.hierarchical:
        return tuple()

    with create_hier(gear_inst):
        with intf_name_tracer(gear_inst):
            out_intfs = gear_inst.func(*gear_inst.in_port_intfs,
                                       **gear_inst.explicit_params)

    if out_intfs is None:
        out_intfs = tuple()
    elif not isinstance(out_intfs, tuple):
        out_intfs = (out_intfs, )

    return out_intfs


def resolve_out_types(out_intfs, gear_inst):

    if out_intfs:
        out_dtype = tuple(intf.dtype for intf in out_intfs)
    elif gear_inst.params['return'] is not None:
        if not isinstance(gear_inst.params['return'], tuple):
            out_dtype = (gear_inst.params['return'], )
        else:
            out_dtype = gear_inst.params['return']
    else:
        out_dtype = tuple()

    return out_dtype


def resolve_gear(gear_inst, fix_intfs):
    out_intfs = resolve_func(gear_inst)
    out_dtype = resolve_out_types(out_intfs, gear_inst)

    dflt_dout_name = registry('gear/naming/default_out_name')
    for i in range(len(gear_inst.outnames), len(out_dtype)):
        if out_intfs and hasattr(out_intfs[i], 'var_name'):
            gear_inst.outnames.append(out_intfs[i].var_name)
        else:
            gear_inst.outnames.append(
                dflt_dout_name
                if len(out_dtype) == 1 else f'{dflt_dout_name}{i}')

    gear_inst.connect_output(out_intfs, out_dtype)

    # Connect output interfaces
    out_intfs = []
    out_intfs = []
    if isinstance(fix_intfs, dict):
        for i, (name, dt) in enumerate(zip(gear_inst.outnames, out_dtype)):
            if name in fix_intfs:
                intf = fix_intfs[name]
            else:
                intf = Intf(dt)
                out_intfs.append(intf)

            out_intfs.append(intf)

    elif fix_intfs:
        out_intfs = fix_intfs
    else:
        out_intfs = [Intf(dt) for dt in out_dtype]
        out_intfs = out_intfs

    assert len(out_intfs) == len(gear_inst.out_port_intfs)
    for intf, port in zip(out_intfs, gear_inst.out_ports):
        intf.source(port)

    if any(not type_is_specified(i.dtype) for i in out_intfs):
        raise GearTypeNotSpecified(
            f"Output type of the module {gear_inst.name}"
            f" could not be resolved, and resulted in {repr(out_dtype)}")

    for c in gear_inst.child:
        for p in c.out_ports:
            intf = p.consumer
            if intf not in out_intfs and not intf.consumers:
                core_log().warning(f'{c.name}.{p.basename} left dangling.')

    if len(out_intfs) > 1:
        return tuple(out_intfs)
    elif len(out_intfs) == 1:
        return out_intfs[0]
    else:
        return None


def gear_base_resolver(func,
                       meta_kwds,
                       *args,
                       name=None,
                       intfs=None,
                       __base__=None,
                       outnames=None,
                       **kwds):
    name = name or resolve_gear_name(func, __base__)

    paramspec = inspect.getfullargspec(func)

    try:
        args, annotations, const_args, ret_outnames = resolve_args(
            args, paramspec.args, paramspec.annotations, paramspec.varargs)
    except (TooManyArguments, GearArgsNotSpecified) as e:
        raise type(e)(f'{str(e)}, when instantiating {name}')

    if intfs is None:
        fix_intfs = []
    elif isinstance(intfs, Intf):
        fix_intfs = [intfs]
    else:
        fix_intfs = intfs.copy()

    kwddefaults = paramspec.kwonlydefaults or {}
    param_templates = {
        **dict(
            outnames=outnames or ret_outnames or [],
            name=name,
            intfs=fix_intfs),
        **kwddefaults,
        **kwds,
        **meta_kwds,
        **annotations
    }

    try:
        params = infer_params(args, param_templates, context=func.__globals__)
    except TypeMatchError as e:
        raise TypeMatchError(f'{str(e)}, of the module "{name}"')

    if not params.pop('enablement'):
        raise TypeMatchError(
            f'Enablement condition failed for "{name}" alternative'
            f' "{meta_kwds["definition"].__module__}.'
            f'{meta_kwds["definition"].__name__}": '
            f'{meta_kwds["enablement"]}')

    gear_inst = Gear(func, args, params)

    out_intfs = resolve_gear(gear_inst, fix_intfs)

    for name, val in const_args.items():
        from pygears.common import const
        const(val=val, intfs=[args[name]])

    return out_intfs


def alternative(*base_gear_defs):
    def gear_decorator(gear_def):
        for d in base_gear_defs:
            alternatives = getattr(d.func, 'alternatives', [])
            alternatives.append(gear_def.func)
            d.func.alternatives = alternatives
        return gear_def

    return gear_decorator


@doublewrap
def gear(func, gear_resolver=gear_base_resolver, **meta_kwds):
    from pygears.core.funcutils import FunctionBuilder
    fb = FunctionBuilder.from_func(func)
    fb.filename = '<string>'

    # Add defaults from GearExtraParams registry
    for k, v in registry('gear/params/extra').items():
        if k not in fb.kwonlyargs:
            fb.kwonlyargs.append(k)
            fb.kwonlydefaults[k] = copy.copy(v)

    fb.body = (f"return gear_resolver(gear_func, meta_kwds, "
               f"{fb.get_invocation_str()})")

    # Add defaults from GearMetaParams registry
    for k, v in registry('gear/params/meta').items():
        if k not in meta_kwds:
            meta_kwds[k] = copy.copy(v)

    execdict = {
        'gear_resolver': gear_resolver,
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
    return registry('gear/current_module')


class GearPlugin(PluginBase):
    @classmethod
    def bind(cls):
        safe_bind('gear/naming', {'default_out_name': 'dout'})
        safe_bind('gear/hier_root', NamedHierNode(''))
        safe_bind('gear/current_module', cls.registry['gear']['hier_root'])
        safe_bind('gear/code_map', [])
        safe_bind('gear/params/meta', {'enablement': True})
        safe_bind('gear/params/extra', {
            'name': None,
            'intfs': [],
            'outnames': None,
            '__base__': None
        })

    @classmethod
    def reset(cls):
        safe_bind('gear/hier_root', NamedHierNode(''))
        safe_bind('gear/current_module', cls.registry['gear']['hier_root'])
        safe_bind('gear/code_map', [])
