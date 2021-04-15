def remove_node(node):
    node.prev[0].next = node.next[:]
    node.next[0].prev = node.prev[:]


def insert_node_before(origin, node):
    i = origin.prev[0].next.index(origin)
    origin.prev[0].next[i] = node

    node.prev = origin.prev[:]

    node.next = [origin]
    origin.prev = [node]

    return node


def insert_node_after(origin, node):
    node.next = origin.next[:]
    node.next[0].prev = [node]

    node.prev = [origin]
    origin.next = [node]

    return node
