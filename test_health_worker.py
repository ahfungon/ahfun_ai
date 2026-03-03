import subprocess
import shutil

print('=== Testing Worker Detection in Health Check ===\n')

worker_running = False
detection_method = 'unknown'

# Method 1: systemctl
print('Method 1: systemctl')
try:
    result = subprocess.run(
        ['systemctl', 'is-active', 'dual-agent-celery'],
        capture_output=True,
        text=True,
        timeout=2
    )
    print(f'  returncode: {result.returncode}')
    print(f'  stdout: {repr(result.stdout)}')
    print(f'  stdout.strip(): {repr(result.stdout.strip())}')
    print(f'  Check: returncode==0: {result.returncode == 0}')
    print(f'  Check: stdout.strip()=="active": {result.stdout.strip() == "active"}')
    
    if result.returncode == 0 and result.stdout.strip() == 'active':
        worker_running = True
        detection_method = 'systemd'
        print('  ✅ DETECTED by systemctl')
    else:
        print('  ❌ NOT detected by systemctl')
except Exception as e:
    print(f'  ❌ Exception: {e}')

# Method 2: pgrep
print('\nMethod 2: pgrep')
if not worker_running:
    try:
        pgrep_path = shutil.which('pgrep')
        print(f'  pgrep_path: {pgrep_path}')
        if pgrep_path:
            result = subprocess.run(
                [pgrep_path, '-f', 'celery.*worker'],
                capture_output=True,
                timeout=2
            )
            print(f'  returncode: {result.returncode}')
            print(f'  stdout type: {type(result.stdout)}')
            print(f'  stdout length: {len(result.stdout)}')
            print(f'  stdout: {repr(result.stdout[:100])}...')
            print(f'  Check: returncode==0: {result.returncode == 0}')
            print(f'  Check: len(stdout)>0: {len(result.stdout) > 0}')
            
            if result.returncode == 0 and len(result.stdout) > 0:
                worker_running = True
                detection_method = 'pgrep'
                print('  ✅ DETECTED by pgrep')
            else:
                print('  ❌ NOT detected by pgrep')
    except Exception as e:
        print(f'  ❌ Exception: {e}')
else:
    print('  (skipped, already detected)')

print(f'\n=== RESULT ===')
print(f'worker_running: {worker_running}')
print(f'detection_method: {detection_method}')
