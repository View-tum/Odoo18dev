import os
import signal
import subprocess

def kill_odoo_processes():
    try:
        # Get all processes via wmic
        output = subprocess.check_output('wmic process get ProcessId,CommandLine', shell=True).decode('utf-8', errors='ignore')
        
        killed = 0
        for line in output.splitlines():
            line_lower = line.lower()
            if 'odoo-bin' in line_lower or 'odoo.py' in line_lower:
                if 'kill_odoo' not in line_lower and 'wmic' not in line_lower:
                    parts = line.strip().split()
                    if parts:
                        pid_str = parts[-1]
                        if pid_str.isdigit():
                            pid = int(pid_str)
                            print(f"Killing Odoo process PID: {pid}")
                            try:
                                # Use taskkill for Windows
                                subprocess.call(['taskkill', '/F', '/PID', str(pid)])
                                killed += 1
                            except Exception as e:
                                print(f"Failed to kill PID {pid}: {e}")
                                
        if killed == 0:
            print("No Odoo processes found running.")
        else:
            print(f"Done! Killed {killed} Odoo processes.")
    except Exception as e:
        print(f"Error checking processes: {e}")

if __name__ == '__main__':
    kill_odoo_processes()
