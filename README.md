# System_Utilities
Utility scripts for administration of Linux systems

check_messages_msm.py: This script scans /var/log/messages for messages from the MegaRAID Storage Manager. Usually run as a cron job (e.g., hourly) if the email message setup in MSM doesn't work for any reason. Trivial events (fan speed and power state changes) are ignored, all others are sent as an email to root.

check_compute_nodes.py: This script checks the status of the compute nodes of a cluster and sends an email to root if there are any problems (nodes down).

monitor_core_temps.py: This script checks the temperatures of CPUs and cores, logs them in a csv file, creates daily plots, and sends an email to root if a set maximum temperature is exceeded.
