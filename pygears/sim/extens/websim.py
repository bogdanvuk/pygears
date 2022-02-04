from enum import IntEnum
import time
import multiprocessing
from pygears.core.hier_node import HierYielderBase
from pygears.conf import inject, Inject
import os
from pygears.typing import typeof
from pygears import find, reg
from pygears.hdl import HDLPlugin
from pygears.hdl.sv.intf import SVIntfGen
from pygears.core.gear import Gear, Intf
from pygears.core.port import HDLConsumer, OutPort, Port, InPort
from pygears.sim import timestep
from .sim_extend import SimExtend
from pygears.core.hier_node import HierVisitorBase
from pygears.sim.modules import SimVerilated, SimSocket

multiprocessing.set_start_method('fork')

VALUE = set(('0', '1', 'x', 'X', 'z', 'Z'))
INVALID_VALUE = set(('x', 'X', 'z', 'Z'))
VECTOR_VALUE_CHANGE = set(('b', 'B', 'r', 'R'))
VALUE_CHANGE = VALUE | VECTOR_VALUE_CHANGE


@inject
def find_cosim_modules(top=Inject('gear/root')):
    class CosimVisitor(HierVisitorBase):
        @inject
        def __init__(self, sim_map=Inject('sim/map')):
            self.sim_map = sim_map
            self.cosim_modules = []

        def Gear(self, module):
            if isinstance(self.sim_map.get(module, None), SimVerilated):
                self.cosim_modules.append(self.sim_map[module])
                return True

    v = CosimVisitor()
    v.visit(top)
    return v.cosim_modules


class ChannelState(IntEnum):
    Invalid = 0
    NotReady = 1
    Ready = 2
    Done = 3
    Awaiting = 4


import functools


@functools.lru_cache(maxsize=None)
def subtypes(dtype):
    return tuple((t, t.width) for t in dtype)


def split_coded_dtype(t, val):
    for subt, subt_width in t:
        subt_mask = (1 << subt_width) - 1
        yield val & subt_mask
        val >>= subt_width


def split_coded_change(t, val1, val2):
    for subt, subt_width in subtypes(t):
        subt_mask = (1 << subt_width) - 1

        subval1 = val1 & subt_mask
        val1 >>= subt_width

        if val2 is not None:
            subval2 = val2 & subt_mask
            val2 >>= subt_width
        else:
            subval2 = None

        yield subt, subval1, subval2


def create_data_change(t, val, prev_val):
    from pygears.typing import Queue, Array, Tuple, Union
    is_changed = prev_val is None and val is not None or val != prev_val

    if typeof(t, (Queue, Array, Tuple, Union)):
        change = [
            create_data_change(subt, v, prev_v)
            for subt, v, prev_v in split_coded_change(t, val, prev_val)
        ]

        # return {'isValueComplex': True, 'isDataChanged': is_changed, 'value': change}
        return (1, int(is_changed), change)
    else:
        if isinstance(val, (int, float)):
            val = int(val)

        return (0, int(is_changed), val)
        # return {'isValueComplex': False, 'isDataChanged': is_changed, 'value': val}


class VcdToJson:
    def __init__(self):
        self.json_vcd = {}
        self.diff = {}
        self.state = {}
        self.value = {}

    def create_change(self, timestep, state, state_change, t, val, prev_val):
        # elem = {
        #     'cycle': timestep,
        #     'state': int(state),
        #     'isStateChanged': state_change,
        # }

        elem = [timestep, int(state), int(state_change)]

        if val is not None:
            elem.append(create_data_change(t, val, prev_val))
            # elem['data'] = create_data_change(t, val, prev_val)

        import json
        # print(json.dumps(elem, separators=(',', ':')))

        return json.dumps(elem, separators=(',', ':'))

    def after_timestep(self, timestep):
        for p, d in self.diff.items():
            changes = self.json_vcd[p.name]
            data_change = False
            new_state = state = self.state[p]
            prev_val = self.value[p]
            new_val = d['d']

            # data_change = new_val is not None and (prev_val or prev_val != new_val)

            # if data_change:
            #     new_val = p.dtype.decode(d['d'])
            # else:
            #     new_val = None

            if state == ChannelState.Invalid:
                if d['v'] and d['r']:
                    new_state = ChannelState.Ready
                    data_change = True
                elif d['v']:
                    new_state = ChannelState.NotReady
                    data_change = True
                elif d['r']:
                    new_state = ChannelState.Awaiting
            elif state == ChannelState.Ready:
                if d['r'] == 0 and d['v'] == 0:
                    new_state = ChannelState.Invalid
                elif d['r'] == 0:
                    new_state = ChannelState.NotReady
                    data_change = prev_val != new_val
                elif d['v'] == 0:
                    new_state = ChannelState.Awaiting
                else:
                    data_change = prev_val != new_val
            elif state == ChannelState.NotReady:
                if d['r']:
                    new_state = ChannelState.Ready
            elif state == ChannelState.Awaiting:
                if d['r'] == 0 and d['v']:
                    new_state = ChannelState.NotReady
                    data_change = prev_val != new_val
                elif d['v']:
                    new_state = ChannelState.Ready
                    data_change = prev_val != new_val

            new_state_json = new_state
            if new_state_json == ChannelState.Awaiting:
                new_state_json = ChannelState.Invalid

            state_json = state
            if state_json == ChannelState.Awaiting:
                state_json = ChannelState.Invalid

            if new_state_json != state_json or data_change or timestep == 0:
                cycle_change = self.create_change(
                    timestep,
                    new_state_json,
                    state_change=(new_state_json != state_json),
                    t=p.dtype,
                    val=(None if new_state_json == ChannelState.Invalid else new_val),
                    prev_val=prev_val)

                if cycle_change is not None:
                    changes.append(cycle_change)

            if data_change:
                self.value[p] = new_val

            self.state[p] = new_state

        # self.diff.clear()


def follow(fn, finish_event=None, sleep_sec=0.1):
    """ Yield each line from a file as they are written.
    `sleep_sec` is the time to sleep after empty reads. """
    line = ''
    with open(fn) as f:
        while True:
            tmp = f.readline()
            if tmp:
                line += tmp
                if line.endswith("\n"):
                    yield line
                    line = ''
            else:
                if finish_event is None or finish_event.is_set():
                    return

                time.sleep(sleep_sec)


# def follow(fn, finish_event, sleep_sec=0.5):
#     import time
#     import subprocess
#     import select

#     f = subprocess.Popen(['tail', '-F', fn], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#     p = select.poll()
#     p.register(f.stdout)

#     while True:
#         if p.poll(sleep_sec):
#             yield f.stdout.readline().decode()
#         elif finish_event.is_set():
#             return
#         else:
#             # print(f'Sleep')
#             time.sleep(sleep_sec)


def vcd_to_json_worker(entries, wire_map: dict, vcd_conv, t):
    for identifier_code, value in entries:

        if identifier_code not in wire_map:
            continue

        for port, wire_name in wire_map[identifier_code]:
            # print(f'"{identifier_code}": {port.name}_{wire_name} change @ {t}')

            if port not in vcd_conv.diff:
                vcd_conv.diff[port] = {'r': None, 'v': None, 'd': None}

            if wire_name == 'valid':
                vcd_conv.diff[port]['v'] = value
            elif wire_name == 'ready':
                vcd_conv.diff[port]['r'] = value
            elif wire_name == 'data' and value is not None:
                vcd_conv.diff[port]['d'] = value

    vcd_conv.after_timestep(t)


def vcd_to_json(top, file_iter):
    wire_map = {}
    vcd_conv = None
    skip_scope = 0
    bc_parent = None

    t = -1
    hier = top
    worker_data = []

    for line in file_iter:
        # for line in f:
        line = line.strip()
        if line == '':
            continue

        line_head = line[0]

        if line_head == '#':
            next_t = int(line[1:])
            if next_t % 10 != 0:
                continue

            next_t //= 10

            if t == -1:
                vcd_conv = VcdToJson()
                for identifier_code in wire_map:
                    for p, _ in wire_map[identifier_code]:
                        vcd_conv.state[p] = ChannelState.Invalid
                        vcd_conv.value[p] = None
                        vcd_conv.json_vcd[p.name] = []

            if t >= 0:
                vcd_to_json_worker(worker_data, wire_map, vcd_conv, t)
                worker_data.clear()

            t = next_t

        elif line_head in VALUE_CHANGE:
            if line_head in VECTOR_VALUE_CHANGE:
                value, identifier_code = line[1:].split()
            elif line_head in VALUE:
                value = line[0]
                identifier_code = line[1:]

            if value[0] in INVALID_VALUE:
                value = None
            elif value[0] not in ('b', 'B'):
                value = int(value, 2)
            else:
                value = int(value[1:])

            if identifier_code in wire_map:
                worker_data.append((identifier_code, value))

        elif '$enddefinitions' in line:
            pass
        elif '$scope' in line:
            if skip_scope:
                skip_scope += 1
                continue

            segs = line.split()
            # Name of the TOP is ' '
            if len(segs) == 3:
                hier = top
                continue

            scope_name = segs[2]
            child = None

            if scope_name.startswith('_') and scope_name.endswith('_spy'):
                scope_name = scope_name[1:-4]

            if scope_name == 'TOP' or scope_name.endswith('_wrap'):
                hier = top
                continue

            if scope_name.startswith('bc_'):
                skip_scope = 1
                continue
            elif '_bc_' in scope_name:
                scope_name, _, bc_dout_id = scope_name.rpartition('_')
                scope_name = scope_name[1:-3]

                for i in hier.local_intfs:
                    svmod = reg['hdlgen/map'].get(i, i)
                    if svmod.basename == scope_name:
                        child = i.consumers[int(bc_dout_id)]
                        bc_parent = hier
                        break
                else:
                    breakpoint()

            else:
                child = None
                for c in hier.child + hier.local_intfs:
                    svmod = reg['hdlgen/map'].get(c, None)
                    if svmod is None:
                        continue

                    if isinstance(svmod, SVIntfGen):
                        if svmod.basename == scope_name:
                            child = c
                            break
                    elif svmod.inst_name == scope_name:
                        child = c
                        break

            if child is None:
                child = find(f'{hier.name}.{scope_name}')

                if child is not None and hier.parent is not None and not node_hierarchical(
                        hier.parent):
                    skip_scope = 1
                    continue

                if not isinstance(child, Port):
                    child = None

            if child is None:
                child = find(f'{hier.name}/{scope_name}')

            if child is None:
                skip_scope = 1
                continue

            hier = child

        elif '$upscope' in line:
            if skip_scope:
                skip_scope -= 1
                continue

            if bc_parent is not None:
                hier = bc_parent
                bc_parent = None
            elif isinstance(hier, (Gear, Intf)):
                if hier is not top:
                    hier = hier.parent
            else:
                hier = hier.gear
        elif '$var' in line:
            if hier is top or skip_scope:
                continue

            if not isinstance(hier, (Port, Intf)):
                continue

            # Output ports are not monitored for non-hierarchical gears, since
            # the output channel will be picked up by the consumer.
            # UNLESS:
            #    - It is a hierarchical gear, which means there is a part of
            #      the interface inside the hierarchical gear
            #    - It is an output port which is connected to a broadcast

            if (isinstance(hier, Port) and not isinstance(hier, InPort)
                    and not node_hierarchical(hier.gear) and not len(hier.consumer.consumers) > 1):
                continue

            ls = line.split()
            identifier_code = ls[3]
            name = ls[4]
            # name = ''.join(ls[4:-1])
            # print(f'Var "{identifier_code}": {hier.name}_{name}')
            if identifier_code not in wire_map:
                wire_map[identifier_code] = []

            if isinstance(hier, OutPort) and len(hier.consumer.consumers) > 1:
                wire_map[identifier_code].append((hier.consumer, name))
            else:
                wire_map[identifier_code].append((hier, name))

        elif '$timescale' in line:
            continue

    if vcd_conv is None:
        return None

    return vcd_conv.json_vcd


def vcd_to_json_task(vcd_fn, finish_event, ret_pipe, top):
    import os
    import time

    while not os.path.exists(vcd_fn):
        time.sleep(0.1)

    time.sleep(0.1)

    json_vcd = vcd_to_json(top, follow(vcd_fn, finish_event))

    ret_pipe.send(json_vcd)


def dtype_tree(dtype):
    from pygears.typing import Queue, Array, Tuple, Union
    if issubclass(dtype, Array):
        return {'name': repr(dtype), 'subtypes': [dtype_tree(t) for t in dtype]}
    elif issubclass(dtype, (Queue, Array, Tuple, Union)):
        return {
            'name': repr(dtype),
            'subtypes': [dtype_tree(t) for t in dtype],
            'keys': dtype.fields
        }
    else:
        return {'name': repr(dtype)}


def node_hierarchical(node):
    return node.hierarchical and node.meta_kwds.get('hdl', {}).get('hierarchical', True)


def dump_json_graph(top):
    nodes = {}
    ports = {}
    connections = {}

    class NodeYielder(HierYielderBase):
        def Gear(self, node):
            yield node
            return not node_hierarchical(node)

    for node in NodeYielder().visit(find(top)):
        in_ports = []
        for p in node.in_ports:
            ports[p.name] = {
                'basename': p.basename,
                'name': p.name,
                'dtype': repr(p.dtype),
                'index': p.index
            }
            in_ports.append(p.name)

        out_ports = []
        for p in node.out_ports:
            ports[p.name] = {
                'basename': p.basename,
                'name': p.name,
                'dtype': repr(p.dtype),
                'index': p.index
            }
            out_ports.append(p.name)

        node_json = {
            'basename': node.basename,
            'name': node.name,
            'definition': 'None' if node.definition is None else
            f'{node.definition.func.__module__}.{node.definition.func.__name__}',
            'in_ports': in_ports,
            'out_ports': out_ports
        }

        nodes[node.name] = node_json

    for node in NodeYielder().visit(find(top)):
        nodes[node.name]['child'] = []
        if node_hierarchical(node):  # node.hierarchical:
            for c in node.child:
                nodes[node.name]['child'].append(c.name)

    for node in NodeYielder().visit(find(top)):
        for p in node.in_ports + node.out_ports:
            if p.consumer is None or any(isinstance(c, HDLConsumer) for c in p.consumer.consumers):
                continue

            if isinstance(p, InPort) and not node_hierarchical(node):
                continue

            i = p.consumer
            connections[i.name] = {
                'producer': i.producer.name,
                'dtype': repr(p.dtype),
                'dtype_tree': dtype_tree(p.dtype),
                'name': i.name
            }

            consumers = [pc.name for pc in i.consumers if not isinstance(pc, HDLConsumer)]

            if len(consumers) <= 1:
                connections[i.name]['consumers'] = consumers
                for c in consumers:
                    ports[c]['producer'] = i.name
            else:

                parent = node if node_hierarchical(node) and isinstance(p, InPort) else node.parent
                bc_basename = f'{i.basename}_bc'
                bc_name = f'{parent.name}/{bc_basename}'
                inp_name = f'{bc_name}.din'
                ports[f'{bc_name}.din'] = {
                    'basename': 'din',
                    'name': inp_name,
                    'producer': i.name,
                    'dtype': repr(p.dtype),
                    'index': 0
                }
                in_ports = [inp_name]

                connections[i.name]['consumers'] = [inp_name]

                out_ports = []
                for c in range(len(consumers)):
                    outp_name = f'{bc_name}.dout{c}'
                    ports[outp_name] = {
                        'basename': f'dout{c}',
                        'name': outp_name,
                        'consumer': outp_name,
                        'dtype': repr(p.dtype),
                        'index': c
                    }
                    connections[outp_name] = {
                        'producer': outp_name,
                        'dtype': repr(p.dtype),
                        'dtype_tree': dtype_tree(p.dtype),
                        'name': outp_name,
                        'consumers': [consumers[c]]
                    }
                    ports[consumers[c]]['producer'] = outp_name

                    out_ports.append(outp_name)

                node_json = {
                    'basename': bc_basename,
                    'name': bc_name,
                    'definition': 'broadcast',
                    'in_ports': in_ports,
                    'out_ports': out_ports,
                    'child': []
                }

                nodes[parent.name]['child'].append(bc_name)
                nodes[bc_name] = node_json

            # if not all(isinstance(p, HDLConsumer) for p in i.consumers):
            ports[i.producer.name]['consumer'] = i.name

    return {'gears': nodes, 'ports': ports, 'connections': connections}


class WebSim(SimExtend):
    @inject
    def __init__(self, trace_fn='pygears.json', outdir=Inject('results-dir'), multiprocess=True):
        super().__init__()
        self.outdir = outdir
        self.trace_fn = os.path.abspath(os.path.join(self.outdir, trace_fn))
        self.multiprocess = multiprocess
        self.cosim_modules = []
        self.p = []
        # atexit.register(self.finish)

        self.vcd_fn = os.path.abspath(os.path.join(self.outdir, 'pygears.vcd'))
        self.finished = False

    def register_vcd_worker(self, vcd_fn, top):
        qin, qout = multiprocessing.Pipe(duplex=False)
        self.qin.append(qin)

        p = multiprocessing.Process(target=vcd_to_json_task,
                                    args=(vcd_fn, self.finish_event, qout, top))
        self.p.append(p)

    def before_run(self, sim):
        if not self.multiprocess:
            for m in find_cosim_modules():
                self.cosim_modules.append((m.gear.parent, m.trace_fn))

            return

        self.finish_event = multiprocessing.Event()

        self.qin = []
        self.p = []
        for m in find_cosim_modules():
            if not m.trace_fn:
                continue
            self.register_vcd_worker(m.trace_fn, top=m.gear.parent)

        self.register_vcd_worker(self.vcd_fn, find('/'))

        for p in self.p:
            p.start()

    def sim_vcd_to_json(self):
        graph = dump_json_graph('/')

        if self.multiprocess:
            self.finish_event.set()
            json_vcds = [qin.recv() for qin in self.qin]

            for p in self.p:
                p.join()
        else:
            json_vcds = []
            for top, trace_fn in self.cosim_modules:
                json_vcds.append(vcd_to_json(top, follow(trace_fn)))

            json_vcds.append(vcd_to_json(find('/'), follow(self.vcd_fn)))

        visited_channels = set()
        changes = []
        for json_vcd in json_vcds:
            if json_vcd is None:
                continue
            for p_name in json_vcd:
                p = find(p_name)
                intf_name = p_name
                port_name = None if isinstance(p, Intf) else p.producer.name
                if ((isinstance(p, InPort) or
                     (isinstance(p, OutPort) and node_hierarchical(p.gear)))
                        and len(p.producer.consumers) > 1):
                    for i in range(len(p.producer.consumers)):
                        if p.producer.consumers[i] is p:
                            break

                    if isinstance(p, InPort) and node_hierarchical(p.gear):
                        intf_name = p_name
                    bc_name = f'{p.producer.parent.name}/{p.producer.basename}_bc'
                    port_name = f'{bc_name}.dout{i}'

                if isinstance(p, InPort) and (p.consumer is None or any(
                        isinstance(c, HDLConsumer) for c in p.consumer.consumers)):
                    intf_name = None

                for channel_name in [intf_name, port_name]:
                    if channel_name is not None and channel_name not in visited_channels:
                        changes.append({'channelName': channel_name, 'changes': json_vcd[p_name]})
                        visited_channels.add(channel_name)

        return {
            'graphInfo': graph,
            'simulationChanges': {
                'startCycle': 0,
                'endCycle': timestep(),
                'channelChanges': changes
            }
        }

    def finish(self):
        if not self.finished:
            err = None
            json_out = self.sim_vcd_to_json()
            try:
                # json_out = self.sim_vcd_to_json()
                import json
                json.dump(json_out, open(self.trace_fn, 'w'), separators=(',', ':'))
                # json.dump(json_out, open(self.trace_fn, 'w'))
                # json.dump(json_out, open(self.trace_fn, 'w'), indent=4)
            except Exception as e:
                for p in self.p:
                    p.terminate()
                err = e

            if err is not None:
                raise err

            self.finished = True

    def after_cleanup(self, sim):
        self.finish()


def websim_activate(var, val):
    if val:
        if WebSim not in reg['sim/extens']:
            reg['debug/expand_trace_data'] = False
            reg['debug/trace_end_cycle_dump'] = False
            reg['sim/extens'].append(WebSim)
    else:
        if WebSim in reg['sim/extens']:
            reg['debug/expand_trace_data'] = True
            reg['debug/trace_end_cycle_dump'] = True
            del reg['sim/extens'][reg['sim/extens'].index(WebSim)]


class WebSimPlugin(HDLPlugin):
    @classmethod
    def bind(cls):
        reg.confdef('debug/webviewer', setter=websim_activate, default=False)
