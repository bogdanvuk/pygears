import itertools
from pygears.hls import HDLWriter, InstanceVisitor, parse_gear_body
from pygears import registry
from pygears.hls2.pydl import nodes as pydl
from pygears.hls2.hdl import nodes
from pygears.hls2 import Context, GearContext, FuncContext
from pygears.typing import code, Bool
from pygears.core.port import Port
from dataclasses import dataclass, field
from typing import List
from pygears import Intf

from ..util import separate_conditions
from .sv_expression2 import svexpr
from .util import svgen_typedef

REG_TEMPLATE = """
always @(posedge clk) begin
    if(rst | rst_cond) begin
        {0} <= {1};
    end else if ({0}_en && cycle_done) begin
        {0} <= {0}_next;
    end
end
"""

res_true = pydl.ResExpr(Bool(True))


@dataclass
class BlockLines:
    header: List = field(default_factory=list)
    content: List = field(default_factory=list)
    footer: List = field(default_factory=list)

@dataclass
class IfElseBlock(BlockLines):
    pass


class SVCompiler(InstanceVisitor):
    def __init__(self, ctx, visit_var, writer, selected):
        self.ctx = ctx
        self.defaults = {}
        self.writer = writer
        self.visit_var = visit_var
        self.selected = selected
        self.block_lines = []
        self.block_stack = []

    @property
    def cur_block_lines(self):
        return self.block_lines[-1]

    def write(self, line):
        self.cur_block_lines.content.append(line)

    def header(self, line):
        self.cur_block_lines.header.append(line)

    def footer(self, line):
        self.cur_block_lines.footer.append(line)

    def enter_block(self, block):
        self.block_stack.append(block)
        bl = BlockLines()
        self.block_lines.append(bl)

        maybe_else = 'else ' if getattr(block, 'else_branch', False) else ''

        in_cond = pydl.BinOpExpr((block.in_cond, block.opt_in_cond),
                                 pydl.opc.And)

        if in_cond != res_true:
            in_cond_val = svexpr(in_cond)

            self.header(f'{maybe_else}if ({in_cond_val}) begin')
        elif maybe_else:
            self.header(f'else begin')

    def exit_block(self, block=None):
        bl = self.block_lines.pop()

        self.write(bl)

        self.block_stack.pop()

    def _assign_value(self, stmt):
        if isinstance(stmt.target, pydl.SubscriptExpr):
            target = stmt.target.val
        elif isinstance(stmt.target, pydl.Name):
            target = stmt.target
            if target.name == 'out_res':
                breakpoint()
        else:
            raise Exception

        if not self.selected(target):
            return

        val = stmt.val

        if isinstance(target.obj, pydl.Register):
            svstmt = f"{target.name}_next = {svexpr(val)}"

            if target.name not in self.defaults:
                self.defaults[target.name] = svstmt
            elif svstmt != self.defaults[target.name]:
                self.write(svstmt)

            self.write(f"{target.name}_en = 1")
            return

        if isinstance(target.obj, pydl.Interface):
            if target.ctx == 'store':
                svstmt = f"{target.name}_s = {svexpr(val)}"

                if target.name not in self.defaults:
                    self.defaults[target.name] = svstmt
                elif svstmt != self.defaults[target.name]:
                    self.write(svstmt)

                # self.write(f"{target.name}_s = {svexpr(val)}")
                self.write(f"{target.name}.valid = 1")
            elif target.ctx == 'ready':
                self.write(f"{target.name}.ready = 1")

            return

        target = svexpr(stmt.target)
        svstmt = f"{target} = {svexpr(val)}"

        if target not in self.defaults:
            self.defaults[target] = svstmt
        elif svstmt != self.defaults[target]:
            self.write(svstmt)

        # self.write(f"{svexpr(stmt.target)} = {svexpr(val)}")

    def visit_AssertValue(self, node):
        self.write(f'assert ({svexpr(node.val.test)})')
        self.write(f'else $error("{node.val.msg}");')

    def visit_AssignValue(self, node):
        assign_stmt = self._assign_value(node)
        if assign_stmt is not None:
            self.write(f'{assign_stmt};')

    def visit_StateBlock(self, node):
        self.write('case (state)')
        self.write.indent += 4
        for i, child in enumerate(node.stmts):
            self.write(f'{i}: begin')
            self.write.indent += 4
            self.visit(child)
            self.write.indent -= 4
            self.write('end')

        self.write.indent -= 4
        self.write('endcase')

    def list_initials(self):
        for name, obj in self.ctx.scope.items():
            if isinstance(obj, pydl.Interface):
                if obj.direction == 'in':
                    if self.selected(self.ctx.ref(name, ctx='ready')):
                        self.write(f"{name}.ready = {name}.valid ? 0 : 1'bx")
                else:
                    if self.selected(self.ctx.ref(name, ctx='store')):
                        self.write(f"{name}.valid = 0")
                        # self.write(f"{name}_s = {obj.dtype.width}'(1'bx)")

            elif isinstance(obj, pydl.Register):
                if self.selected(self.ctx.ref(name, ctx='store')):
                    # self.write(f"{name}_next = {obj.dtype.width}'(1'bx)")
                    # self.write(f"{name}_next = {name}")
                    self.write(f'{name}_en = 0')

            elif isinstance(obj, pydl.Variable):
                pass
                # if self.selected(self.ctx.ref(name, ctx='store')):
                #     self.write(f"{name} = {obj.dtype.width}'(1'bx)")

    def visit_CombBlock(self, node):
        self.block_lines.append(BlockLines())

        self.header(f'// Comb block for: {self.visit_var}')
        self.header(f'always_comb begin')

        self.list_initials()

        self.visit_HDLBlock(node)

        for target, svstmt in self.defaults.items():
            self.cur_block_lines.content.insert(0, svstmt)

        self.footer('end')

    def visit_FuncReturn(self, node):
        self.write(f"{svexpr(node.func.name)} = {svexpr(node.expr)}")

    def visit_FuncBlock(self, node):
        self.block_lines.append(BlockLines())

        self.header('')

        self.visit_HDLBlock(node)

        self.footer(f'endfunction')
        self.footer('')

    def visit_CombSeparateStmts(self, node):
        if node.stmts:
            self.write(f'// Comb statements for: {self.visit_var}')
            for stmt in node.stmts:
                assign_stmt = self._assign_value(stmt)
                if assign_stmt is not None:
                    self.write(f'assign {assign_stmt};')
            self.write('')

    def visit_HDLBlock(self, node):
        self.enter_block(node)

        for stmt in node.dflt_stmts:
            assign_stmt = self._assign_value(stmt)
            if assign_stmt is not None:
                self.write(f'{assign_stmt};')

        for stmt in node.stmts:
            self.visit(stmt)

        content = []
        for c in self.cur_block_lines.content:
            if isinstance(c, BlockLines) and not c.content:
                continue

            content.append(c)

        self.cur_block_lines.content = content

        self.exit_block(node)

    def visit_IfElseBlock(self, node):
        self.enter_block(node)

        for stmt in node.dflt_stmts:
            assign_stmt = self._assign_value(stmt)
            if assign_stmt is not None:
                self.write(f'{assign_stmt};')

        for i, stmt in enumerate(node.stmts):
            if i > 0:
                stmt.else_branch = True

            self.visit(stmt)

        content = []
        for c in reversed(self.cur_block_lines.content):
            if not content and not c.content:
                continue

            content.insert(0, c)

        self.cur_block_lines.content = content

        self.exit_block(node)


gear_module_template = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.gear_module(module_name, intfs, comment, sigs) %}

{{svlines|indent(4,True)}}

{%- endcall %}
"""


def write_block(block, writer):
    for h in block.header:
        writer.line(h)

    if block.header:
        writer.indent += 4

    for c in block.content:
        if isinstance(c, str):
            writer.line(c + ';')
        else:
            write_block(c, writer)

    if block.header:
        writer.indent -= 4
        writer.line('end')


def typedef_or_inline(writer, dtype, name):
    res = svgen_typedef(dtype, name)
    if "\n" not in res[:-1]:
        return res.partition(' ')[-1].rpartition(';')[0].rpartition(' ')[0]

    writer.block(res)
    return f'{name}_t'


def svcompile(hdl_stmts, writer, ctx, title, selected):
    v = SVCompiler(ctx, title, writer, selected=selected)
    v.visit(hdl_stmts)
    write_block(v.block_lines[0], writer)
    writer.line()


def write_module(ctx: Context,
                 hdl,
                 writer,
                 subsvmods,
                 funcs,
                 template_env,
                 config=None):
    if config is None:
        config = {}

    # svcompile(hdl, writer, ctx, "proba", selected=lambda x: x)

    for name, expr in ctx.regs.items():
        writer.line(f'logic {name}_en;')
        writer.line(f'logic [{expr.dtype.width-1}:0] {name}, {name}_next;')
        writer.line()

    for name, expr in ctx.intfs.items():
        if isinstance(expr.intf, Intf):
            writer.line(f'dti#({expr.dtype.width}) {name}();')

        name_t = typedef_or_inline(writer, expr.dtype, name)
        writer.line(f'{name_t} {name}_s;')
        if expr.direction == 'in':
            writer.line(f'assign {name}_s = {name}.data;')
        else:
            writer.line(f'assign {name}.data = {name}_s;')

        writer.line()

    for name, expr in ctx.variables.items():
        name_t = typedef_or_inline(writer, expr.dtype, name)
        writer.line(f'{name_t} {name};')
        writer.line()

    for c, s in zip(ctx.submodules, subsvmods):
        port_map = {}
        for intf, p in zip(c.in_ports, c.gear.in_ports):
            port_map[p.basename] = intf.name

        for intf, p in zip(c.out_ports, c.gear.out_ports):
            port_map[p.basename] = intf.name

        writer.block(s.get_inst(template_env, port_map))

    for f_hdl, f_ctx in funcs:
        size = ''
        if int(f_hdl.ret_dtype) > 0:
            size = f'[{int(f_hdl.ret_dtype)-1}:0]'

        if getattr(f_hdl.ret_dtype, 'signed', False):
            size = f'signed {size}'

        writer.line(f'function {size} {f_hdl.name};')

        writer.indent += 4

        for name, expr in f_ctx.args.items():
            name_t = typedef_or_inline(writer, expr.dtype, name)
            writer.line(f'input {name_t} {name};')
            writer.line()

        svcompile(f_hdl, writer, f_ctx, '', selected=lambda x: True)

    if ctx.regs:
        writer.line(f'initial begin')
        for name, expr in ctx.regs.items():
            writer.line(f"    {name} = {svexpr(expr.val)};")

        writer.line(f'end')

    for name, expr in ctx.regs.items():
        writer.block(REG_TEMPLATE.format(name, svexpr(expr.val)))

    for name, expr in ctx.regs.items():
        svcompile(hdl, writer, ctx, name, selected=lambda x: x.obj == expr)

    for name, expr in ctx.variables.items():
        svcompile(hdl, writer, ctx, name, selected=lambda x: x.obj == expr)

    for name, expr in ctx.intfs.items():
        svcompile(hdl, writer, ctx, name, selected=lambda x: x.name == name)


def compile_gear_body(gear, outdir, template_env):
    # ctx, hdl_ast = parse_gear_body(gear)
    from pygears.hls2.translate import translate_gear
    ctx, hdl_ast = translate_gear(gear)

    subsvmods = []
    if ctx.submodules:
        from pygears.hdl import hdlgen
        svgen_map = registry("svgen/map")
        for c in ctx.submodules:
            rtl_top = hdlgen(c.gear, outdir=outdir)
            svmod = svgen_map[rtl_top]
            subsvmods.append(svmod)

    funcs = []

    def _get_funcs_rec(block):
        for f_ast, f_ctx in block.funcs:
            funcs.append((f_ast, f_ctx))
            _get_funcs_rec(f_ast)

    _get_funcs_rec(hdl_ast)

    gear.child.clear()

    writer = HDLWriter()
    write_module(ctx,
                 hdl_ast,
                 writer,
                 subsvmods,
                 funcs,
                 template_env,
                 config=gear.params.get('hdl', {}))

    return '\n'.join(writer.lines), subsvmods


def compile_gear(gear, template_env, module_name, outdir):
    context = {
        'module_name': module_name,
        'intfs': template_env.port_intfs(gear),
        'sigs': gear.params['signals'],
        'params': gear.params
    }

    context['svlines'], subsvmods = compile_gear_body(gear, outdir,
                                                      template_env)

    return template_env.render_string(gear_module_template, context), subsvmods
