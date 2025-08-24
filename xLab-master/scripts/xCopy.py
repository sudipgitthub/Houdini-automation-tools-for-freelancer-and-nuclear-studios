import hou
import os
from datetime import datetime

# Get selected nodes
nodes = hou.selectedNodes()
if not nodes:
    raise Exception("No nodes selected")

# Ensure all nodes are from the same parent
parent = nodes[0].parent()

# Get namespace (parent path)
namespace = parent.path().replace("/", "_").strip("_")

# Get current date & time
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Create a subnet at the same level
subnet_name = f"multiNode_{namespace}_{timestamp}_subnet"
subnet = parent.createNode("subnet", subnet_name)

# Dictionary to map original node -> copied node
node_map = {}

# Copy nodes into the subnet
for node in nodes:
    copied = node.copyTo(subnet)
    copied.setName(node.name(), unique_name=True)
    copied.moveToGoodPosition()
    node_map[node] = copied

# Recreate connections inside the subnet
for node in nodes:
    copied_node = node_map[node]
    for i in range(node.inputs().__len__()):
        input_node = node.input(i)
        if input_node in node_map:
            copied_node.setInput(i, node_map[input_node])

# Layout subnet contents
subnet.layoutChildren()

# Prepare export path
xlab_path = os.environ.get("XLAB")
if not xlab_path:
    raise Exception("XLAB environment variable not set")
export_dir = os.path.join(xlab_path, "nodedata")
os.makedirs(export_dir, exist_ok=True)

# Define HDA path
hda_path = os.path.join(export_dir, subnet.name() + ".hda")

# Create HDA from the subnet and ignore external references
subnet.createDigitalAsset(
    name=subnet.name(),
    hda_file_name=hda_path,
    description="Exported multiple nodes via script (with connections)",
    ignore_external_references=True
)

print(f"HDA exported to: {hda_path}")
print(f"Namespace: {namespace}")
print(f"Timestamp: {timestamp}")
