# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#      Unless required by applicable law or agreed to in writing, software
#      distributed under the License is distributed on an "AS IS" BASIS,
#      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#      See the License for the specific language governing permissions and
#      limitations under the License.
"""Control flow graph analysis.

Given a Python AST we construct a doubly linked control flow graph whose nodes
contain the AST of the statements. We can then perform forward analysis on this
CFG.

"""
from __future__ import absolute_import
import functools
import operator

import ast as gast

from . import ir
from . import HDLVisitor
from .debug import hls_debug_log_enabled


def get_name(node):
    """Get the name of a variable.
    Args:
        node: A `Name`, `Subscript` or `Attribute` node.
    Returns:
        The name of the variable e.g. `'x'` for `x`, `x.i` and `x[i]`.
    """
    if isinstance(node, ir.Name):
        return node.name
    elif isinstance(node, (ir.SubscriptExpr, ir.AttrExpr)):
        return get_name(node.val)
    else:
        raise TypeError


def _get_target(target):
    if isinstance(target, (ir.Name, ir.SubscriptExpr, ir.AttrExpr)):
        return set([get_name(target)])
    elif isinstance(target, (ir.ConcatExpr, gast.List)):
        return set.union(*(_get_target(target) for target in target.operands))
    elif isinstance(target, (ir.Component)):
        return set()
    else:
        breakpoint()
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
    if isinstance(node, ir.AssignValue):
        return _get_target(node.target)
    else:
        return set()

    # if isinstance(node, gast.Assign):
    #     return set.union(*(_get_target(target) for target in node.targets))
    # elif isinstance(node, (gast.For, gast.AugAssign)):
    #     return _get_target(node.target)
    # elif isinstance(node, gast.AsyncWith):
    #     return set(i.optional_vars.id for i in node.items)
    # elif isinstance(node, gast.arguments):
    #     targets = set(arg.arg for arg in node.args + node.kwonlyargs)
    #     if node.vararg:
    #         targets.add(node.vararg.id)
    #     if node.kwarg:
    #         targets.add(node.kwarg.id)
    #     return targets
    # else:
    #     return set()


class Node(object):
    """A node in the CFG."""
    __slots__ = ['next', 'value', 'prev']

    def __init__(self, value):
        self.next = set()
        self.prev = set()
        self.value = value

        if self.value is not None and not hasattr(self.value, 'reaching'):
            self.value.reaching = {}


class CFG(HDLVisitor):
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
                succ.prev.add(node)
                if succ not in seen:
                    to_see.append(succ)

    def set_head(self, node):
        """Link this node to the current leaves."""
        for head in self.head:
            head.next.add(node)
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
        cfg = cls()
        cfg.entry = Node(node)
        cfg.head = [cfg.entry]
        cfg.BaseBlock(node)
        cfg.exit = Node(None)
        cfg.set_head(cfg.exit)
        cfg.backlink(cfg.entry)
        return cfg

    def BaseBlock(self, block: ir.BaseBlock):
        for stmt in block.stmts:
            self.visit(stmt)

    def Statement(self, stmt: ir.Statement):
        expr = Node(stmt)
        self.set_head(expr)

    def HDLBlock(self, block: ir.HDLBlock):
        test = Node(block.in_cond)
        self.set_head(test)

        self.BaseBlock(block)

        # If there is a condition to enter this block, make two possible paths:
        # one through it and one around it
        if block.in_cond != ir.res_true:
            body_exit = self.head[:]
            self.head[:] = []
            self.head.append(test)
            self.head.extend(body_exit)

    def LoopBlock(self, block: ir.LoopBlock):
        in_cond = Node(block.in_cond)
        node = Node(block)
        self.set_head(in_cond)
        self.set_head(node)
        # Start a new level of nesting
        self.break_.append([])
        self.continue_.append([])
        # Handle the body
        self.BaseBlock(block)
        self.head.extend(self.continue_.pop())

        # self.set_head(test)
        exit_cond = Node(block.exit_cond)
        self.set_head(exit_cond)
        self.set_head(node)

        # The break statements and the test go to the next node
        self.head.extend(self.break_.pop())

    def IfElseBlock(self, block: ir.IfElseBlock):
        branch_exits = []
        for stmt in block.stmts:
            test = Node(stmt.in_cond)
            self.set_head(test)

            self.BaseBlock(stmt)

            branch_exits.extend(self.head[:])
            self.head[:] = []

            if stmt.in_cond != ir.res_true:
                self.head.append(test)

        self.head.extend(branch_exits)

    def generic_visit(self, node):
        breakpoint()
        raise ValueError('unknown control flow')

    # def visit_AsyncWith(self, node):
    #     # The current head will hold the conditional
    #     test = Node(node)
    #     self.set_head(test)
    #     # Handle the body
    #     self.visit_statements(node.body)

    # def visit_If(self, node):
    #     # The current head will hold the conditional
    #     test = Node(node.test)
    #     self.set_head(test)
    #     # Handle the body
    #     self.visit_statements(node.body)
    #     body_exit = self.head[:]
    #     self.head[:] = []
    #     self.head.append(test)
    #     # Handle the orelse
    #     self.visit_statements(node.orelse)
    #     self.head.extend(body_exit)

    # def visit_While(self, node):
    #     test = Node(node.test)
    #     self.set_head(test)
    #     # Start a new level of nesting
    #     self.break_.append([])
    #     self.continue_.append([])
    #     # Handle the body
    #     self.visit_statements(node.body)
    #     self.head.extend(self.continue_.pop())
    #     self.set_head(test)
    #     # Handle the orelse
    #     self.visit_statements(node.orelse)
    #     # The break statements and the test go to the next node
    #     self.head.extend(self.break_.pop())

    # def visit_AsyncFor(self, node):
    #     self.visit_For(node)

    # def visit_For(self, node):
    #     iter_ = Node(node)
    #     self.set_head(iter_)
    #     self.break_.append([])
    #     self.continue_.append([])
    #     self.visit_statements(node.body)
    #     self.head.extend(self.continue_.pop())
    #     self.set_head(iter_)
    #     self.head.extend(self.break_.pop())

    # def visit_Break(self, node):
    #     self.break_[-1].extend(self.head)
    #     self.head[:] = []

    # def visit_Continue(self, node):
    #     self.continue_[-1].extend(self.head)
    #     self.head[:] = []

    # def visit_Try(self, node):
    #     self.visit_statements(node.body)
    #     body = self.head
    #     handlers = []
    #     for handler in node.handlers:
    #         self.head = body[:]
    #         self.visit_statements(handler.body)
    #         handlers.extend(self.head)
    #     self.head = body
    #     self.visit_statements(node.orelse)
    #     self.head = handlers + self.head
    #     self.visit_statements(node.finalbody)


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

    def visit(self, node):
        if node.value:
            if 'out' in node.value.reaching:
                before = hash(node.value.reaching['out'])
            else:
                before = None

            preds = [
                pred.value.reaching['out'] for pred in node.prev if 'out' in pred.value.reaching
            ]
            if preds:
                incoming = functools.reduce(self.op, preds[1:], preds[0])
            else:
                incoming = frozenset()

            node.value.reaching['in'] = incoming
            gen, kill = self.gen(node, incoming)
            node.value.reaching['gen'] = gen
            node.value.reaching['kill'] = kill
            node.value.reaching['out'] = (incoming - kill) | gen

            if hash(node.value.reaching['out']) != before:
                for succ in node.next:
                    self.visit(succ)
        else:
            preds = [
                pred.value.reaching['out'] for pred in node.prev if 'out' in pred.value.reaching
            ]
            self.exit = functools.reduce(self.op, preds[1:], preds[0])


def forward(node, analysis):
    """Perform a given analysis on all functions within an AST."""
    if not isinstance(analysis, Forward):
        raise TypeError('not a valid forward analysis object')

    cfg_obj = CFG.build_cfg(node)

    if hls_debug_log_enabled():
        draw_cfg(cfg_obj)

    analysis.visit(cfg_obj.entry)

    return node


def node_name(node):
    if isinstance(node.value, ir.BaseBlock):
        return f'{type(node.value)}'

    return str(node.value)


def dfs(node, G, visited, labels):
    if node in visited:
        return

    visited.add(node)
    labels[id(node)] = node_name(node)

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


class ReachingDefinitions(Forward):
    """Perform reaching definition analysis.

  Each statement is annotated with a set of (variable, definition) pairs.

  """
    def __init__(self):
        def definition(node, incoming):
            definitions = get_updated(node.value)
            gen = frozenset((id_, node.value) for id_ in definitions)
            kill = frozenset(def_ for def_ in incoming if def_[0] in definitions)
            return gen, kill

        super(ReachingDefinitions, self).__init__('definitions', definition)


class Defined(Forward):
    """Perform defined variable analysis.

  Each statement is annotated with a set of variables which are guaranteed to
  be defined at that point.
  """
    def __init__(self):
        def defined(node, incoming):
            gen = get_updated(node.value)
            return gen, frozenset()

        super(Defined, self).__init__('defined', defined, operator.and_)


class Active(Forward):
    """Active variable analysis.

  Given a set of active arguments, find all variables that are active i.e.
  variables whose values possibly depend on the given set of arguments.

  Args:
    wrt: A tuple of indices of arguments that are active.
  """
    def __init__(self, wrt):
        def active(node, incoming):
            gen = set()
            kill = set()
            if isinstance(node.value, gast.arguments):
                gen.update(node.value.args[i].id for i in wrt)
            if isinstance(node.value, gast.Assign):
                # Special-case e.g. x = tangent.pop(_stack)
                # such that all values popped off the stack are live.
                if anno.getanno(node.value.value, 'func', False) == utils.pop:
                    gen.update(get_updated(node.value))
                else:
                    for succ in gast.walk(node.value.value):
                        if isinstance(succ, gast.Name) and succ.id in incoming:
                            gen.update(get_updated(node.value))
                            break
                    else:
                        kill.update(get_updated(node.value))
            return gen, kill

        super(Active, self).__init__('active', active)
