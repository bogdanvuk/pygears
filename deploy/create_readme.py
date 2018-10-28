import re
import os

re_ref = ':ref:`([^<]+)\s<([^>]+)>`'


def ref_replace(matchobj):
    page_name = matchobj.group(2).split('-')[0]
    return (f'`{matchobj.group(1)}'
            f' <https://www.pygears.org/{page_name}.html'
            f'#{matchobj.group(2)}>`_')


os.chdir('../docs/manual')

meta_tag = False

with open('index.rst', 'r') as fin:
    with open('../../README.rst', 'w') as fout:

        for line in fin:
            if line == "Contents\n":
                break

            if line.startswith('.. meta'):
                meta_tag = True

            if meta_tag:
                if line == "\n":
                    meta_tag = False

                continue

            line_subs = re.sub(re_ref, ref_replace, line)
            fout.write(line_subs)
