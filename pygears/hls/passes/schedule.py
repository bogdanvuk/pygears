from queue import Queue
import attr
import inspect
from .. import cfg as cfgutil
from contextlib import contextmanager
from copy import deepcopy, copy
from ..cfg import Node, draw_cfg, CfgDfs, ReachingDefinitions
from ..cfg_util import insert_node_before, insert_node_after
from ..ir_utils import res_true, HDLVisitor, ir, add_to_list, res_false, is_intf_id, IrRewriter
from pygears.typing import bitw, Uint, Bool
from .inline_cfg import VarScope, JumpScoping
from .exit_cond_cfg import ResolveBlocking, cond_wrap
from ..cfg_util import insert_node_before


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

        breakpoint()
        loop_exit = node.next[1]
        loop_entry = node.prev[0]

        node.prev = [loop_entry]
        loop_entry.next = [node]
        node.next = [node.next[0]]

        node.sink.next = [loop_exit]
        loop_exit.prev = [node.sink]


class LoopBreakerPrev(IrRewriter):
    def __init__(self, loops, cpmap, ctx):
        self.loops = loops
        self.ctx = ctx
        super().__init__(cpmap)

    # def Jump(self, node: ir.Jump):
    #     # # breakpoint()
    #     # if node.label == 'break':
    #     #     node.where = self.loops

    #     return node

    def LoopBlock(self, block: ir.LoopBlock):
        loop = ir.LoopBody(state_id=len(self.loops) + 1)
        # maybe_loop = ir.Branch(test=block.test_in, stmts=[loop])
        # loop = ir.Branch(test=block.test_in)
        # body = ir.LoopBody(state_id=len(self.loops) + 1, test=block.test_in)

        transition = ir.Branch(test=block.test_loop)
        return_stmt = ir.Jump('state', len(self.loops) + 1)
        cond_exit_blk = ir.HDLBlock(branches=[transition])
        # cond_enter_blk = ir.HDLBlock(branches=[maybe_loop])

        self.loops.append(loop)

        for stmt in block.stmts:
            add_to_list(loop.stmts, self.visit(stmt))

        transition.stmts.append(return_stmt)
        loop.stmts.append(cond_exit_blk)

        # TODO: out -> in, not just copy
        self.cpmap[id(transition)] = block.stmts[-1]
        self.cpmap[id(return_stmt)] = block.stmts[-1]
        self.cpmap[id(cond_exit_blk)] = block.stmts[-1]
        # self.cpmap[id(maybe_loop)] = block.stmts[-1]

        return loop


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

            self.entry = node
            self.isolated = Node(ir.Module())
            self.node_map[node.prev[0]] = self.isolated

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
    # sink = cfg.sink

    # source = insert_node_after(cfg, Node(ir.BaseBlock()))
    # insert_node_before(cfg.sink, Node(ir.BaseBlockSink, source=source))
    insert_node_before(cfg.sink, Node(ir.Jump('state', 0)))

    # exit_jump = Node(
    #     ir.AssignValue(ctx.ref('_state'), ir.ResExpr(0)),
    #     prev=[sink.prev[0]],
    # )
    # break_stmt = Node(ir.Await(ir.res_false), prev=[exit_jump])
    # cp_sink = Node(ir.ModuleSink(), prev=[break_stmt], source=cfg)
    # sink.prev[0].next = [exit_jump]
    # exit_jump.next = [break_stmt]
    # break_stmt.next = [cp_sink]


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


def schedule(cfg, ctx):
    ctx.scope['_state'] = ir.Variable(
        '_state',
        val=ir.ResExpr(Uint[1](0)),
        reg=True,
    )

    draw_scheduled_cfg(cfg, simple=False)

    loops = []
    LoopBreaker(ctx, loops).visit(cfg)

    # cfg = cfgutil.CFG.build_cfg(block)
    # draw_cfg(cfg)

    # draw_scheduled_cfg(cfg, simple=False)

    state_cfg = [cfg]
    for l in loops:
        state_cfg.append(isolate(ctx, l))

    # draw_scheduled_cfg(state_cfg[1], simple=False)

    # for k, v in cpmap.items():
    #     ctx.reaching[k] = ctx.reaching.get(id(v), None)

    state_in_scope = [{} for _ in range(len(state_cfg))]
    i = 0
    order = list(range(len(state_cfg)))
    while i < len(order):
        state_id = order[i]
        print(f'[{state_id}]: Scoping')
        new_states = {}
        # print_cfg_ir(state_cfg[state_id])
        # breakpoint()
        VarScope(ctx, state_in_scope, state_id, new_states).visit(state_cfg[state_id])
        if new_states:
            print(f'[{state_id}]: Isolating')
            state_cfg[state_id] = isolate(ctx,
                                          state_cfg[state_id],
                                          exits=new_states,
                                          state_num=len(state_cfg))

            # draw_scheduled_cfg(state_cfg[state_id], simple=False)
            # print_cfg_ir(state_cfg[state_id])
            for ns in new_states:
                order.insert(i + 1, len(state_cfg))
                print(f'[{len(state_cfg)}]: Isolating')
                state_cfg.append(isolate(ctx, ns))
                # draw_scheduled_cfg(state_cfg[-1], simple=False)

        i += 1

    for i, (s, in_scope) in enumerate(zip(state_cfg, state_in_scope)):
        # print_cfg_ir(s)
        # draw_scheduled_cfg(s, simple=True)
        # draw_scheduled_cfg(s, simple=False)
        # breakpoint()
        append_state_epilog(s, ctx)
        prepend_state_prolog(s, ctx, in_scope)
        ResolveBlocking(ctx).visit(s)
        # print_cfg_ir(s)
        # JumpScoping(ctx).visit(s)
        RebuildStateIR().visit(s)

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
