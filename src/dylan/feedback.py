"""The local backchannel site in Howes & Eshghi (2021), §3.5, Fig. 6.

This is a bounded adaptation of the DS-TTR rule to the native grammars.
It records overt feedback, not inferred participant understanding. Early/late
feedback and the paper's separate participant coordination DAGs are not supplied.
"""


def backchannel_site(tree):
    """Return the compiled unit under the pointer, or why it is not a site.

    The published rule requires a complete node with no complete binary sister,
    forcing ordinary compilation before feedback can be consumed. We additionally
    require a typed formula and a complete subtree. At the clause root, the native
    adaptation records feedback without attempting to move above the root.
    """
    node = tree.pointed_node
    address = node.address
    if (node.get_type() is None or node.get_formula() is None
            or not all(n.is_complete() for a, n in tree.items()
                       if str(a).startswith(str(address)))):
        return None
    parent = address.up()
    if address != tree.root_addr:
        if parent not in tree or str(address)[-1:] not in {"0", "1"}:
            return None
        sister = parent.down1() if str(address).endswith("0") else parent.down0()
        if sister in tree and tree[sister].is_complete():
            return None
    return {
        "node": str(address),
        "type": str(node.get_type()),
        "content": str(node.get_formula()),
        "pointer_after": str(parent if address != tree.root_addr else address),
        "clause_complete": tree.is_complete(),
    }
