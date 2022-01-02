import inspect
import fnmatch
import sys
from copy import copy

from pygears.core.graph import get_producer_port
from pygears.conf import MultiAlternativeError, core_log, reg
from pygears.typing import Any, cast, get_match_conds
from pygears.core.util import is_standard_func, get_function_context_dict

from .partial import Partial
from .intf import Intf
from .infer_ftypes import TypeMatchError, infer_ftypes, type_is_specified
from .gear import TooManyArguments, GearTypeNotSpecified, GearArgsNotSpecified
from .gear import Gear, create_hier
from .gear_decorator import GearDecoratorPlugin
from .gear_memoize import get_memoized_gear, memoize_gear
from .port import HDLConsumer, HDLProducer
from .channel import channel_interfaces


def check(pattern, node):
    if isinstance(pattern, str):
        return fnmatch.fnmatch(node.name, pattern)
    else:
        return pattern(node)

def is_traced(node):
    return any(check(p, node) for p in reg['debug/trace'])

    # cfg = reg['debug/trace']
    # return any(fnmatch.fnmatch(name, p) for p in cfg)


def get_obj_var_name(frame, obj):
    for var_name, var_obj in frame.f_locals.items():
        if obj is var_obj:
            return var_name
    else:
        None


def find_current_gear_frame():
    import inspect
    code_map = reg['gear/code_map']
    if not code_map:
        return None

    for frame, *_ in inspect.stack():
        if frame.f_code is code_map[-1].func.__code__:
            return frame
    else:
        return None


def check_args_num(argnames, varargsname, args):
    if (len(args) < len(argnames)) or (not varargsname and (len(args) > len(argnames))):
        balance = "few" if (len(args) < len(argnames)) else "many"

        raise TooManyArguments(f"Too {balance} arguments provided.")


def check_args_specified(args):
    for name, intf in args.items():
        if not isinstance(intf, Intf):
            raise GearArgsNotSpecified(f'Unresolved input argument "{name}": {repr(intf)}')

        if not type_is_specified(intf.dtype):
            raise GearArgsNotSpecified(
                f'Input argument "{name}" has unresolved type "{repr(intf.dtype)}"')


def resolve_gear_name(func, __base__):
    if __base__ is None:
        name = func.__name__
    else:
        name = __base__.__name__

    return name


oper_name = {
    '__add__': '+',
    '__and__': '&',
    '__floordiv__': '/',
    '__truediv__': '//',
    '__eq__': '==',
    '__ge__': '>=',
    '__gt__': '>',
    '__invert__': '~',
    '__le__': '<=',
    '__lt__': '<',
    '__lshift__': '<<',
    '__matmul__': '@',
    '__mod__': '%',
    '__mul__': '*',
    '__ne__': '!=',
    '__neg__': '-',
    '__rshift__': '>>',
    '__sub__': '-',
    '__xor__': '^',
}


def get_operator_name(func):
    for name, p in reg['gear/intf_oper'].items():
        if isinstance(p, Partial):
            p = p.func

        if p is func:
            return oper_name[name]

    return None


def infer_const_args(args):
    args_res = {}
    const_args = {}
    for name, intf in args.items():
        if not isinstance(intf, Intf):
            from pygears.lib.const import get_literal_type
            try:
                const_args[name] = intf
                intf = Intf(get_literal_type(intf))
            except GearTypeNotSpecified:
                if isinstance(intf, Partial):
                    # raise GearArgsNotSpecified(
                    #     f'Unresolved gear "{intf.func.__name__}" with inputs'
                    #     f' {intf.args} and parameters {intf.kwds},'
                    #     f'connected to the input "{name}"')

                    opinfo = ''
                    op = get_operator_name(intf.func)
                    if op:
                        opinfo = f' (operator "{op}")'

                    raise GearArgsNotSpecified(
                        f'Unresolved gear "{intf.func.__name__}"{opinfo} with'
                        f' arguments {intf.args} and parameters {intf.kwds},'
                        f' connected to the input "{name}": {str(MultiAlternativeError(intf.errors))}'
                    )
                else:
                    raise GearArgsNotSpecified(
                        f'Unresolved argument "{intf}" connected to the input'
                        f' "{name}"')

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

    if vararg_type_list:
        annotations[varargsname] = f'({", ".join(vararg_type_list)}, )'.encode()


def resolve_return_annotation(annotations):
    if "return" in annotations:
        ret_anot = annotations["return"]
        if isinstance(ret_anot, dict):
            annotations['return'] = tuple(ret_anot.values())
            if len(annotations['return']) == 1:
                annotations['return'] = annotations['return'][0]
    else:
        annotations['return'] = None


def resolve_args(args, argnames, annotations, varargs):
    check_args_num(argnames, varargs, args)
    args_dict = {name: a for name, a in zip(argnames, args)}

    if varargs:
        expand_varargs(args_dict, annotations, varargs, args[len(args_dict):])

    resolve_return_annotation(annotations)

    for a in args_dict:
        if a not in annotations:
            annotations[a] = Any

    return args_dict, annotations


def gear_signature(func, args, kwds):
    paramspec = inspect.getfullargspec(func)

    args, annotations = resolve_args(args, paramspec.args, paramspec.annotations, paramspec.varargs)

    kwddefaults = paramspec.kwonlydefaults or {}

    templates = {**annotations, **kwddefaults, **kwds}

    return args, templates


def infer_params(args, params, context):
    arg_types = {name: arg.dtype for name, arg in args.items()}

    return infer_ftypes(params, arg_types, namespace=context)


class intf_name_tracer:
    def __init__(self, gear):
        self.enabled = reg['gear/infer_signal_names']
        if self.enabled == 'debug':
            self.enabled = is_traced(gear)

        if not self.enabled:
            return

        self.code_map = reg['gear/code_map']
        self.gear = gear

    def tracer(self, frame, event, arg):
        if event == 'return':
            for cm in self.code_map:
                if frame.f_code is cm.func.__code__:
                    cm.func_locals = frame.f_locals.copy()

    def __enter__(self):
        if not self.enabled:
            return

        self.code_map.append(self.gear)

        # tracer is activated on next call, return or exception
        if reg['gear/current_module'].parent == reg['gear/root']:
            sys.setprofile(self.tracer)

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if not self.enabled:
            return

        if reg['gear/current_module'].parent == reg['gear/root']:
            sys.setprofile(None)

        cm = self.code_map.pop()

        if exception_type is None and hasattr(cm, 'func_locals'):
            for name, val in filter(lambda x: isinstance(x[1], Intf), cm.func_locals.items()):
                if not hasattr(val, 'var_name'):
                    val.var_name = name


# TODO: Apparently no error is thrown if an input interface is not connected
# within a hierarchical module
def resolve_func(gear_inst):
    out_dtype = gear_inst.params.get('return', None)
    if out_dtype is None:
        out_dtype = ()
    elif out_dtype:
        if isinstance(out_dtype, dict):
            out_dtype = tuple(out_dtype.values())

    if not isinstance(out_dtype, tuple):
        out_dtype = (out_dtype, )

    if not is_standard_func(gear_inst.func):
        # TODO: If something is being yield-ed and there is no output type
        # specified, try to throw an error
        return tuple(), out_dtype

    with create_hier(gear_inst):
        # TODO: Try to detect infinite recursions
        # TODO: If the gear is instantiated in REPL, intf_name_tracer will fail
        with intf_name_tracer(gear_inst):
            local_in_intfs = gear_inst.in_port_intfs
            out_intfs = gear_inst.func(*local_in_intfs, **gear_inst.explicit_params)

        if out_intfs is None:
            out_intfs = tuple()
        elif not isinstance(out_intfs, tuple):
            out_intfs = (out_intfs, )

        for i, intf in enumerate(out_intfs):
            if isinstance(intf, Partial):
                raise GearArgsNotSpecified(
                    f'Unresolved gear "{intf.func.__name__}" with'
                    f' arguments {intf.args} and parameters {intf.kwds},'
                    f' returned as output "{i}": {str(MultiAlternativeError(intf.errors))}')

        err = None
        try:
            out_intfs, out_dtype = resolve_out_types(out_intfs, out_dtype, gear_inst)
        except (TypeError, TypeMatchError) as e:
            err = type(e)(f"{str(e)}\n    when instantiating '{gear_inst.name}'")

        if err:
            raise err

    return out_intfs, out_dtype


def resolve_gear(gear_inst, out_intfs, out_dtype, fix_intfs):
    dflt_dout_name = reg['gear/naming/default_out_name']
    for i in range(len(gear_inst.outnames), len(out_dtype)):
        if out_intfs and hasattr(out_intfs[i], 'var_name'):
            gear_inst.outnames.append(out_intfs[i].var_name)
        else:
            gear_inst.outnames.append(dflt_dout_name if len(out_dtype) ==
                                      1 else f'{dflt_dout_name}{i}')

    gear_inst.connect_output(out_intfs, out_dtype)

    # Connect output interfaces
    intfs = []
    out_intfs = []
    if isinstance(fix_intfs, dict):
        for i, (name, dt) in enumerate(zip(gear_inst.outnames, out_dtype)):
            if (name in fix_intfs) or (i in fix_intfs):
                if name in fix_intfs:
                    intf = fix_intfs[name]
                elif i in fix_intfs:
                    intf = fix_intfs[i]

                err = None
                try:
                    get_match_conds(dt, intf.dtype)
                except (TypeError, TypeMatchError) as e:
                    err = type(
                        e
                    )(f"{str(e)}\n    when connecting user supplied output interface '{name}' of '{gear_inst.name}'"
                      f"\n    FIX: Consider changing the type of the supplied output interface '{name}' to '{repr(dt)}'"
                      )

                if err:
                    raise err
            else:
                intf = Intf(dt)
                out_intfs.append(intf)

            intfs.append(intf)

    elif fix_intfs:
        # TODO: Should we allow partially supplied fix_intfs? Maybe None should
        # be supplied where a new Intf should be created
        # TODO: Do similar type checking as above
        intfs = fix_intfs
    else:
        intfs = [Intf(dt) for dt in out_dtype]
        out_intfs = intfs

    if len(intfs) != len(gear_inst.out_port_intfs):
        raise GearArgsNotSpecified(
            f'Received {len(intfs)} output interfaces,'
            f' while expecting {len(gear_inst.out_port_intfs)}'
            f"\n    when instantiating '{gear_inst.name}'"
        )

    for intf, port in zip(intfs, gear_inst.out_ports):
        intf.source(port)

    if any(not type_is_specified(i.dtype) for i in out_intfs):
        raise GearTypeNotSpecified(f'Output type of the gear "{gear_inst.name}"'
                                   f' could not be resolved, and resulted in "{repr(out_dtype)}"')

    for c in gear_inst.child:
        channel_interfaces(c)

    if len(out_intfs) > 1:
        return tuple(out_intfs)
    elif len(out_intfs) == 1:
        return out_intfs[0]
    else:
        return None


def resolve_out_types(out_intfs, out_dtype, gear_inst):

    if out_intfs and (not out_dtype):
        out_dtype = tuple(intf.dtype for intf in out_intfs)
        return out_intfs, out_dtype

    if out_intfs:
        if len(out_intfs) != len(out_dtype):
            relation = 'smaller' if len(out_intfs) < len(out_dtype) else 'larger'
            raise TypeMatchError(
                f"Number of actual output interfaces ({len(out_intfs)}) is {relation} "
                f"than the number of specified output types: ({tuple(getattr(i, 'dtype', type(i)) for i in out_intfs)})"
                f" vs {repr(out_dtype)}")

        casted_out_intfs = list(out_intfs)

        # Try casting interface types upfront to get better error messaging
        for i, (intf, t) in enumerate(zip(out_intfs, out_dtype)):
            err = None
            try:
                if intf.dtype != t:
                    cast(intf.dtype, t)
            except (TypeError, TypeMatchError) as e:
                err = type(e)(f"{str(e)}, when casting type for output port {i}")

            if err:
                raise err

        # If no exceptions occured, do it for real
        for i, (intf, t) in enumerate(zip(out_intfs, out_dtype)):
            if intf.dtype != t:
                from pygears.lib.cast import cast as cast_gear
                casted_out_intfs[i] = cast_gear(intf, t=t)

        out_intfs = tuple(casted_out_intfs)
        return out_intfs, out_dtype

    return out_intfs, out_dtype


def terminate_internal_intfs(gear_inst):
    if not is_standard_func(gear_inst.func):
        for p in gear_inst.in_ports:
            if p.consumer is not None:
                p.consumer.connect(HDLConsumer())

        for i in gear_inst.out_port_intfs:
            i.source(HDLProducer())


def gear_base_resolver(func, *args, name=None, intfs=None, **kwds):
    meta_kwds = func.meta_kwds
    name = name or resolve_gear_name(func, meta_kwds['__base__'])

    err = None
    try:
        args, param_templates = gear_signature(func, args, kwds)

        param_templates['_enablement'] = meta_kwds['enablement']
        args, const_args = infer_const_args(args)
        check_args_specified(args)
    except (TooManyArguments, GearArgsNotSpecified) as e:
        err = type(e)(f'{str(e)}\n - when instantiating "{name}"')

    if err:
        raise err

    if intfs is None:
        fix_intfs = []
    elif isinstance(intfs, Intf):
        fix_intfs = [intfs]
    elif isinstance(intfs, dict):
        fix_intfs = intfs
    else:
        fix_intfs = list(intfs)

    if reg['gear/memoize']:
        gear_inst, outputs, memo_key = get_memoized_gear(func, args, const_args, kwds, fix_intfs,
                                                         name)

        if gear_inst is not None:
            if len(outputs) == 1:
                return outputs[0]
            else:
                return outputs

    try:
        params = infer_params(args, param_templates, context=get_function_context_dict(func))
    except TypeMatchError as e:
        err = type(e)(f'{str(e)}\n - when instantiating "{name}"')

    if err:
        raise err

    if not err:
        if not params.pop('_enablement'):
            err = TypeMatchError(f'Enablement condition failed for "{name}" alternative'
                                 f' "{meta_kwds["definition"].__module__}.'
                                 f'{meta_kwds["definition"].__name__}": '
                                 f'{meta_kwds["enablement"].decode()}')

    params['name'] = name
    params['intfs'] = fix_intfs

    gear_inst = Gear(func, params)

    if err:
        err.gear = gear_inst
        err.root_gear = gear_inst

    if not err:
        gear_inst.connect_input(args, const_args)
        try:
            out_intfs, out_dtype = resolve_func(gear_inst)
            out_intfs = resolve_gear(gear_inst, out_intfs, out_dtype, fix_intfs)
            terminate_internal_intfs(gear_inst)

        except (TooManyArguments, GearTypeNotSpecified, GearArgsNotSpecified, TypeError,
                TypeMatchError, MultiAlternativeError) as e:
            err = e
            if hasattr(func, 'alternatives') or hasattr(func, 'alternative_to'):
                err.root_gear = gear_inst
        except Exception as e:
            if not hasattr(e, '_stamped'):
                e.args = (f'{str(e)}, in the module "{reg["gear/current_module"].name}/{name}"', )
                e._stamped = True

            err = e

    if err:
        if hasattr(func, 'alternatives') or hasattr(func, 'alternative_to'):
            gear_inst.parent.child.remove(gear_inst)
            for port in gear_inst.in_ports:
                if port.basename not in gear_inst.const_args:
                    port.producer.consumers.remove(port)
                else:
                    gear_inst.parent.child.remove(get_producer_port(port).gear)

        raise err

    if reg['gear/memoize'] and not func.__name__.endswith('_unpack__'):
        if memo_key is not None:
            memoize_gear(gear_inst, memo_key)

    return out_intfs


class GearInstPlugin(GearDecoratorPlugin):
    @classmethod
    def bind(cls):
        reg['gear/code_map'] = []
        reg['gear/gear_dflt_resolver'] = gear_base_resolver
        reg.confdef('gear/memoize', False)
        reg.confdef('gear/infer_signal_names', 'debug')
        reg.confdef('debug/trace', default=[])

    @classmethod
    def reset(cls):
        reg['gear/code_map'] = []
