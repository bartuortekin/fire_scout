# FireScout FS-01 — Backup Files

This directory contains previous versions of FireScout configuration and robot model files.

These files are preserved for troubleshooting, comparison, and recovery purposes.

## Available Backups

| File | Description |
|---|---|
| `config/bridge.yaml.bak` | Previous ROS 2 / Gazebo bridge configuration |
| `launch/simulation.launch.py.bak_original` | Original launch file before VMware/native mode support |
| `urdf/firescout.urdf.xacro.bak_before_contact_fix` | Robot model before the contact sensor collision fix |
| `urdf/firescout.urdf.xacro.bak_before_lidar_fix` | Robot model before the LiDAR positioning fix |

## Important Notes

- The active and updated ROS 2 files are located in `firescout_fs01/`.
- Backup files are not automatically used by the simulation.
- Older versions may contain issues that were corrected in later versions.
- Always preserve the current working file before restoring a backup.

## Restoring a Backup

To restore an older version, copy the desired backup over its corresponding active file.

For example, the original launch file can be restored using:

    cp backups/launch/simulation.launch.py.bak_original firescout_fs01/launch/simulation.launch.py

Run restoration commands from the repository root.

Restoring a backup may remove newer fixes. Rebuild and retest the affected components after restoration.
