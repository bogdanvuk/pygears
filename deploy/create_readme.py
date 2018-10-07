import re
import os

re_ref = ':ref:`([^<]+)\s<([^>]+)>`'


def ref_replace(matchobj):
    page_name = matchobj.group(2).split('-')[0]
    return (f'`{matchobj.group(1)}'
            f' <https://www.pygears.org/{page_name}.html'
            f'#{matchobj.group(2)}>`_')


os.chdir('../docs/manual')

with open('index.rst', 'r') as fin:
    with open('../../README.rst', 'w') as fout:
        for line in fin:
            if line == "Contents\n":
                break

            line_subs = re.sub(re_ref, ref_replace, line)
            fout.write(line_subs)
