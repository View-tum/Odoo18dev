import sys
try:
    import psutil
except ImportError:
    print("psutil not found, using subprocess and taskkill")
    import subprocess
    output = subprocess.check_output(['wmic', 'process', 'get', 'ProcessId,CommandLine']).decode('utf-8', errors='ignore')
    killed = 0
    for line in output.splitlines():
        if 'odoo-bin' in line.lower() or 'odoo.py' in line.lower():
            parts = line.strip().split()
            if parts:
                pid = parts[-1]
                if pid.isdigit():
                    print(f"Killing PID {pid}: {line.strip()[:60]}...")
                    subprocess.call(['taskkill', '/F', '/PID', pid])
                    killed += 1
    print(f"Done! Killed {killed} Odoo processes.")
    sys.exit(0)

print("Scanning for Odoo processes using psutil...")
killed_count = 0

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info.get('cmdline')
        if cmdline:
            cmd_str = ' '.join(cmdline).lower()
            if 'odoo-bin' in cmd_str or 'odoo.py' in cmd_str:
                print(f"Killing PID {proc.info['pid']}: {cmd_str[:80]}...")
                proc.kill()
                killed_count += 1
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass

print(f"\nDone! Killed {killed_count} Odoo processes.")
