import subprocess

cp = subprocess.run(["keepassxc-cli", "locate", "-q", "/home/peter/SynologyDrive/passwords/Passwords.kdbx", "amex"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, input=b"passwordhere")

print(cp.returncode)
print(cp.stdout)
print(cp.stderr)
