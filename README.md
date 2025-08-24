# Houdini automation tools for freelancer and nuclear studios


Some Automation and Pipeline tool for houdini 20+ python 3.7 Windows Only // not tested on Linux

Description: (HOUDINI_PACKAGE_DIR = /some_root_directory)

Set an environment variable HOUDINI_PACKAGE_DIR to point to the root directory (e.g., /some_root_directory/).
The PLab_package.json file, located in the root directory alongside xLab-master, uses this variable to define paths inside the package.
Inside xLab-master, the MainMenuCommon.xml file configures menus for Houdini.
The subfolders ffmpeg, otls, and scripts contain respective tools, libraries, and scripts used by the xlab tools.
This setup allows Houdini to correctly load and access the PLab tools and their dependencies.

After sussecfully setting up the path and Enviroment variable you will find new menu called xLab


<img width="904" height="1336" alt="Image Aug 24, 2025, 12_12_06 PM" src="https://github.com/user-attachments/assets/c86cdb1f-1bbc-477a-9345-46c2422c8b97" />

Here is some working principles called Houdini Lab tool ~

Home Page:
Serves as the main dashboard providing quick access to key project information and workflow tools. It includes sections for camera listing, grouped nodes by parent type, and cache tree visualization. The page supports refreshing content to keep data current. It acts as a central hub to navigate and manage scene elements efficiently within Houdini

<img width="904" height="598" alt="Screenshot 2025-08-16 223345" src="https://github.com/user-attachments/assets/526962c9-d5aa-42e1-8e26-056639c560fb" />


Flipbook Page:
Provides an interactive viewer for image sequences (flipbooks) generated within Houdini. It scans a specified flipbook directory for image sequences, listing them with details like frame ranges and total frames. Users can select sequences to preview, and control playback with play, pause, stop, and navigation buttons. The interface updates dynamically and integrates smoothly with Houdini workflows for quick visual feedback on rendered sequences.

<img width="909" height="593" alt="Screenshot 2025-08-16 223447" src="https://github.com/user-attachments/assets/16edb00c-6595-4346-ab61-0228dae06747" />

A multi-level dropdown browser lets users navigate project directories hierarchically (Project Type → Project → Shots → Sequence → Shot → Task). It displays the current path, folder contents, and allows browsing, selecting, and opening folders or files directly. Double-clicking supports loading Houdini scenes (.hip), Alembic (.abc), or other geometry files into Houdini nodes.

Deadline Job Monitor:
Integrates with Thinkbox Deadline render farm software to load, filter (by user, date, and search), and manage jobs in real-time with optional auto-refresh. Displays comprehensive job info including progress bars, statuses, frame ranges, priorities, submission times, and output paths. Users can suspend, resume, delete jobs, and view detailed job metadata via context menus or selection

happy houdining !!!
