with open('_build/latex/gears_paper.tex') as outfile:
    sphinx_out = outfile.read()

with open('_build/latex/gears_paper.tex', 'w') as outfile:
    with open('tex/ieee.tex') as template:
        outfile.write(template.read())

    discard = True
    for line in sphinx_out.split('\n'):
        if line == r"\begin{abstract}":
            discard = False

        if line == r"\section{References}":
            line = r""

        if not discard:
            outfile.write(line)
            outfile.write('\n')
