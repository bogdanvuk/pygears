from bdp import block, cap, path, text, fig, prev, p, poffx

part = block(text_margin=p(0.5, 0.5),
             alignment="nw",
             dotted=True,
             group='tight',
             group_margin=[p(1, 3), p(1, 2)])

comp = block(size=p(4, 4), nodesep=(6, 2))
ps_comp = block(size=p(6, 6), nodesep=(2, 3))
bus_cap = cap(length=0.4, width=0.6, inset=0, type='Stealth')
bus = path(style=(None, bus_cap),
           line_width=0.3,
           double=True,
           border_width=0.06)
bus_text = text(font="\\scriptsize", margin=p(0, 0.5))

functor = part("Tuple fmap")
functor['split'] = comp("split", size=(4, 4))
functor['f1'] = comp(r"$\times 2$",
                     size=(4, 3)).right(functor['split']).aligny(
                         functor['split'].w(1),
                         prev().s(0))
functor['f2'] = comp(r"$\times 2$", size=(4, 3)).below(functor['f1'])

functor['concat'] = comp("ccat", size=(4, 4)).right(functor['f1']).aligny(
    functor['split'].p)

prod2split = bus(functor['split'].w(0.5) - p(4, 0), functor['split'].w(0.5))
fig << prod2split
fig << bus_text("(u16, u16)").align(prod2split.pos(0.5), prev().s(0.5, 0.2))

for i in range(2):
    conn = bus(functor['split'].e(i * 2 + 1),
               functor[f'f{i+1}'].w(0.5) - (2, 0),
               functor[f'f{i+1}'].w(0.5),
               routedef='-|')
    fig << bus_text("u16").align(conn.pos(0), prev().s(-0.4, 0.1))
    fig << conn

    conn = bus(functor[f'f{i+1}'].e(0.5),
               functor[f'f{i+1}'].e(0.5) + (2, 0),
               functor['concat'].w(i * 2 + 1),
               routedef='|-')
    fig << bus_text("u17").align(conn.pos(1), prev().s(1.4, 0.1))
    fig << conn

con2cons = bus(functor['concat'].e(0.5), poffx(4))
fig << con2cons
fig << bus_text("(u17, u17)").align(con2cons.pos(0.5), prev().s(0.5, 0.2))

fig << functor

# render_fig(fig)
