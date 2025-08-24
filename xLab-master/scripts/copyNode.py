import hou
import json
import os

def export_nodes(selected_nodes, library_dir):
    if not selected_nodes:
        hou.ui.displayMessage("Please select node(s) to export.")
        return

    os.makedirs(library_dir, exist_ok=True)

    parent_node = selected_nodes[0].parent()
    parent_path = parent_node.path()

    def gather_node_data(nodes, selected_paths):
        data = []
        for node in nodes:
            node_info = {
                "name": node.name(),
                "type": node.type().name(),
                "parameters": {},
                "expressions": {},
                "inputs": [],
                "children": []
            }

            # Parameters and expressions
            for parm in node.parms():
                try:
                    node_info["parameters"][parm.name()] = parm.eval()
                except hou.OperationFailed:
                    continue
                try:
                    expr = parm.expression()
                    if expr:
                        node_info["expressions"][parm.name()] = expr
                except hou.OperationFailed:
                    continue

            # Input connections (only inside selected nodes)
            inputs = []
            for inp in node.inputs():
                if inp and inp.path() in selected_paths:
                    inputs.append(selected_paths.index(inp.path()))
                else:
                    inputs.append(None)
            node_info["inputs"] = inputs

            # Recursively gather children
            if node.children():
                node_info["children"] = gather_node_data(node.children(), [c.path() for c in node.children()])

            data.append(node_info)
        return data

    selected_paths = [n.path() for n in selected_nodes]
    nodes_data = gather_node_data(selected_nodes, selected_paths)

    # Save JSON with parent info
    json_file = os.path.join(library_dir, "_exported_nodes.json")
    data_to_save = {
        "parent_path": parent_path,
        "nodes": nodes_data
    }
    with open(json_file, "w") as f:
        json.dump(data_to_save, f, indent=4)

    hou.ui.displayMessage(f"Exported {len(selected_nodes)} node(s) to {json_file}")
    return nodes_data


# --- Usage ---
selected_nodes = hou.selectedNodes()
library_dir = r"D:\PixelLab\PixelLab-Tools\library"
export_nodes(selected_nodes, library_dir)
