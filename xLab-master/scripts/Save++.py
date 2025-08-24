import os
import re
import hou

def save_incremental_hip():
    """Save the current Houdini hip file incrementally (v001, v002, ...) 
    without overwriting existing files."""
    
    current_path = hou.hipFile.path()
    hip_dir = hou.getenv("HIP")

    # If unsaved file, start at v001
    if current_path == "untitled.hip" or not current_path:
        new_path = os.path.join(hip_dir, "untitled_v001.hip")
        hou.hipFile.save(new_path)
        print(f"File saved as {new_path}")
        return

    dir_path = os.path.dirname(current_path)
    base_name = os.path.basename(current_path)
    name, ext = os.path.splitext(base_name)

    # Look for version pattern _v### at the end
    match = re.search(r"(.*_v)(\d{3})$", name, re.IGNORECASE)
    if match:
        prefix = match.group(1)
        version_num = int(match.group(2)) + 1
    else:
        prefix = f"{name}_v"
        version_num = 1

    # Find the next available version to avoid overwriting
    while True:
        new_base = f"{prefix}{version_num:03d}{ext}"
        new_path = os.path.join(dir_path, new_base)
        if not os.path.exists(new_path):
            break
        version_num += 1

    # Save the new hip file
    hou.hipFile.save(new_path.replace("\\", "/"))
#    print(f"File saved as {new_path}")

# Run the function
save_incremental_hip()
