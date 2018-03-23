import re
re_space_rem = re.compile(r"^\s+", re.MULTILINE)


def equal_on_nonspace(str1, str2):
    return re_space_rem.sub('', str1.strip()) == re_space_rem.sub(
        '', str2.strip())
