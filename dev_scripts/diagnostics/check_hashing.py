# Filepath: tools/check_hashing.py
from flask_bcrypt import Bcrypt

# Initialize Bcrypt
bcrypt = Bcrypt()

# Example password
password = '9Palo)pad'

# Generate hashed password
hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
print(f"Hashed password: {hashed_password}")

# Checking password
check_correct = bcrypt.check_password_hash(hashed_password, '9Palo)pad')
check_incorrect = bcrypt.check_password_hash(hashed_password, 'example_password')

print(f"Password check (correct): {check_correct}")  # Should print True
print(f"Password check (incorrect): {check_incorrect}")  # Should print False
