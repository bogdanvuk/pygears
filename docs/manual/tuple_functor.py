from bdp import *

part = block(text_margin=p(0.5, 0.5), alignment="nw", dotted=True, group='tight', group_margin=[p(1,3), p(1,2)])

comp = block(size=p(6,4), nodesep=(6,2))
ps_comp = block(size=p(6,6), nodesep=(2,3))
bus_cap = cap(length=0.4, width=0.6, inset=0, type='Stealth')
bus = path(style=(bus_cap, bus_cap), line_width=0.3, double=True, border_width=0.06)
bus_text = text(font="\\scriptsize", margin=p(0,0.5))

functor = part("Queue Functor")
functor['split'] = comp("Split", size=(4,6))
functor['f1'] = comp("*2", size=(4,4)).right(functor['split']).aligny(functor['split'].w(2), prev().s(0))
functor['f2'] = comp("*2", size=(4,4)).below(functor['f1'])

functor['concat'] = comp("Concat", size=(4,6)).right(functor['f1']).aligny(functor['split'].p)

producer = comp("Producer").left(functor['split'], 1).aligny(functor['split'].e(0.5), prev().e(0.5))
fig << producer
prod2split = bus(producer.e(0.5), functor['split'].w(0.5))
fig << prod2split
fig << bus_text("(u16, u16)").align(prod2split.pos(0.5), prev().s(0.5, 0.2))

for i in range(2):
    conn = bus(functor['split'].e(i*4+1), functor[f'f{i+1}'].w(0.5) - (2, 0), functor[f'f{i+1}'].w(0.5), routedef='-|')
    fig << bus_text("u16").align(conn.pos(0), prev().s(-0.4, 0.1))
    fig << conn

    conn = bus(functor[f'f{i+1}'].e(0.5), functor[f'f{i+1}'].e(0.5) + (2, 0), functor['concat'].w(i*4+1), routedef='|-')
    fig << bus_text("u17").align(conn.pos(1), prev().s(1.4, 0.1))
    fig << conn

consumer = comp("Consumer").right(functor['concat'], 1).aligny(functor['concat'].e(0.5), prev().e(0.5))
fig << consumer
con2cons = bus(functor['concat'].e(0.5), consumer.w(0.5))
fig << con2cons
fig << bus_text("(u17, u17)").align(con2cons.pos(0.5), prev().s(0.5, 0.2))

fig << functor

render_fig(fig)
