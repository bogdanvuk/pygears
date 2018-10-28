from bdp import block, p, group, cap, path, text, fig, prev, render_fig, poffx

bus_cap = cap(length=0.4, width=0.6, inset=0, type='Stealth')
bus = path(
    color="black!40",
    style=('', bus_cap),
    shorten=p(0.2, 0.2),
    line_width=0.3,
    border_width=0.06,
    double=True)
bus_text = text(font="\\footnotesize", margin=p(0.5, 0.35))

gear = block(size=p(6, 4), nodesep=p(2, 2))

fig['drv'] = gear('drv', size=p(6, 2))
fig['riscv'] = gear('riscv').right(fig['drv'], 3)
fig['register_file'] = gear('register_file').below(fig['riscv'])

fig << bus(fig['drv'].e(1), fig['riscv'].w(1))
fig << bus_text("instruction").align(fig[-1].pos(0), prev().s())
fig << bus(
    fig['riscv'].e(1), poffx(7), fig['register_file'].e(3), routedef='|-')
fig << bus_text("reg_file_rd_req").align(fig[-1].pos(0), prev().s())

fig << bus(
    fig['riscv'].e(3), poffx(5), fig['register_file'].e(1), routedef='|-')
fig << bus_text("reg_file_wr_req").align(fig[-1].pos(0), prev().s())

fig << bus(
    fig['register_file'].w(0.5), poffx(-3), fig['riscv'].w(3), routedef='|-')
fig << bus_text("reg_rd_data").align(fig[-1].pos(1.0), prev().s(1.1))

fig << text(
    r"\textasciitilde", font="\\Huge").align(fig[-1].s(0.54),
                                             prev().n(0.5))
fig << text(
    r"\textasciitilde", font="\\Huge").align(fig[-2].s(0.54),
                                             prev().n(0.5, -0.2))

# render_fig(fig)
