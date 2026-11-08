from argon2 import PasswordHasher, Type

# Argon2id; the library generates a fresh random salt for each password.
password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
