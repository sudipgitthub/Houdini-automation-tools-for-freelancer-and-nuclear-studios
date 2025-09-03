import hou
import os
import time

# ---------------------------
# 1. Load HDA (sorted by date)
# ---------------------------

xlab_path = os.environ.get("XLAB")
hda_dir = os.path.join(xlab_path, "nodedata")

# Collect .hda files with timestamps
hda_files = [
    (f, os.path.getmtime(os.path.join(hda_dir, f)))
    for f in os.listdir(hda_dir) if f.endswith(".hda")
]
if not hda_files:
    raise Exception("No HDA files found in folder.")

# Sort newest first
hda_files.sort(key=lambda x: x[1], reverse=True)

# Build display list: filename + timestamp
hda_display_list = [
    f"{fname}   [{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))}]"
    for fname, mtime in hda_files
]

# Show selection window
selected_index = hou.ui.selectFromList(hda_display_list, message="Select HDA", exclusive=True)
if not selected_index:
    raise Exception("No HDA selected")

# Get chosen HDA
selected_hda = hda_files[selected_index[0]][0]
hda_path = os.path.join(hda_dir, selected_hda)

# ---------------------------
# 2. Install HDA temporarily
# ---------------------------

hou.hda.installFile(hda_path)
definitions = hou.hda.definitionsInFile(hda_path)
if not definitions:
    raise Exception("No definitions found in HDA file")

hda_def = definitions[0]
node_type_name = hda_def.nodeTypeName()

# ---------------------------
# 3. Detect parent network from filename
# ---------------------------

parts = selected_hda.split("_")

# Scan each part of filename to find a valid network
parent = None
for part in parts:
    candidate = hou.node("/" + part)
    if candidate:
        parent = candidate
        break

if parent is None:
    parent = hou.node("/obj")
    print("No matching namespace found in filename, using /obj instead.")

# ---------------------------
# 4. Create HDA node
# ---------------------------

hda_node = parent.createNode(node_type_name)
hda_node.moveToGoodPosition()
print(f"HDA loaded and node created: {hda_node.path()}")

# ---------------------------
# 5. Unlock and extract internal nodes with connections
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
# 6. Delete original HDA node
# ---------------------------

hda_node.destroy()
print("Original HDA node deleted.")

# ---------------------------
# 7. Uninstall HDA definition (so it's not permanently available)
# ---------------------------

hou.hda.uninstallFile(hda_path)
print(f"HDA {selected_hda} uninstalled after import.")
