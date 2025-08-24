import hou
import os

# ---------------------------
# 1. Load HDA
# ---------------------------

xlab_path = os.environ.get("XLAB")
hda_dir = os.path.join(xlab_path, "nodedata")

hda_files = [f for f in os.listdir(hda_dir) if f.endswith(".hda")]
if not hda_files:
    raise Exception("No HDA files found in folder.")

selected_index = hou.ui.selectFromList(hda_files, message="Select HDA", exclusive=True)
if not selected_index:
    raise Exception("No HDA selected")

selected_hda = hda_files[selected_index[0]]
hda_path = os.path.join(hda_dir, selected_hda)

# Temporarily load HDA
hou.hda.installFile(hda_path)

definitions = hou.hda.definitionsInFile(hda_path)
if not definitions:
    raise Exception("No definitions found in HDA file")

hda_def = definitions[0]
node_type_name = hda_def.nodeTypeName()

# ---------------------------
# 2. Detect parent network from filename
# ---------------------------

parts = selected_hda.split("_")
if len(parts) >= 2:
    namespace_name = parts[1]  # Assuming second part is namespace
    parent = hou.node("/" + namespace_name)
    if parent is None:
        print(f"Namespace '{namespace_name}' not found. Using /obj instead.")
        parent = hou.node("/obj")
else:
    parent = hou.node("/obj")

# ---------------------------
# 3. Create HDA node
# ---------------------------

hda_node = parent.createNode(node_type_name)
hda_node.moveToGoodPosition()
print(f"HDA loaded and node created: {hda_node.path()}")

# ---------------------------
# 4. Unlock and extract internal nodes with connections
# ---------------------------

hda_node.allowEditingOfContents()
internal_nodes = hda_node.children()

if not internal_nodes:
    print("HDA is empty, nothing to copy.")
else:
    # Map original node -> copied node
    node_map = {}
    for n in internal_nodes:
        copied = n.copyTo(parent)
        copied.moveToGoodPosition()
        node_map[n] = copied

    # Recreate connections
    for orig_node in internal_nodes:
        copied_node = node_map[orig_node]
        for i, input_node in enumerate(orig_node.inputs()):
            if input_node in node_map:
                copied_node.setInput(i, node_map[input_node])

    print(f"Copied {len(internal_nodes)} nodes with connections to {parent.path()}.")

# ---------------------------
# 5. Delete original HDA node
# ---------------------------

hda_node.destroy()
print("Original HDA node deleted.")
