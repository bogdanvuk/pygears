from enum import IntEnum
from pygears.core.hier_node import HierYielderBase
from pygears.conf import inject, Inject
import os
import atexit
from pygears import find
from pygears.core.gear import Gear
from pygears.core.port import HDLConsumer
from pygears.sim import timestep
from .sim_extend import SimExtend

VALUE = set(('0', '1', 'x', 'X', 'z', 'Z'))
INVALID_VALUE = set(('x', 'X', 'z', 'Z'))
VECTOR_VALUE_CHANGE = set(('b', 'B', 'r', 'R'))
VALUE_CHANGE = VALUE | VECTOR_VALUE_CHANGE


class ChannelState(IntEnum):
    Invalid = 0
    NotReady = 1
    Ready = 2
    Done = 3
    Awaiting = 4


class VcdToJson:
    def __init__(self):
        self.json_vcd = {}
        self.diff = {}
        self.state = {}
        self.value = {}

    def create_data_change(self, val, prev_val):
        from pygears.typing import Queue, Array, Tuple
        is_changed = prev_val is None and not val is None or val != prev_val

        if isinstance(val, (Queue, Array, Tuple)):
            if prev_val is None:
                prev_val = [None] * len(val)

            change = [self.create_data_change(v, prev_v) for v, prev_v in zip(val, prev_val)]
            return {'isValueComplex': True, 'isDataChanged': is_changed, 'value': change}
        else:
            if isinstance(val, (int, float)):
                val = int(val)
            else:
                val = val.code()

            return {'isValueComplex': False, 'isDataChanged': is_changed, 'value': val}

    def create_change(self, timestep, state, state_change, val, prev_val):
        elem = {
            'cycle': timestep,
            'state': int(state),
            'isStateChanged': state_change,
        }

        if val is not None:
            elem['data'] = self.create_data_change(val, prev_val)

        return elem

    def after_timestep(self, timestep):
        for p, d in self.diff.items():
            changes = self.json_vcd[p]
            new_state = state = self.state[p]

            data_change = self.value[p] is None or (d['d'] is not None and self.value[p] != d['d'])
            if data_change:
                new_val = p.dtype.decode(d['d'])

            if state == ChannelState.Invalid:
                if d['v'] and d['r']:
                    new_state = ChannelState.Ready
                elif d['v']:
                    new_state = ChannelState.NotReady
                elif d['r']:
                    new_state = ChannelState.Awaiting
            elif state == ChannelState.Ready:
                if d['r'] == 0 and d['v'] == 0:
                    new_state = ChannelState.Invalid
                elif d['r'] == 0:
                    new_state = ChannelState.NotReady
                elif d['v'] == 0:
                    new_state = ChannelState.Awaiting
            elif state == ChannelState.NotReady:
                if d['r']:
                    new_state = ChannelState.Ready
            elif state == ChannelState.Awaiting:
                if d['r'] == 0 and d['v']:
                    new_state = ChannelState.NotReady
                elif d['v']:
                    new_state = ChannelState.Ready

            if new_state != state or data_change or timestep == 0:
                cycle_change = self.create_change(timestep,
                                                  new_state,
                                                  state_change=True,
                                                  val=new_val,
                                                  prev_val=self.value[p])

                if cycle_change is not None:
                    changes.append(cycle_change)

            if d['d'] is not None and data_change:
                self.value[p] = new_val

            self.state[p] = new_state


def vcd_to_json(vcd_fn):
    vcd_conv = VcdToJson()

    with open(vcd_fn) as f:
        wire_map = {}
        timestep = -1
        top = find('/')
        hier = top

        for line in f:
            line = line.strip()
            if line == '':
                continue

            line_head = line[0]

            if line_head == '#':
                if timestep >= 0:
                    vcd_conv.after_timestep(timestep)
                timestep = int(line[1:])
            elif line_head in VALUE_CHANGE:
                if line_head in VECTOR_VALUE_CHANGE:
                    value, identifier_code = line[1:].split()
                elif line_head in VALUE:
                    value = line[0]
                    identifier_code = line[1:]

                if identifier_code not in wire_map:
                    continue

                port, wire_name = wire_map[identifier_code]

                if port not in vcd_conv.diff:
                    vcd_conv.diff[port] = {'r': None, 'v': None, 'd': None}

                if wire_name == 'valid':
                    vcd_conv.diff[port]['v'] = int(value)
                elif wire_name == 'ready':
                    vcd_conv.diff[port]['r'] = int(value)
                elif wire_name == 'data' and value[0] not in INVALID_VALUE:
                    if value[0] not in ('b', 'B'):
                        value = int(value, 2)
                    else:
                        value = int(value[1:])

                    # vcd_conv.diff[port]['d'] = port.dtype.decode(value)
                    vcd_conv.diff[port]['d'] = value

            elif '$enddefinitions' in line:
                pass
            elif '$scope' in line:
                segs = line.split()
                # Name of the TOP is ' '
                if len(segs) == 3:
                    hier = top
                    continue

                scope_name = segs[2]

                child = find(f'{hier.name}.{scope_name}')

                if child is None:
                    child = hier[scope_name]

                if child is None:
                    raise Exception(f'Cannot find gear for scope: {line}')

                hier = child

            elif '$upscope' in line:
                if isinstance(hier, Gear):
                    if not hier is top:
                        hier = hier.parent
                else:
                    hier = hier.gear
            elif '$var' in line:
                if hier is top:
                    continue

                ls = line.split()
                identifier_code = ls[3]
                name = ''.join(ls[4:-1])
                vcd_conv.state[hier] = ChannelState.Invalid
                vcd_conv.value[hier] = None
                vcd_conv.json_vcd[hier] = []

                wire_map[identifier_code] = (hier, name)
            elif '$timescale' in line:
                continue

        return vcd_conv.json_vcd


def dtype_tree(dtype):
    from pygears.typing import Queue, Array, Tuple
    if issubclass(dtype, Array):
        return {'name': repr(dtype), 'subtypes': [dtype_tree(t) for t in dtype]}
    elif issubclass(dtype, (Queue, Array, Tuple)):
        return {
            'name': repr(dtype),
            'subtypes': [dtype_tree(t) for t in dtype],
            'keys': dtype.fields
        }
    else:
        return {'name': repr(dtype)}


def dump_json_graph(top):

    nodes = {}
    ports = {}
    connections = {}

    class NodeYielder(HierYielderBase):
        def Gear(self, node):
            yield node

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
        for c in node.child:
            nodes[node.name]['child'].append(c.name)

    for node in NodeYielder().visit(find(top)):
        for p in node.in_ports + node.out_ports:
            if p.consumer is None:
                continue

            i = p.consumer
            connections[i.name] = {
                'producer': i.producer.name,
                'dtype': repr(p.dtype),
                'dtype_tree': dtype_tree(p.dtype),
                'name': i.name,
                'consumers': [pc.name for pc in i.consumers if not isinstance(pc, HDLConsumer)]
            }

            ports[i.producer.name]['consumer'] = i.name
            for p in i.consumers:
                if isinstance(p, HDLConsumer):
                    continue

                ports[p.name]['producer'] = i.name

        # for i in node.local_intfs:
        #     if i.name == '.depthwise':
        #         breakpoint()

        #     connections[i.producer.name] = {
        #         'producer': i.producer.name,
        #         'dtype': repr(p.dtype),
        #         'dtype_tree': dtype_tree(p.dtype),
        #         'name': i.name,
        #         'consumers': [p.name for p in i.consumers]
        #     }
        #     ports[i.producer.name]['consumer'] = i.name
        #     for p in i.consumers:
        #         ports[p.name]['producer'] = i.name

    return {'gears': nodes, 'ports': ports, 'connections': connections}

    # import json
    # # s = json.dumps({'gears': nodes, 'ports': ports, 'connections': connections})

    # with open(fn, 'w') as f:
    #     f.write(json.dumps(graph, indent=4, sort_keys=True))


class WebSim(SimExtend):
    @inject
    def __init__(self, trace_fn='pygears.json', outdir=Inject('results-dir')):
        super().__init__()
        self.outdir = outdir
        self.trace_fn = os.path.abspath(os.path.join(self.outdir, trace_fn))
        # atexit.register(self.finish)

        self.vcd_fn = os.path.abspath(os.path.join(self.outdir, 'pygears.vcd'))
        self.finished = False

    def sim_vcd_to_json(self):
        graph = dump_json_graph('/')
        json_vcd = vcd_to_json(self.vcd_fn)

        changes = []
        for p in json_vcd:
            changes.append({
                'channelName': p.producer.name,
                'changes': json_vcd[p]
            })

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
            from pycallgraph import PyCallGraph
            from pycallgraph.output import GraphvizOutput

            with PyCallGraph(output=GraphvizOutput()):
                json_out = self.sim_vcd_to_json()

            # print(f'VcdToJson in {time.time() - start}')
            import json
            # json.dump(json_out, open(self.trace_fn, 'w'), indent=4)
            json.dump(json_out, open(self.trace_fn, 'w'))
            self.finished = True

    def after_cleanup(self, sim):
        self.finish()
