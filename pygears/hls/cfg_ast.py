# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
#            Unless required by applicable law or agreed to in writing, software
#            distributed under the License is distributed on an "AS IS" BASIS,
#            WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#            See the License for the specific language governing permissions and
#            limitations under the License.
"""Control flow graph analysis.

Given a Python AST we construct a doubly linked control flow graph whose nodes
contain the AST of the statements. We can then perform forward analysis on this
CFG.

"""
from collections import Counter
import inspect
import functools
import operator
from copy import copy
from queue import Queue

import ast as gast

LITERALS = (gast.Num, gast.Str, gast.Bytes, gast.Ellipsis, gast.NameConstant)

CONTROL_FLOW = (gast.For, gast.AsyncFor, gast.While, gast.If, gast.Try, gast.Break, gast.Continue,
                gast.With, gast.AsyncWith)

COMPOUND_STATEMENTS = (gast.FunctionDef, gast.ClassDef, gast.For, gast.While, gast.If, gast.With,
                       gast.Try, gast.AsyncFunctionDef, gast.AsyncFor, gast.AsyncWith)

SIMPLE_STATEMENTS = (gast.Return, gast.Delete, gast.Assign, gast.AugAssign, gast.Raise, gast.Assert,
                     gast.Import, gast.ImportFrom, gast.Global, gast.Nonlocal, gast.Expr, gast.Pass,
                     gast.Break, gast.Continue)

STATEMENTS = COMPOUND_STATEMENTS + SIMPLE_STATEMENTS

BLOCKS = (
    (gast.Module, 'body'),
    (gast.FunctionDef, 'body'),
    (gast.AsyncFunctionDef, 'body'),
    (gast.For, 'body'),
    (gast.For, 'orelse'),
    (gast.AsyncFor, 'body'),
    (gast.AsyncFor, 'orelse'),
    (gast.While, 'body'),
    (gast.While, 'orelse'),
    (gast.If, 'body'),
    (gast.If, 'orelse'),
)


def get_name(node):
    """Get the name of a variable.
    Args:
        node: A `Name`, `Subscript` or `Attribute` node.
    Returns:
        The name of the variable e.g. `'x'` for `x`, `x.i` and `x[i]`.
    """
    if isinstance(node, gast.Name):
        return node.id
    elif isinstance(node, (gast.Subscript, gast.Attribute)):
        return get_name(node.value)
    else:
        raise TypeError


def _get_target(node):
    if isinstance(node, (gast.Name, gast.Subscript, gast.Attribute)):
        return set([get_name(node)])
    elif isinstance(node, (gast.Tuple, gast.List)):
        return set.union(*(_get_target(target) for target in node.elts))
    else:
        raise ValueError


def get_updated(node):
    """Return the variable names created or mutated by this statement.
    This function considers assign statements, augmented assign statements, and
    the targets of for loops, as well as function arguments.
    For example, `x[0] = 2` will return `x`, `x, y = 3, 4` will return `x` and
    `y`, `for i in range(x)` will return `i`, etc.
    Args:
        node: An AST node
    Returns:
        A set of variable names (strings) of all the variables created or mutated.
    """
    if isinstance(node, gast.Assign):
        return set.union(*(_get_target(target) for target in node.targets))
    elif isinstance(node, (gast.For, gast.AugAssign)):
        return _get_target(node.target)
    elif isinstance(node, gast.AsyncWith):
        return set.union(*(_get_target(target.optional_vars) for target in node.items))
    elif isinstance(node, gast.AsyncFor):
        return _get_target(node.target)
    elif isinstance(node, gast.With):
        breakpoint()
    elif isinstance(node, gast.arguments):
        targets = set(arg.arg for arg in node.args + node.kwonlyargs)
        if node.vararg:
            targets.add(node.vararg.arg)
        if node.kwarg:
            targets.add(node.kwarg.arg)
        return targets
    else:
        return set()


class Loop(gast.AST):
    pass


class Node(object):
    """A node in the CFG."""
    __slots__ = ['next', 'value', 'prev', 'loop']

    def __init__(self, value, loop=False):
        self.loop = loop
        self.next = []
        self.prev = []
        self.value = value


class CFG(gast.NodeVisitor):
    """Construct a control flow graph.

    Each statement is represented as a node. For control flow statements such
    as conditionals and loops the conditional itself is a node which either
    branches or cycles, respectively.

    Attributes:
        entry: The entry node, which contains the `gast.arguments` node of the
                function definition.
        exit: The exit node. This node is special because it has no value (i.e. no
                corresponding AST node). This is because Python functions can have
                multiple return statements.
    """
    def __init__(self):
        # The current leaves of the CFG
        self.head = []
        # A stack of continue statements
        self.continue_ = []
        # A stack of break nodes
        self.break_ = []

    @staticmethod
    def backlink(node):
        """Given a CFG with outgoing links, create incoming links."""
        seen = set()
        to_see = [node]
        while to_see:
            node = to_see.pop()
            seen.add(node)
            for succ in node.next:
                succ.prev.append(node)
                if succ not in seen:
                    to_see.append(succ)

    def set_head(self, node):
        """Link this node to the current leaves."""
        for head in self.head:
            head.next.append(node)
        self.head[:] = []
        self.head.append(node)

    @classmethod
    def build_cfg(cls, node):
        """Build a CFG for a function.

        Args:
            node: A function definition the body of which to analyze.

        Returns:
            A CFG object.

        Raises:
            TypeError: If the input is not a function definition.
        """
        if not isinstance(node, (gast.FunctionDef, gast.AsyncFunctionDef, gast.Lambda)):
            breakpoint()
            raise TypeError('input must be a function definition')
        cfg = cls()
        cfg.entry = Node(node.args)
        cfg.head = [cfg.entry]
        cfg.visit_statements(node.body)
        cfg.exit = Node(None)
        cfg.set_head(cfg.exit)
        cfg.backlink(cfg.entry)
        return cfg

    def visit_statements(self, nodes):
        for node in nodes:
            if isinstance(node, CONTROL_FLOW):
                self.visit(node)
            else:
                expr = Node(node)
                self.set_head(expr)

    def generic_visit(self, node):
        raise ValueError('unknown control flow')

    def visit_If(self, node):
        # The current head will hold the conditional
        test = Node(node.test)
        self.set_head(test)
        # Handle the body
        self.visit_statements(node.body)
        body_exit = self.head[:]
        self.head[:] = []
        self.head.append(test)
        # Handle the orelse
        self.visit_statements(node.orelse)
        self.head.extend(body_exit)

    def visit_AsyncWith(self, node):
        # The current head will hold the conditional
        test = Node(node)
        self.set_head(test)
        # Handle the body
        self.visit_statements(node.body)

    visit_With = visit_AsyncWith

    def Loop(self, body, orelse, test):
        test = Node(test)
        self.set_head(test)
        loop = Node(Loop())
        self.set_head(loop)
        # Start a new level of nesting
        self.break_.append([])
        self.continue_.append([])
        # Handle the body
        self.visit_statements(body)
        self.head.extend(self.continue_.pop())

        test_exit = Node(copy(test.value))
        self.set_head(test_exit)
        self.set_head(loop)
        # test.next[0].loop = True
        # Handle the orelse
        self.visit_statements(orelse)
        # The break statements and the test go to the next node
        self.head = [test, test_exit]
        self.head.extend(self.break_.pop())

    def visit_While(self, node):
        self.Loop(node.body, node.orelse, node.test)

    def visit_AsyncFor(self, node):
        self.Loop(node.body, node.orelse, node.iter)

    def visit_For(self, node):
        self.Loop(node.body, node.orelse, node.iter)

    def visit_Break(self, node):
        self.break_[-1].extend(self.head)
        self.head[:] = []

    def visit_Continue(self, node):
        self.continue_[-1].extend(self.head)
        self.head[:] = []

    def visit_Try(self, node):
        self.visit_statements(node.body)
        body = self.head
        handlers = []
        for handler in node.handlers:
            self.head = body[:]
            self.visit_statements(handler.body)
            handlers.extend(self.head)
        self.head = body
        self.visit_statements(node.orelse)
        self.head = handlers + self.head
        self.visit_statements(node.finalbody)


def _loops_on_self_rec(start_node, cur_node, reaching):
    if cur_node not in reaching:
        return False

    names = [v[0] for v in reaching[start_node]['gen']]
    for name, in_node in reaching[cur_node]['in']:
        if in_node is cur_node:
            continue

        if name in names:
            if in_node is start_node:
                return True

            if _loops_on_self_rec(start_node, in_node, reaching):
                return True

    return False


def loops_on_self(node, reaching):
    return _loops_on_self_rec(node, node, reaching)


class Forward(object):
    """Forward analysis on CFG.

  Args:
    label: A name for this analysis e.g. 'active' for activity analysis. The
        AST nodes in the CFG will be given annotations 'name_in', 'name_out',
        'name_gen' and 'name_kill' which contain the incoming values, outgoing
        values, values generated by the statement, and values deleted by the
        statement respectively.
    gen: A function which takes the CFG node as well as a set of incoming
        values. It must return a set of newly generated values by the statement
        as well as a set of deleted (killed) values.
    op: Either the AND or OR operator. If the AND operator is used it turns
        into forward must analysis (i.e. a value will only be carried forward
        if it appears on all incoming paths). The OR operator means that
        forward may analysis is done (i.e. the union of incoming values will be
        taken).
  """
    def __init__(self, label, gen, op=operator.or_):
        self.gen = gen
        self.op = op
        self.out_label = label + '_out'
        self.in_label = label + '_in'
        self.gen_label = label + '_gen'
        self.kill_label = label + '_kill'
        self.reaching = {}
        self.registers = set()

    def visit(self, node):
        if node not in self.reaching:
            self.reaching[node] = {}

        reaching = self.reaching[node]

        if node.value:
            if 'out' in reaching:
                in_before = reaching['in']
            else:
                in_before = None

            preds = [
                self.reaching[pred]['out'] for pred in node.prev
                if 'out' in self.reaching.get(pred, {})
            ]
            if preds:
                incoming = functools.reduce(self.op, preds[1:], preds[0])
            else:
                incoming = frozenset()

            reaching['in'] = incoming
            gen, kill = self.gen(node, incoming)
            reaching['gen'] = gen
            reaching['kill'] = kill
            reaching['out'] = (incoming - kill) | gen

            if reaching['in'] != in_before:
                for succ in node.next:
                    self.visit(succ)
        else:
            preds = [
                self.reaching[pred]['out'] for pred in node.prev
                if 'out' in self.reaching.get(pred, {})
            ]
            self.exit = functools.reduce(self.op, preds[1:], preds[0])


class InferRegisters:
    def __init__(self, reaching):
        self.reaching = reaching
        self.visited = set()
        self.registers = set()

    def visit(self, node):
        if node in self.visited:
            return

        if isinstance(node.value, Loop):
            # Check if any of the variables are conditionaly changed (i.e.
            # under some if statement) in the loop. This means that their value
            # needs to be registered.
            loop_end = [p for p in node.prev if p not in self.visited]
            loop_start = [p for p in node.prev if p in self.visited]

            all_in_end = set()
            for n in loop_end:
                all_in_end |= self.reaching[n]['out']

            all_in_start = set()
            for n in loop_start:
                all_in_start |= self.reaching[n]['out']

            changed = set(name for name, n in (all_in_end - all_in_start))
            reached_from_before = set(name for name, _ in (all_in_end & all_in_start)
                                      if name in changed)

            self.registers |= reached_from_before

        if not isinstance(node.value, Loop) and any(p not in self.visited for p in node.prev):
            return

        # print(f'Visit: {node.value}')
        self.visit_ast(node.value, self.reaching[node])
        self.visited.add(node)

        for succ in node.next:
            self.visit(succ)

    def visit_ast(self, node, reaching):
        for base_class in inspect.getmro(node.__class__):
            if hasattr(self, base_class.__name__):
                getattr(self, base_class.__name__)(node, reaching)
                break
        else:
            self.generic_visit(node, reaching)

    def generic_visit(self, node, reaching):
        # print(f'Generic: {node}')
        pass

    def expr(self, node, reaching):
        if all(d[1] in self.visited for d in reaching.get('in', [])):
            return

        variables = []
        for succ in gast.walk(node):
            if not isinstance(succ, gast.Name):
                continue

            if not (isinstance(succ.ctx, gast.Load) or isinstance(node, gast.AugAssign)):
                continue

            variables.append(succ.id)


        for name, n in reaching['in']:
            if (n in self.visited) or (name not in variables) or (name in self.registers):
                continue

            self.registers.add(name)

    def Expr(self, node: gast.Expr, reaching):
        self.visit_ast(node.value, reaching)

    def Return(self, node: gast.Yield, reaching):
        self.expr(node.value, reaching)

    def Yield(self, node: gast.Yield, reaching):
        self.expr(node.value, reaching)

    def AugAssign(self, node: gast.AugAssign, reaching):
        self.expr(node, reaching)

    def Assign(self, node: gast.Assign, reaching):
        self.expr(node, reaching)

    AnnAssign = Assign

    def AsyncWith(self, node: gast.AsyncWith, reaching):
        # TODO: Fix me!
        pass


def dfs(node, G, visited, labels):
    if node in visited:
        return

    visited.add(node)
    labels[id(node)] = type(node.value).__name__

    for n in node.next:
        G.add_edge(id(node), id(n))

        dfs(n, G, visited, labels)


def draw_cfg(cfg):
    import networkx as nx
    import matplotlib.pyplot as plt

    G = nx.DiGraph()
    visited = set()
    labels = {}

    dfs(cfg.entry, G, visited, labels)

    pos = nx.planar_layout(G)
    nx.draw(G, pos, font_size=16, with_labels=False)

    # for p in pos:  # raise text positions
    #     pos[p][1] += 0.07

    nx.draw_networkx_labels(G, pos, labels)
    plt.show()


def forward(node, analysis):
    """Perform a given analysis on all functions within an AST."""
    if not isinstance(analysis, Forward):
        raise TypeError('not a valid forward analysis object')

    cfg_obj = CFG.build_cfg(node)
    # draw_cfg(cfg_obj)

    analysis.visit(cfg_obj.entry)

    v = InferRegisters(analysis.reaching)
    v.visit(cfg_obj.entry)

    # print(f'Registers: {v.registers}')

    return node, cfg_obj.entry, analysis.reaching, v.registers


def reaching(node):
    return forward(node, ReachingDefinitions())


class ReachingDefinitions(Forward):
    """Perform reaching definition analysis.

    Each statement is annotated with a set of (variable, definition) pairs.

    """
    def __init__(self):
        def definition(node, incoming):
            definitions = get_updated(node.value)
            gen = frozenset((id_, node) for id_ in definitions)
            kill = frozenset(def_ for def_ in incoming if def_[0] in definitions)
            return gen, kill

        super(ReachingDefinitions, self).__init__('definitions', definition)
