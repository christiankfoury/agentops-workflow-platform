"""Stable branch identities for already validated, closed fork/join regions."""


def branch_paths(graph):
    nodes = {node.id: node for node in graph.nodes}
    outgoing = {key: [edge.target for edge in graph.edges if edge.source == key] for key in nodes}
    paths = {}

    def visit(key, stop, path):
        if key == stop:
            return
        if len(path) > 256:
            raise ValueError("Nested branch identity exceeds 256 characters")
        if key in paths:
            if paths[key] != path:
                raise ValueError("Node crosses a declared parallel branch boundary")
            return
        paths[key] = path
        node = nodes[key]
        if node.type == "parallel" and node.config.mode == "fork":
            for branch in node.config.branches:
                visit(branch.entry_node, node.config.join_node, f"{path}/{key}:{branch.name}")
            visit(node.config.join_node, stop, path)
        else:
            for target in outgoing[key]:
                visit(target, stop, path)

    visit(graph.entry_node, None, "main")
    return paths


def has_parallel(graph):
    return any(node.type == "parallel" for node in graph.nodes)
