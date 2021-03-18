from queue import Queue
import attr
import inspect
from contextlib import contextmanager
from copy import deepcopy, copy
from ..cfg import Node
from ..ir_utils import res_true, HDLVisitor, ir, add_to_list, res_false, is_intf_id
from pygears.typing import bitw, Uint, Bool
from .loops import infer_cycle_done


class PPrinter(HDLVisitor):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.msg = ''
        self.indent = 0

    def enter_block(self, node):
        self.write_line(f'{type(node).__name__} {node.state}')
        self.indent += 4

    def exit_block(self):
        self.indent -= 4

    def write_line(self, line):
        self.msg += f'{" "*self.indent}{line}\n'

    def HDLBlock(self, node):
        self.enter_block(node)

        for stmt in node.stmts:
            self.visit(stmt)

        self.exit_block()

        return self.msg

    def generic_visit(self, node):
        self.write_line(f'{type(node).__name__} {node.state}')
        return self.msg


@attr.s(auto_attribs=True)
class SchedStatus:
    forward_blocked: bool = False
    back_blocked: bool = False
    output_value: set = attr.Factory(set)
    cur_state: int = 0

    def copy(self):
        return deepcopy(self)


class Scheduler(HDLVisitor):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.scope = []
        self.path = []
        self.max_state = 0
        self.status = SchedStatus()

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def new_state(self):
        self.max_state += 1
        self.status = SchedStatus(cur_state=self.max_state)
        return self.max_state

    @property
    def parent(self):
        if self.scope:
            return self.scope[-1]
        else:
            return None

    def traverse_block(self, node):
        init_state = node.cur_state

        self.enter_block(node)

        for i, stmt in enumerate(node.stmts):
            self.visit(stmt)
            if not isinstance(stmt, ir.HDLBlock):
                if hasattr(stmt, 'state'):
                    node.cur_state = list(stmt.state)[0]
                else:
                    if node.cur_state == init_state:
                        stmt.state = node.state.copy()
                    else:
                        stmt.state = {node.cur_state}

                    if stmt.in_await == res_false:  # await clk()
                        node.cur_state = self.new_state()
                        stmt.state = {node.cur_state}
                    elif stmt.in_await != res_true:
                        self.status.forward_blocked = True
                        if self.status.back_blocked:
                            node.cur_state = self.new_state()
                            stmt.state = {node.cur_state}
                    elif stmt.exit_await != res_true:
                        self.status.back_blocked = True

            node.state.update(stmt.state)

        self.exit_block()

    def HDLBlock(self, node: ir.HDLBlock):
        if self.parent:
            node.cur_state = self.parent.cur_state
        else:
            node.cur_state = 0

        node.state = {node.cur_state}

        self.traverse_block(node)

    def AssignValue(self, node: ir.AssignValue):
        if is_intf_id(node.target):
            if self.status.back_blocked or node.target.name in self.status.output_value:
                node.state = {self.new_state()}

            self.status.output_value.add(node.target.name)

    def IfElseBlock(self, node):
        node.state = {self.parent.cur_state}
        node.cur_state = self.parent.cur_state

        init_state = self.status.copy()

        self.enter_block(node)

        out_states = []

        for stmt in node.stmts:
            self.status = init_state.copy()

            self.visit(stmt)

            out_states.append(self.status.copy())

            node.state.update(stmt.state)

        self.exit_block()


class StateIsolator(HDLVisitor):
    def __init__(self, ctx, state_id):
        super().__init__(ctx)
        self.state_id = state_id
        self.cur_state_id = 0

    @property
    def cur_state(self):
        return self.cur_state_id == self.state_id

    def traverse_block(self, all_stmts, state):
        self.cur_state_id = list(state)[0]
        stmts = []

        for stmt in all_stmts:
            if self.state_id in stmt.state:
                if self.cur_state_id not in stmt.state:
                    self.cur_state_id = list(stmt.state)[0]

                add_to_list(stmts, self.visit(stmt))
            elif self.cur_state:
                stmts.append(
                    ir.AssignValue(self.ctx.ref('_state', ctx='store'),
                                   ir.Await(ir.ResExpr(list(stmt.state)[0]), exit_await=res_false)))
                break

        if self.cur_state_id not in state:
            self.cur_state_id = list(state)[0]

        return stmts

    def ExprStatement(self, node: ir.ExprStatement):
        # TODO: Make this more general, now it convers the case of "await
        # clk()" like this
        if node.in_await != res_false:
            return node

    def HDLBlock(self, node):
        if self.state_id not in node.state:
            return None

        if len(node.state) == 1:
            return node

        in_cond = node.in_cond if self.cur_state else res_true
        exit_cond = node.exit_cond

        stmts = self.traverse_block(node.stmts, node.state)

        if in_cond == res_true and exit_cond == res_true:
            return stmts

        if in_cond == res_true and exit_cond == res_true and not stmts:
            return None

        return ir.HDLBlock(in_cond=in_cond, exit_cond=exit_cond, stmts=stmts)

    def LoopBlock(self, node):
        if self.state_id not in node.state:
            return None

        if len(node.state) == 1:
            return node

        block = ir.LoopBlock(in_cond=node.in_cond if self.cur_state else res_true,
                             exit_cond=node.exit_cond,
                             stmts=self.traverse_block(node.stmts, node.state))

        if '_state' in self.ctx.scope:
            if (self.cur_state and self.state_id != list(node.state)[0]):
                # and node.out_blocking):

                block.stmts.append(
                    ir.AssignValue(self.ctx.ref('_state', ctx='store'),
                                   ir.Await(ir.ResExpr(list(node.state)[0]), exit_await=res_false)))
        return block

    def IfElseBlock(self, node):
        block = ir.IfElseBlock(stmts=[])

        for stmt in node.stmts:
            sub_stmts = self.visit(stmt)
            if isinstance(sub_stmts, list):
                if len(block.stmts) != 0:
                    # traverse_block logic stripped the HDLBlock from else
                    # path, we need it back
                    block.stmts.append(ir.HDLBlock(stmts=sub_stmts))
                else:
                    return sub_stmts
            else:
                add_to_list(block.stmts, sub_stmts)

        if len(block.stmts) == 1:
            return block.stmts[0]

        return block


class SkipBranch(Exception):
    pass


def create_scheduled_cfg(node, G, visited, labels):
    if node in visited:
        return

    visited.add(node)
    if node.value is None:
        labels[id(node)] = "None"
    elif isinstance(node.value, ir.BaseBlock):
        labels[id(node)] = f'{type(node.value)}'
    else:
        labels[id(node)] = str(node.value)

    for n in node.next:
        G.add_edge(id(node), id(n))

        create_scheduled_cfg(n, G, visited, labels)


def draw_scheduled_cfg(cfg):
    import networkx as nx
    import matplotlib.pyplot as plt

    G = nx.DiGraph()
    visited = set()
    labels = {}

    create_scheduled_cfg(cfg, G, visited, labels)

    pos = nx.planar_layout(G)
    nx.draw(G, pos, font_size=16, with_labels=False)

    # for p in pos:  # raise text positions
    #     pos[p][1] += 0.07

    nx.draw_networkx_labels(G, pos, labels)
    plt.show()


class RebuildStateIR:
    def __init__(self, ctx):
        self.ctx = ctx
        self.scope = [ir.HDLBlock()]
        self.queue = Queue()
        self.visited = set()
        self.sink = None

    @property
    def parent(self):
        return self.scope[-1]

    def append(self, node):
        self.parent.stmts.append(node)

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def visit(self, node):
        for base_class in inspect.getmro(node.value.__class__):
            if hasattr(self, base_class.__name__):
                self.visited.add(node)
                return getattr(self, base_class.__name__)(node)
        else:
            return self.generic_visit(node)

    def HDLBlock(self, node):
        if node.value.in_cond == ir.res_true:
            return self.generic_visit(node)

        blocks = []
        for n in node.next:
            if isinstance(n.value, ir.HDLBlockSink):
                continue

            ir_node = ir.HDLBlock(in_cond=ir.res_true, stmts=[])
            self.enter_block(ir_node)
            self.visit(n)
            self.exit_block()
            blocks.append(ir_node)

        blocks[0].in_cond = node.value.in_cond

        if len(blocks) == 1:
            self.append(blocks[0])
        else:
            self.append(ir.IfElseBlock(stmts=blocks))

        for n in node.sink.next:
            self.visit(n)

    def IfElseBlock(self, node: ir.IfElseBlock):
        breakpoint()

    def HDLBlockSink(self, node: ir.HDLBlockSink):
        return

    def LoopBlockSink(self, node: ir.LoopBlockSink):
        return self.generic_visit(node)

    def Statement(self, node: ir.Statement):
        self.append(node.value)
        for n in node.next:
            self.visit(n)

    def generic_visit(self, node):
        for n in node.next:
            self.visit(n)


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
        self.add_state(node.next[0])

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
        # for i, p in enumerate(node.prev):
        #     if isinstance(node.value, ir.LoopBlock) and i > 0:
        #         continue

        #     if p not in self.state_map:
        #         return

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
            stmt = ir.AssignValue(self.ctx.ref('_state'), ir.ResExpr(node.value.looped_state))
            stmt.exit_cond = ir.res_false
            state_node = Node(stmt, prev=[cond])

            self.append(state_node)
            sink_node = Node(ir.HDLBlockSink(), source=cond, prev=[state_node, cond])
            self.append(sink_node)
            self.state_map[node.sink] = sink_node
            self.schedule(nexit)
        else:
            stmt = ir.AssignValue(self.ctx.ref('_state'), ir.ResExpr(node.value.looped_state))
            stmt.exit_cond = ir.res_false
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


def schedule(block, cfg, ctx):
    # ctx.scope['_rst_cond'] = ir.Variable('_rst_cond', Bool)
    # block.stmts.insert(0, ir.AssignValue(ctx.ref('_rst_cond', 'store'), res_false))

    # block.stmts.append(ir.AssignValue(ctx.ref('_rst_cond', 'store'), res_true))

    ctx.scope['_state'] = ir.Variable(
        '_state',
        val=ir.ResExpr(Uint[1](0)),
        reg=True,
    )

    v = ScheduleBFS(ctx)
    v.bfs(cfg)

    # draw_scheduled_cfg(v.state_entry[0])
    # draw_scheduled_cfg(v.state_entry[1])

    states = []
    for n in v.state_entry:
        v = RebuildStateIR(ctx)
        v.visit(n)
        states.append(v.parent)
        print(v.parent)

    # Scheduler(ctx).visit(block)
    # print('*** Schedule ***')
    # print(PPrinter(ctx).visit(block))
    # state_num = len(block.state)
    state_num = len(states)
    ctx.scope['_state'].val = ir.ResExpr(Uint[bitw(state_num - 1)](0))

    stateblock = ir.IfElseBlock(stmts=[])
    for i, res in enumerate(states):
        # v = StateIsolator(ctx, i)
        # res = v.visit(block)
        # if isinstance(res, list):
        #     res = ir.HDLBlock(stmts=res)

        res.exit_cond = res_false

        stateblock.stmts.append(res)

        if state_num > 1:
            res.in_cond = ir.BinOpExpr((ctx.ref('_state'), ir.ResExpr(i)), ir.opc.Eq)

    if state_num > 1:
        modblock = ir.CombBlock(stmts=[stateblock])
    else:
        modblock = ir.CombBlock(stmts=stateblock.stmts[0].stmts)

    # modblock = infer_cycle_done(modblock, ctx)

    return modblock
