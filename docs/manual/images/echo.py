from bdp import block, p, group, cap, path, text, poffx, poffy, prectx, fig, render_fig, cur, prev

mul_block = block("x", size=p(2, 2), shape='circle')
add_block = block("+", size=p(2, 2), shape='circle')
bus_cap = cap(length=0.4, width=0.6, inset=0, type='Stealth')
bus = path(color="black!40",
           style=('', bus_cap),
           shorten=p(0.2, 0.2),
           line_width=0.3,
           border_width=0.06,
           double=True)
bus_text = text(font="\\footnotesize", margin=p(0.4, 0.4))

echo = block("echo",
             text_margin=p(0.5, 0.5),
             alignment="nw",
             dotted=True,
             group='tight',
             group_margin=[p(1, 3), p(2, 1)],
             text_font="\\Large")


def make_external(pos, direction='o', pin_extrude=1.5, **kwds):
    if direction == 'o':
        style = ('', bus_cap)
    else:
        style = (bus_cap, '')
    return bus(pos,
               poffx(echo.w() - pos - p(pin_extrude, 0)),
               style=style,
               **kwds)


echo['add'] = add_block()
echo['decouple'] = block(r"decouple \\ (FIFO)", size=p(5, 4)).align(echo['add'].p + p(15, 3))

echo['dout'] = bus(echo['add'].e(0.5),
                   prectx(echo['decouple'].n(1.0) + p(1, 1)),
                   echo['decouple'].e(0.5),
                   shorten=p(0.2, 0.2),
                   routedef='|-')

echo['prefill'] = block("prefill", size=p(5, 4)).left(echo['decouple'], 2)

echo += bus(echo['decouple'].w(0.5), echo['prefill'].e(0.5))

echo['mul'] = mul_block().align(echo['prefill'].w(0.5) - p(4, 0), cur().e(0.5))
echo += bus(echo['prefill'].w(0.5), echo['mul'].e(0.5))
echo += bus_text("feedback").align(echo[-1].pos(0), prev().s(1.0))

echo += bus(echo['mul'].w(0.5), echo['add'].s(0.5), routedef='-|')

echo += bus(echo['mul'].s(0.5),
            poffy(2),
            poffx(-6.5),
            routedef='-|',
            style=(bus_cap, None))
echo += bus_text("feedback_gain").align(echo[-1].pos(1), prev().s())

fig << make_external(echo['add'].w(0.5), direction='i')
fig << bus_text("samples").aligny(echo['add'].w(0.5),
                                  prev().s()).alignx(echo.w(),
                                                     prev().s())

fig << echo

fig << bus(echo['add'].e(0.5), echo['decouple'].n(1.0) + p(4.5, -2))

fig << bus_text("dout").aligny(fig[-1][1],
                               prev().s()).alignx(echo.e(),
                                                  prev().s(1.0))

render_fig(fig)
