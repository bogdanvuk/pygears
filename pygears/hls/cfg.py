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
import inspect

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
        # return set()
        return set([f'{target.val.name}.{target.field}'])
    else:
        return set()
        # breakpoint()
        # raise ValueError


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
    elif isinstance(node, ir.RegReset):
        return set([node.target.name])
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


class Node:
    # """A node in the CFG."""
    # __slots__ = ['next', 'value', 'prev', 'sink', '_source']

    def __init__(self, value, next_=None, prev=None, source=None):
        if next_ is None:
            next_ = []

        if prev is None:
            prev = []

        self.next = next_
        self.prev = prev
        self.value = value
        self._source = None

        self.source = source
        self.sink = None

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, val):
        if val is not None:
            val.sink = self
        elif self._source is not None:
            self._source.sink = None

        self._source = val


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


def forwardlink(node):
    """Given a CFG with outgoing links, create incoming links."""
    seen = set()
    to_see = [node]
    while to_see:
        node = to_see.pop()
        seen.add(node)
        for pred in node.prev:
            pred.next.append(node)
            if pred not in seen:
                to_see.append(pred)


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
        cfg = cls()
        cfg.head = []
        cfg.entry = cfg.visit(node)
        cfg.exit = cfg.entry.sink
        backlink(cfg.entry)
        return cfg

    def Module(self, block: ir.Module):
        node = self.BaseBlock(block)
        node.sink.value = ir.ModuleSink()
        return node

    def BaseBlock(self, block: ir.BaseBlock):
        node = Node(block)
        self.set_head(node)
        for stmt in block.stmts:
            self.visit(stmt)

        sink = Node(ir.BaseBlockSink(), source=node)
        self.set_head(sink)

        return node

    def Branch(self, block: ir.Branch):
        node = self.BaseBlock(block)
        node.sink.value = ir.BranchSink()

    def Statement(self, stmt: ir.Statement):
        node = Node(stmt)
        self.set_head(node)
        return node

    def LoopBlock(self, block: ir.LoopBlock):
        # Start a new level of nesting
        self.break_.append([])
        self.continue_.append([])
        # Handle the body
        node = self.BaseBlock(block)
        node.sink.value = ir.LoopBlockSink()

        self.head.extend(self.continue_.pop())
        self.set_head(node)

        # The break statements and the test go to the next node
        self.head.extend(self.break_.pop())

    def HDLBlock(self, block: ir.HDLBlock):
        branch_exits = []
        node = Node(block)

        for b in block.branches:
            self.set_head(node)
            self.visit(b)
            branch_exits.extend(self.head[:])
            self.head[:] = []

        self.head.extend(branch_exits)
        sink = Node(ir.HDLBlockSink(), source=node)
        self.set_head(sink)

        if not block.has_else:
            br_else_sink = Node(ir.BranchSink(), next_=[sink])
            br_else = Node(ir.Branch(), next_=[br_else_sink])
            br_else_sink.source = br_else
            node.next.append(br_else)

    def generic_visit(self, node):
        breakpoint()
        raise ValueError('unknown control flow')


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

    def visit(self, node):
        if node not in self.reaching:
            self.reaching[node] = {}

        reaching = self.reaching[node]

        if node.value:
            if 'out' in reaching:
                before = hash(reaching['out'])
            else:
                before = None

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

            if hash(reaching['out']) != before:
                for succ in node.next:
                    self.visit(succ)


def forward(node, analysis):
    """Perform a given analysis on all functions within an AST."""
    if not isinstance(analysis, Forward):
        raise TypeError('not a valid forward analysis object')

    cfg_obj = CFG.build_cfg(node)

    if hls_debug_log_enabled():
        draw_cfg(cfg_obj)

    analysis.visit(cfg_obj.entry)

    return node, cfg_obj.entry, analysis.reaching


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
    def __init__(self, update=get_updated):
        def definition(node, incoming):
            if isinstance(node.value, ir.Await) and isinstance(node.value.expr, ir.Component):
                intf_name = node.value.expr.val.name
                # gen = frozenset([(f'{intf_name}.ready', node.value)])
                gen = frozenset()
                kill = frozenset(def_ for def_ in incoming if def_[0] == f'{intf_name}.data')
            else:
                definitions = update(node.value)
                gen = frozenset((id_, node) for id_ in definitions)
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


class CfgDfs:
    def __init__(self):
        self.scopes = []

    def visit(self, node):
        for base_class in inspect.getmro(node.value.__class__):
            if hasattr(self, base_class.__name__):
                return getattr(self, base_class.__name__)(node)
        else:
            return self.generic_visit(node)

    def enter(self, node):
        for base_class in inspect.getmro(node.value.__class__):
            method_name = f'enter_{base_class.__name__}'
            if hasattr(self, method_name):
                return getattr(self, method_name)(node)

    def exit(self, node):
        for base_class in inspect.getmro(node.value.__class__):
            method_name = f'exit_{base_class.__name__}'
            if hasattr(self, method_name):
                return getattr(self, method_name)(node)

    @property
    def parent(self):
        return self.scopes[-1]

    def LoopBlock(self, node):
        skip = self.enter(node)
        if not skip:
            self.scopes.append(node)
            self.visit(node.next[0])
            self.scopes.pop()

        self.exit(node)

        return self.visit(node.next[1])

    def LoopBlockSink(self, node):
        return

    def BaseBlock(self, node):
        skip = self.enter(node)
        if not skip:
            self.scopes.append(node)
            self.visit(node.next[0])
            self.scopes.pop()

        self.exit(node)

        return self.generic_visit(node.sink)

    def HDLBlock(self, node):
        skip = self.enter(node)
        if not skip:
            self.scopes.append(node)
            for n in node.next:
                self.visit(n)

            self.scopes.pop()
        self.exit(node)

        return self.generic_visit(node.sink)

    def generic_visit(self, node):
        skip = self.enter(node)
        self.exit(node)
        if not skip:
            for n in node.next:
                self.visit(n)

    def HDLBlockSink(self, node: ir.HDLBlockSink):
        if node.source in self.scopes:
            return

        return self.generic_visit(node)

    def BaseBlockSink(self, node: ir.BaseBlockSink):
        if node.source in self.scopes:
            return

        return self.generic_visit(node)
