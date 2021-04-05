from queue import Queue
import attr
import inspect
from .. import cfg as cfgutil
from contextlib import contextmanager
from copy import deepcopy, copy
from ..cfg import Node, draw_cfg, CfgDfs, ReachingDefinitions
from ..ir_utils import res_true, HDLVisitor, ir, add_to_list, res_false, is_intf_id, IrRewriter
from pygears.typing import bitw, Uint, Bool
from .loops import infer_cycle_done
from .inline_cfg import VarScope
from .exit_cond_cfg import ResolveBlocking


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

    def enter_BaseBlock(self, block):
        block.value = type(block.value)()

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


class ScheduleBFS:
    def __init__(self, ctx):
        self.state = -1
        self.max_state = 0
        self.ctx = ctx
        self.state_entry = []
        self.state_stmts = []
        self.state_maps = []
        self.visited = set()

    def bfs(self, node):
        self.queue = Queue()
        self.add_state(node)

        while self.state < len(self.state_entry) - 1:
            self.state += 1
            self.queue.put(self.state_entry[self.state])
            self.visited.clear()
            while not self.queue.empty():
                self.visit(self.queue.get())

        self.state_entry = [m[e] for m, e in zip(self.state_maps, self.state_entry)]

    @property
    def state_map(self):
        return self.state_maps[self.state]

    def add_state(self, node):
        self.state_maps.append({})
        self.state_entry.append(node)
        return len(self.state_maps) - 1

    def change_state(self, state=None):
        if state is None:
            self.state += 1
            self.state_maps.append({})
        else:
            self.state = state

    def schedule(self, node):
        self.queue.put(node)

    def copy(self, node):
        if node not in self.state_map:
            source = self.state_map.get(node.source, None)

            cp_node = Node(node.value, source=source)
            self.state_map[node] = cp_node
            cp_node.prev = [self.state_map[p] for p in node.prev if p in self.state_map]
        else:
            cp_node = node

        self.append(cp_node)

        return cp_node

    def append(self, node):
        for n in node.prev:
            n.next.append(node)

        if len(self.state_entry) <= self.state:
            self.state_entry.append(node)

        return node

    @property
    def next_state(self):
        return len(self.state_entry)

    def set_state(self, state):
        self.state = state

    def visit(self, node):
        self.visited.add(node)
        for base_class in inspect.getmro(node.value.__class__):
            if hasattr(self, base_class.__name__):
                return getattr(self, base_class.__name__)(node)
        else:
            return self.generic_visit(node)

    def LoopBlock(self, node):
        nloop, nexit = node.next
        nprev, nsink = node.prev

        second_state = getattr(node.value, 'state', self.state) != self.state
        second_loop = second_state or node in self.state_map

        orig = None
        if second_loop:
            if not second_state:
                orig = self.state_map[node]

            prev = [self.state_map[nsink]]
        else:
            prev = [self.state_map[nprev]]

        cond = Node(ir.HDLBlock(in_cond=node.value.in_cond), prev=prev)
        self.state_map[node] = cond
        self.append(cond)

        if not second_loop:
            self.schedule(nexit)
            self.schedule(nloop)
            node.value.state = self.state
            node.value.looped_state = self.add_state(nloop)
        elif second_state:
            stmt = ir.AssignValue(self.ctx.ref('_state'),
                                  ir.ResExpr(node.value.looped_state),
                                  exit_await=ir.res_false)
            state_node = Node(stmt, prev=[cond])

            self.append(state_node)
            sink_node = Node(ir.HDLBlockSink(), source=cond, prev=[state_node, cond])
            self.append(sink_node)
            self.state_map[node.sink] = sink_node
            self.schedule(nexit)
        else:
            stmt = ir.AssignValue(self.ctx.ref('_state'),
                                  ir.ResExpr(node.value.looped_state),
                                  exit_await=ir.res_false)
            state_node = Node(stmt, prev=[cond])

            self.append(state_node)
            sink_node = Node(ir.HDLBlockSink(),
                             source=cond,
                             prev=[state_node, cond],
                             next_=[orig.sink])
            self.append(sink_node)
            orig.sink.prev.append(sink_node)

    def HDLBlockSink(self, node: ir.LoopBlockSink):
        if not all(p in self.visited for p in node.prev):
            return

        self.copy(node)
        for n in node.next:
            self.schedule(n)

    def generic_visit(self, node):
        self.copy(node)
        for n in node.next:
            self.schedule(n)


class LoopBreaker(IrRewriter):
    def __init__(self, loops, cpmap, ctx):
        self.loops = loops
        self.ctx = ctx
        super().__init__(cpmap)

    def LoopBlock(self, block: ir.LoopBlock):
        body = ir.Branch(test=block.test)

        for stmt in block.stmts:
            add_to_list(body.stmts, self.visit(stmt))

        cond_enter_blk = ir.HDLBlock(branches=[body])

        transition = ir.Branch(test=block.test)
        jump = ir.AssignValue(self.ctx.ref('_state'), ir.ResExpr(len(self.loops) + 1))
        breakstmt = ir.Await(ir.res_false)
        cond_exit_blk = ir.HDLBlock(branches=[transition])

        # TODO: out -> in, not just copy
        self.cpmap[id(transition)] = block.stmts[-1]
        self.cpmap[id(jump)] = block.stmts[-1]
        self.cpmap[id(breakstmt)] = block.stmts[-1]
        self.cpmap[id(cond_exit_blk)] = block.stmts[-1]

        transition.stmts.extend([jump, breakstmt])

        self.loops.append(cond_enter_blk)

        body.stmts.append(cond_exit_blk)

        return cond_enter_blk


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
        # if str(node.value) == "din.ready <= u1(1)\n":
        #     breakpoint()

        source = self.node_map.get(node.source, None)

        cp_val = copy(node.value)

        cp_node = Node(cp_val, source=source)
        self.cpmap[node] = cp_node

        self.node_map[node] = cp_node
        cp_node.prev = [self.node_map[p] for p in node.prev if p in self.node_map]

        for n in cp_node.prev:
            if (str(n.value) == "dout <= (u4)'(u3(4))\n") and (n.next):
                breakpoint()

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

            self.entry = node
            self.isolated = Node(ir.Module())
            self.node_map[node.prev[0]] = self.isolated

        if node in self.exits:
            prev = node.prev[0]
            cp_prev = self.node_map[prev]
            cp_prev.next.clear()

            test = self.exits[node]
            exit_jump = Node(ir.AssignValue(self.ctx.ref('_state'), ir.ResExpr(self.state_num)))
            break_stmt = Node(ir.Await(ir.res_false), prev=[exit_jump])
            self.state_num += 1

            if test == ir.res_false:
                exit_jump.prev = [prev]
                exit_jump = self.copy(exit_jump)
                break_stmt = self.copy(break_stmt)
                self.node_map[self.parent.sink.prev[0]] = break_stmt
                return True

            cond_blk = Node(ir.HDLBlock(), prev=[prev])
            if_branch = Node(ir.Branch(test=ir.UnaryOpExpr(test, ir.opc.Not)), prev=[cond_blk])
            exit_jump.prev = [if_branch]
            if_sink = Node(ir.BranchSink(), source=if_branch, prev=[break_stmt])

            else_branch = Node(ir.Branch(), prev=[cond_blk])
            else_sink = Node(ir.BranchSink(), source=else_branch, prev=[else_branch])
            cond_sink = Node(ir.HDLBlockSink(), source=cond_blk, prev=[if_sink, else_sink])

            cond_blk = self.copy(cond_blk)

            if_branch = self.copy(if_branch)
            exit_jump = self.copy(exit_jump)
            break_stmt = self.copy(break_stmt)
            if_sink = self.copy(if_sink)

            else_branch = self.copy(else_branch)
            else_sink = self.copy(else_sink)

            cond_sink = self.copy(cond_sink)

            self.node_map[node] = cond_sink
            return

        self.copy(node)

        # if self.scopes and ((self.parent in self.node_map) or (self.parent is self.entry_scope)):
        #     self.copy(node)
        # else:
        #     for p in node.prev:
        #         if p in self.node_map:
        #             self.node_map[node] = self.node_map[p]


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
    sink = cfg.sink

    exit_jump = Node(
        ir.AssignValue(ctx.ref('_state'), ir.ResExpr(0)),
        prev=[sink.prev[0]],
    )
    break_stmt = Node(ir.Await(ir.res_false), prev=[exit_jump])
    cp_sink = Node(ir.ModuleSink(), prev=[break_stmt], source=cfg)
    sink.prev[0].next = [exit_jump]
    exit_jump.next = [break_stmt]
    break_stmt.next = [cp_sink]


def prepend_state_prolog(cfg, ctx, in_scope):
    source = cfg
    for name, i in ctx.intfs.items():
        if f'{name}.data' not in in_scope:
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


def schedule(block, ctx):
    ctx.scope['_state'] = ir.Variable(
        '_state',
        val=ir.ResExpr(Uint[1](0)),
        reg=True,
    )

    loops = []
    cpmap = {}
    block = LoopBreaker(loops, cpmap, ctx).visit(block)

    cfg = cfgutil.CFG.build_cfg(block)
    # draw_cfg(cfg)

    # draw_scheduled_cfg(cfg.entry, simple=False)

    state_cfg = [cfg.entry]
    for l in loops:
        entry = find_statement_node(cfg.entry, l.branches[0].stmts[0])
        state_cfg.append(isolate(ctx, entry))

    for k, v in cpmap.items():
        ctx.reaching[k] = ctx.reaching.get(id(v), None)

    state_in_scope = [{} for _ in range(len(state_cfg))]
    i = 0
    order = list(range(len(state_cfg)))
    while i < len(order):
        state_id = order[i]
        print(f'[{state_id}]: Scoping')
        new_states = {}
        VarScope(ctx, state_in_scope, state_id, new_states).visit(state_cfg[state_id])
        if new_states:
            print(f'[{state_id}]: Isolating')
            state_cfg[state_id] = isolate(ctx,
                                          state_cfg[state_id],
                                          exits=new_states,
                                          state_num=len(state_cfg))

            print_cfg_ir(state_cfg[state_id])
            for ns in new_states:
                order.insert(i + 1, len(state_cfg))
                print(f'[{len(state_cfg)}]: Isolating')
                state_cfg.append(isolate(ctx, ns))

        i += 1

    for i, (s, in_scope) in enumerate(zip(state_cfg, state_in_scope)):
        # draw_scheduled_cfg(s, simple=True)
        append_state_epilog(s, ctx)
        prepend_state_prolog(s, ctx, in_scope)
        ResolveBlocking().visit(s)
        v = RebuildStateIR()
        v.visit(s)

    states = [s.value for s in state_cfg]
    state_num = len(states)
    ctx.scope['_state'].val = ir.ResExpr(Uint[bitw(state_num - 1)](0))
    ctx.scope['_state'].dtype = Uint[bitw(state_num - 1)]

    if state_num == 1:
        modblock = ir.CombBlock(stmts=states[0].stmts)
    else:
        stateblock = ir.HDLBlock()
        for i, s in enumerate(states):
            test = ir.BinOpExpr((ctx.ref('_state'), ir.ResExpr(i)), ir.opc.Eq)
            stateblock.add_branch(ir.Branch(stmts=s.stmts, test=test))

        modblock = ir.CombBlock(stmts=[stateblock])

    print(modblock)
    return modblock
