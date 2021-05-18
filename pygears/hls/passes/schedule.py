from queue import Queue
import attr
import inspect
from .. import cfg as cfgutil
from contextlib import contextmanager
from copy import deepcopy, copy
from ..cfg import Node, draw_cfg, CfgDfs
from ..cfg_util import insert_node_before, insert_node_after
from ..ir_utils import res_true, HDLVisitor, ir, add_to_list, res_false, is_intf_id, IrRewriter, IrExprVisitor
from pygears.typing import bitw, Uint, Bool
from .inline_cfg import VarScope, ExploreState
from .exit_cond_cfg import ResolveBlocking, cond_wrap
from ..cfg_util import insert_node_before


class VariableFinder(IrExprVisitor):
    def __init__(self):
        self.variables = set()

    def visit_AssignValue(self, node: ir.AssignValue):
        self.visit(node.target)
        self.visit(node.val)

    def visit_Branch(self, node: ir.Branch):
        self.visit(node.test)

    def visit_Name(self, node):
        if node.ctx == 'load':
            self.variables.add(node.name)


def create_scheduled_cfg(node, G, visited, labels, reaching=None, simple=True):
    if node in visited:
        return

    visited.add(node)
    if node.value is None:
        name = "None"
    elif isinstance(node.value, ir.Branch):
        if node.value.test == ir.res_true:
            name = 'else'
        else:
            name = f'if {node.value.test}'
    elif isinstance(node.value, (ir.HDLBlock, ir.BaseBlock)):
        name = f'{type(node.value)}'
    else:
        name = str(node.value)

    if reaching and node in reaching:
        name += ' <- ' + ','.join([str(rin[1]) for rin in reaching[node].get('in', {})])

    labels[id(node)] = name

    for n in node.next:
        if simple:
            if isinstance(n.value, ir.Branch) and n.next:
                n = n.next[0]

            while (n.next and
                   (isinstance(n.value, ir.BaseBlockSink) or isinstance(n.value, ir.HDLBlockSink))):
                n = n.next[0]

        G.add_edge(id(node), id(n))

        create_scheduled_cfg(n, G, visited, labels, reaching=reaching, simple=simple)


def draw_scheduled_cfg(cfg, reaching=None, simple=True):
    import networkx as nx
    import matplotlib.pyplot as plt

    G = nx.DiGraph()
    visited = set()
    labels = {}

    create_scheduled_cfg(cfg, G, visited, labels, reaching=reaching, simple=simple)

    pos = nx.planar_layout(G)
    nx.draw(G, pos, font_size=16, with_labels=False)

    # for p in pos:  # raise text positions
    #     pos[p][1] += 0.07

    nx.draw_networkx_labels(G, pos, labels)
    plt.show()


class RebuildStateIR(CfgDfs):
    def append(self, node):
        self.parent.value.stmts.append(node)

    def enter_Statement(self, node):
        self.append(node.value)

    # TODO: Why are *Sink nodes defined as statements?
    def enter_BaseBlockSink(self, node):
        pass

    def enter_HDLBlockSink(self, node):
        pass

    def enter_Module(self, block):
        block.value = type(block.value)(states=block.value.states)

    def enter_BaseBlock(self, block):
        block.value = type(block.value)()

    def exit_BaseBlock(self, block):
        if self.scopes:
            self.append(block.value)

    def enter_FuncBlock(self, block):
        irnode = block.value
        block.value = type(irnode)(irnode.args, irnode.name, irnode.ret_dtype)

    def enter_HDLBlock(self, block):
        block.value = type(block.value)()

    def exit_HDLBlock(self, block):
        self.append(block.value)

    def enter_Branch(self, block):
        block.value = type(block.value)(test=block.value.test)

    def exit_Branch(self, block):
        self.parent.value.add_branch(block.value)


class LoopBreaker(CfgDfs):
    def __init__(self, ctx, loops):
        self.ctx = ctx
        self.loops = loops
        super().__init__()

    def LoopBlock(self, node):
        skip = self.enter(node)
        if not skip:
            self.scopes.append(node)
            self.visit(node.next[0])
            self.scopes.pop()

        self.exit(node)

        return self.visit(node.next[0])

    # TODO: How to detect registers used uninitialized?
    def enter_LoopBlock(self, node):
        test = node.value.test
        loop_block = node.value
        node.value = ir.LoopBody(state_id=len(self.loops) + 1)
        jump = Node(ir.Jump('state', len(self.loops) + 1))

        self.loops.append(node)
        insert_node_before(node.sink, jump)
        cond_wrap(jump, jump, test)

        sink_id = id(node.sink.value)
        self.ctx.reaching[id(node.value)] = self.ctx.reaching.get(id(loop_block), None)
        self.ctx.reaching[id(jump.value)] = self.ctx.reaching.get(sink_id, None)
        self.ctx.reaching[id(jump.prev[0].value)] = self.ctx.reaching.get(sink_id, None)

        node.sink.value = ir.BaseBlockSink()

        loop_exit = node.next[1]
        loop_entry = node.prev[0]

        node.prev = [loop_entry]
        loop_entry.next = [node]
        node.next = [node.next[0]]

        node.sink.next = [loop_exit]
        loop_exit.prev = [node.sink]


class LoopLocality(CfgDfs):
    def __init__(self, ctx, loop, reaching_nodes):
        self.ctx = ctx
        self.loop = loop
        self.non_local = False
        self.reaching_nodes = set()
        self.loop_setup_vars = set()
        for n in reaching_nodes[self.loop]['in']:
            v = VariableFinder()
            v.visit(n.value)

            self.loop_setup_vars |= v.variables

        self.within = False
        super().__init__()

    def enter_LoopBody(self, node):
        if node is self.loop:
            self.within = True

    def exit_LoopBody(self, node):
        if node is self.loop:
            # TODO: We could exit immediatelly with exception
            self.within = False

    def enter_AssignValue(self, node):
        if self.within:
            # Node within the Loop influences statements before the loop entry.
            # This loop cannot be easily overlapped with base state
            if any(name in self.loop_setup_vars
                   for name, _ in self.ctx.reaching[id(node.value)]['gen']):
                # TODO: We could exit immediatelly with exception
                self.non_local = True


class StateIsolator(CfgDfs):
    def __init__(self, ctx, entry=None, exits=None, state_num=None):
        super().__init__()
        self.entry = entry
        if exits is None:
            exits = {}
        self.state_num = state_num
        self.exits = exits
        self.ctx = ctx
        self.node_map = {}
        self.entry_scope = None
        self.isolated = None
        self.reaching = self.ctx.reaching
        self.cpmap = {}

    def copy(self, node):
        source = self.node_map.get(node.source, None)

        cp_val = copy(node.value)

        cp_node = Node(cp_val, source=source)
        self.cpmap[node] = cp_node

        self.node_map[node] = cp_node
        cp_node.prev = [self.node_map[p] for p in node.prev if p in self.node_map]

        for n in cp_node.prev:
            n.next.append(cp_node)

        # TODO: find different way to do this, too coupled
        if id(node.value) in self.reaching:
            self.reaching[id(cp_val)] = self.reaching[id(node.value)]
        else:
            for p in cp_node.prev:
                if id(p.value) in self.reaching:
                    self.reaching[id(cp_val)] = self.reaching[id(p.value)]

        return cp_node

    def enter_BaseBlock(self, node):
        self.enter_Statement(node)

    def enter_ModuleSink(self, node):
        sink = Node(ir.ModuleSink(), prev=[node.prev[0]])
        sink = self.copy(sink)
        sink.source = self.isolated
        sink.source.sink = sink

    def enter_HDLBlockSink(self, node):
        if node.source in self.cpmap:
            self.copy(node)
        else:
            for p in node.prev:
                if p in self.node_map:
                    self.node_map[node] = self.node_map[p]

    def enter_BranchSink(self, node):
        if node.source in self.cpmap:
            self.copy(node)
        else:
            for p in node.prev:
                if p in self.node_map:
                    self.node_map[node] = self.node_map[p]

    def enter_Module(self, node):
        pass

    def enter_Statement(self, node):
        if not self.cpmap:
            if self.entry is not None:
                if node.value is not self.entry and node is not self.entry:
                    return

            self.isolated = Node(ir.Module())
            # TODO: Find better way to detect when ir.Module is entry point for isolation
            if self.entry is None and isinstance(node.prev[0].value, ir.Module):
                # node.prev[0] is ir.Module
                self.isolated.value.states = node.prev[0].value.states[:]

            self.entry = node

        if node in self.exits:
            prev = node.prev[0]
            cp_prev = self.node_map[prev]
            cp_prev.next.clear()

            test = self.exits[node]
            # exit_jump = Node(ir.AssignValue(self.ctx.ref('_state'), ir.ResExpr(self.state_num)))
            # break_stmt = Node(ir.Await(ir.res_false), prev=[exit_jump])
            return_stmt = Node(ir.Jump('state', self.state_num))
            self.state_num += 1

            if test == ir.res_true:
                return_stmt.prev = [prev]
                return_stmt = self.copy(return_stmt)
                self.node_map[self.parent.sink.prev[0]] = return_stmt
                return True

            cond_blk = Node(ir.HDLBlock(), prev=[prev])
            if_branch = Node(ir.Branch(test=test), prev=[cond_blk])
            return_stmt.prev = [if_branch]
            if_sink = Node(ir.BranchSink(), source=if_branch, prev=[return_stmt])

            else_branch = Node(ir.Branch(), prev=[cond_blk])
            else_sink = Node(ir.BranchSink(), source=else_branch, prev=[else_branch])
            cond_sink = Node(ir.HDLBlockSink(), source=cond_blk, prev=[if_sink, else_sink])

            cond_blk = self.copy(cond_blk)

            if_branch = self.copy(if_branch)
            return_stmt = self.copy(return_stmt)
            if_sink = self.copy(if_sink)

            else_branch = self.copy(else_branch)
            else_sink = self.copy(else_sink)

            cond_sink = self.copy(cond_sink)

            self.node_map[node] = cond_sink
            return

        self.copy(node)

        if self.entry is node:
            # When we enter in the middle of the graph for isolation, link to
            # previous node of entry point needs to point to new Module() node
            self.node_map[node].prev = [self.isolated]
            self.isolated.next = [self.node_map[node]]



def isolate(ctx, entry, exits=None, state_num=None):
    v = StateIsolator(ctx, exits=exits, state_num=state_num)
    v.visit(entry)
    return v.isolated


def find_statement_node(cfg, stmt):
    """Given a CFG with outgoing links, create incoming links."""
    seen = set()
    to_see = [cfg]
    while to_see:
        node = to_see.pop()

        if node.value is stmt:
            return node

        seen.add(node)
        for succ in node.next:
            if succ not in seen:
                to_see.append(succ)


def append_state_epilog(cfg, ctx):
    insert_node_before(cfg.sink, Node(ir.Jump('state', 0)))


def prepend_state_prolog(cfg, ctx, in_scope):
    source = cfg
    for name, i in ctx.intfs.items():
        if f'{name}.data' not in in_scope:
            continue

        if i.dtype.direction == 1 and in_scope.get(f'{name}.ready', False):
            continue

        hold = Node(ir.AssignValue(ir.Component(ctx.ref(name), 'data'), in_scope[f'{name}.data']),
                    prev=[source])
        hold.next = source.next

        source.next = [hold]
        hold.next[0].prev = [hold]

        source = hold


def print_cfg_ir(cfg):
    v = RebuildStateIR()
    v.visit(cfg)
    print(cfg.value)


from ..cfg import Forward


class ReachingNodes(Forward):
    """Perform reaching definition analysis.

  Each statement is annotated with a set of (variable, definition) pairs.

  """
    def __init__(self):
        def definition(node, incoming):
            kill = frozenset()
            gen = frozenset((node, node))

            # if isinstance(node.value, ir.BaseBlockSink) and isinstance(
            #         node.source.value, ir.LoopBody):
            #     gen = frozenset((node.source.value.state_id, node.source.value))
            # else:
            #     gen = frozenset()

            return gen, kill

        super(ReachingNodes, self).__init__('definitions', definition)


class Piggyback(CfgDfs):
    def __init__(self, ctx, state_id):
        self.state_id = state_id
        self.ctx = ctx
        super().__init__()

    def within_state(self):
        for s in reversed(self.scopes):
            if isinstance(s.value, ir.LoopBody):
                if s.value.state_id == self.state_id:
                    return True
        else:
            return False

    def enter_RegReset(self, node):
        if self.within_state():
            self.ctx.reset_states[node.value.target.name].add(self.state_id)


class LoopBodyFinder(CfgDfs):
    def __init__(self):
        super().__init__()
        self.loops = {}

    def enter_LoopBody(self, node):
        self.loops[node.value.state_id] = node

def discover_piggieback_states(cfg, ctx, scope_map, state_id, reaching_nodes, state_cfg):
    # cfg_temp = isolate(ctx, cfg)

    v_iso = StateIsolator(ctx)
    v_iso.visit(cfg)
    cfg_temp = v_iso.isolated

    v = ReachingNodes()
    v.visit(cfg_temp)
    reaching_nodes = v.reaching

    v = ExploreState(ctx, scope_map, state_id)
    v.visit(cfg_temp)

    if not v.states:
        return [], []

    if all(s in state_cfg for s in v.states):
        return [], []

    piggy_states = v.states

    v = cfgutil.ReachingDefinitions()
    v.visit(cfg)
    reaching_loops = v.reaching

    v = LoopBodyFinder()
    v.visit(cfg)
    loops = v.loops

    non_local = []
    piggied = []
    for child_state in piggy_states:
        loop_cfg = loops[child_state]

        v = LoopLocality(ctx, v_iso.node_map[loop_cfg], reaching_nodes)
        v.visit(cfg_temp)

        # TODO: Optimization currently disabled for loops with multiple states
        if v.non_local:
            non_local.append(child_state)
            continue

        # TODO: Maybe it should go up the "kill" tree and do this for all nodes?
        for name, in_node in reaching_loops[loop_cfg]['in']:
            if name in ctx.scope and isinstance(ctx.scope[name],
                                                ir.Variable) and not ctx.scope[name].reg:
                continue

            if isinstance(in_node.value, ir.RegReset):
                continue

            # If the register is updated withing the loop
            for out_name, out_node in reaching_loops[loop_cfg.sink]['in']:
                if out_name == name:
                    break

            if in_node is not out_node:
                state_test = ir.BinOpExpr((ctx.ref('_state'), ir.ResExpr(child_state)),
                                          ir.opc.NotEq)
                cond_wrap(in_node, in_node, state_test)

        # state_cfg[child_state] = cfg
        Piggyback(ctx, child_state).visit(cfg)
        piggied.append(child_state)

    return non_local, piggied


def schedule(cfg, ctx):
    ctx.scope['_state'] = ir.Variable(
        '_state',
        val=ir.ResExpr(Uint[1](0)),
        reg=True,
    )

    loops = []
    LoopBreaker(ctx, loops).visit(cfg)

    v = ReachingNodes()
    v.visit(cfg)
    reaching_nodes = v.reaching

    state_cfg = {0: cfg}

    isolated_loops = {}
    for l in loops:
        isolated_loops[l.value.state_id] = isolate(ctx, l)

    state_in_scope = [{} for _ in range(1 + len(loops))]
    piggied = set()
    i = 0
    order = list(state_cfg.keys())
    while i < len(order):
        state_id = order[i]
        cfg = state_cfg[state_id]
        # print(f'[{state_id}]: Scoping')
        new_states = {}
        # print_cfg_ir(cfg)

        if loops:
            non_local, piggied_cur = discover_piggieback_states(cfg, ctx, state_in_scope[state_id],
                                                                state_id, reaching_nodes,
                                                                state_cfg)

        VarScope(ctx, state_in_scope, state_id, new_states).visit(cfg)
        cfg.value.states.append(state_id)

        if loops:
            for nl in non_local:
                state_cfg[nl] = isolated_loops[nl]
                order.insert(i + 1, nl)

            cfg.value.states.extend(piggied_cur)

            piggied.update(piggied_cur)

        state_num = len(state_in_scope) - len(new_states)
        if new_states:
            # print(f'[{state_id}]: Isolating')
            state_cfg[state_id] = isolate(ctx, cfg, exits=new_states, state_num=state_num)

            # draw_scheduled_cfg(state_cfg[state_id], simple=False)
            # print_cfg_ir(state_cfg[state_id])
            for si, ns in enumerate(new_states):
                new_state_id = state_num + si

                # order.insert(i + 1, len(state_cfg))
                # print(f'[{len(state_cfg)}]: Isolating')
                # state_cfg.append(isolate(ctx, ns))

                order.insert(i + 1, new_state_id)
                # print(f'[{len(state_cfg)}]: Isolating')
                state_cfg[new_state_id] = isolate(ctx, ns)
                # draw_scheduled_cfg(state_cfg[new_state_id], simple=False)

        i += 1
        if i == len(order):
            missing = (piggied | state_cfg.keys()) ^ set(range(len(state_in_scope)))
            for s in missing:
                # TODO: Can this really be done after all stmts have been inlined?
                state_cfg[s] = isolated_loops[s]
                order.append(s)

    for i, s in state_cfg.items():
        in_scope = state_in_scope[i]

        # draw_scheduled_cfg(s, simple=True)
        # draw_scheduled_cfg(s, simple=False)
        append_state_epilog(s, ctx)
        prepend_state_prolog(s, ctx, in_scope)
        ResolveBlocking(ctx).visit(s)
        # print_cfg_ir(s)
        RebuildStateIR().visit(s)

        # print(f'------------- State {i} --------------')
        # print_cfg_ir(s)

    states = {i: s.value for i, s in state_cfg.items()}

    for i, s in states.items():
        test = ir.res_false
        for j in s.states:
            state_test = ir.BinOpExpr((ctx.ref('_state'), ir.ResExpr(j)), ir.opc.Eq)
            test = ir.BinOpExpr([test, state_test], ir.opc.Or)

    # state_num = len(states)
    state_num = len(state_in_scope)
    ctx.scope['_state'].val = ir.ResExpr(Uint[bitw(state_num - 1)](0))
    ctx.scope['_state'].dtype = Uint[bitw(state_num - 1)]

    stateblock = ir.HDLBlock()
    for i, s in states.items():
        test = ir.res_false
        for j in s.states:
            state_test = ir.BinOpExpr((ctx.ref('_state'), ir.ResExpr(j)), ir.opc.Eq)
            test = ir.BinOpExpr([test, state_test], ir.opc.Or)

        stateblock.add_branch(ir.Branch(stmts=s.stmts, test=test))

    modblock = ir.Module(stmts=[stateblock])

    return modblock
