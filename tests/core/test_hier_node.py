from pygears.core.hier_node import NamedHierNode


def test_unique_renaming():
    child_names = ['stem', 'stem', 'stem1', 'stem01', 'stem1_2']
    root = NamedHierNode('')
    for n in child_names:
        NamedHierNode(n, root)

    renames = [c.basename for c in root.child]
    print(renames)
    assert renames == ['stem0', 'stem2', 'stem1', 'stem01', 'stem1_2']
