from app.auth.hashing import (
    hash_password,
    verify_password,
)

password = "LabGenius123"

hashed = hash_password(password)

print("Hash:")
print(hashed)

print()

print("Verification:")
print(verify_password(password, hashed))