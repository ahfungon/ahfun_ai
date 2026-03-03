import subprocess
import shutil

print('=== Testing Worker Detection ===')

# Method 1: systemctl
print('\n1. Testing systemctl:')
try:
    result = subprocess.run(
        ['systemctl', 'is-active', 'dual-agent-celery'],
        capture_output=True,
        text=True,
        timeout=2
    )
    print(f'   Return code: {result.returncode}')
    print(f'   Stdout: {result.stdout.strip()}')
    print(f'   Stderr: {result.stderr.strip()}')
    if result.returncode == 0 and result.stdout.strip() == 'active':
        print('   ✅ Worker detected by systemctl')
    else:
        print('   ❌ Worker NOT detected by systemctl')
except Exception as e:
    print(f'   ❌ Exception: {e}')

# Method 2: pgrep
print('\n2. Testing pgrep:')
try:
    pgrep_path = shutil.which('pgrep')
    print(f'   pgrep path: {pgrep_path}')
    if pgrep_path:
        result = subprocess.run(
            [pgrep_path, '-f', 'celery.*worker'],
            capture_output=True,
            timeout=2
        )
        print(f'   Return code: {result.returncode}')
        print(f'   Stdout: {result.stdout.strip()}')
        print(f'   Stderr: {result.stderr.strip()}')
        if result.returncode == 0 and result.stdout.strip():
            print('   ✅ Worker detected by pgrep')
        else:
            print('   ❌ Worker NOT detected by pgrep')
    else:
        print('   ❌ pgrep not found')
except Exception as e:
    print(f'   ❌ Exception: {e}')

# Method 3: Celery inspect
print('\n3. Testing Celery inspect:')
try:
    import sys
    sys.path.insert(0, '/home/ubuntu/dual-agent-chat')
    from celery_app import celery_app
    inspect = celery_app.control.inspect(timeout=2.0)
    active_workers = inspect.active()
    print(f'   Active workers: {active_workers}')
    if active_workers:
        print('   ✅ Worker detected by Celery inspect')
    else:
        print('   ❌ Worker NOT detected by Celery inspect')
except Exception as e:
    print(f'   ❌ Exception: {e}')
