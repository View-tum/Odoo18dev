import sys
import subprocess
import os

with open('to_install.txt', 'r') as f:
    to_install = f.read().split(',')

batch_size = 20
for i in range(0, len(to_install), batch_size):
    batch = to_install[i:i+batch_size]
    batch_str = ','.join(batch)
    print(f"Installing batch {i//batch_size + 1}: {batch_str}")
    
    cmd = [
        r'C:\365_project\TheCool18e\Dev\.venv\Scripts\python.exe',
        r'.\server\odoo-bin',
        '-c', r'.\server\odoo.conf',
        '-d', 'GoldMints_Uat_Manu',
        '-i', batch_str,
        '--stop-after-init'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error in batch {i//batch_size + 1}:")
        # Print last 20 lines of error
        print("\n".join(result.stderr.splitlines()[-20:]))
        print("\n".join(result.stdout.splitlines()[-20:]))
    else:
        print(f"Batch {i//batch_size + 1} successful.")
