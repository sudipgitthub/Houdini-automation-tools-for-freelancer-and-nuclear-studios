# Houdini automation tools for freelancer and nuclear studios


Some Automation and Pipeline tool for houdini 20+ python 3.7 Windows Only // not tested on Linux

Description: (HOUDINI_PACKAGE_DIR = /some_root_directory)

Set an environment variable HOUDINI_PACKAGE_DIR to point to the root directory (e.g., /some_root_directory/).
The PLab_package.json file, located in the root directory alongside PLab-Tools, uses this variable to define paths inside the package.
Inside PLab-Tools, the MainMenuCommon.xml file configures menus for Houdini.
The subfolders ffmpeg, otls, and scripts contain respective tools, libraries, and scripts used by the PixelLab tools.
This setup allows Houdini to correctly load and access the PLab tools and their dependencies.



After sussecfully setting up the path and Enviroment variable you will find new menu called PLab


<img width="1024" height="1536" alt="imagefolderstruture" src="https://github.com/user-attachments/assets/b5ecf567-c962-466b-a9a7-3f5da47ef66e" />



Here is some working principles called Houdini Lab tool ~

Home Page:
Serves as the main dashboard providing quick access to key project information and workflow tools. It includes sections for camera listing, grouped nodes by parent type, and cache tree visualization. The page supports refreshing content to keep data current. It acts as a central hub to navigate and manage scene elements efficiently within Houdini
<img width="904" height="598" alt="Screenshot 2025-08-16 223345" src="https://github.com/user-attachments/assets/13a391af-8c38-4065-85bc-667bc8386370" />


Flipbook Page:
Provides an interactive viewer for image sequences (flipbooks) generated within Houdini. It scans a specified flipbook directory for image sequences, listing them with details like frame ranges and total frames. Users can select sequences to preview, and control playback with play, pause, stop, and navigation buttons. The interface updates dynamically and integrates smoothly with Houdini workflows for quick visual feedback on rendered sequences.

Browser Navigator:<img width="909" height="593" alt="Screenshot 2025-08-16 223447" src="https://github.com/user-attachments/assets/f3b20f61-3e96-4dee-90e5-056ac3e1c68d" />

A multi-level dropdown browser lets users navigate project directories hierarchically (Project Type → Project → Shots → Sequence → Shot → Task). It displays the current path, folder contents, and allows browsing, selecting, and opening folders or files directly. Double-clicking supports loading Houdini scenes (.hip), Alembic (.abc), or other geometry files into Houdini nodes.

Deadline Job Monitor:
Integrates with Thinkbox Deadline render farm software to load, filter (by user, date, and search), and manage jobs in real-time with optional auto-refresh. Displays comprehensive job info including progress bars, statuses, frame ranges, priorities, submission times, and output paths. Users can suspend, resume, delete jobs, and view detailed job metadata via context menus or selection

happy houdining !!!
