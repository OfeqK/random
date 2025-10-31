import hashlib
import os
import sqlite3

DB_NAME = "WhisprDB.db"

def connect_to_db(db_name: str) -> sqlite3.Connection:
	"""
	Connects to the given database. If none exists, it creates a new one.
	:param db_name:
	:return: Connection object that represents the connection to the on-disk database.
	"""
	if not isinstance(db_name, str):
		raise TypeError(f"db_name must be of type string\n\tProvided: {db_name}")

	return sqlite3.connect(db_name)

def create_users_table(db_name: str=DB_NAME):
	"""
	Creates the users table in the provided db
	:param db_name: The database to connect to
	:return:
	"""
	if not isinstance(db_name, str):
		raise TypeError(f"db_name must be of type string\n\tProvided: {db_name}")

	try:
		with sqlite3.connect(db_name) as conn:
			cur = conn.cursor()
			cur.execute("""
	                CREATE TABLE IF NOT EXISTS users (
	                    id INTEGER PRIMARY KEY,
	                    name TEXT UNIQUE NOT NULL,
	                    salt TEXT,
	                    hashed_pwd TEXT NOT NULL
	                )
	            """)
			# we store the salt.hex() and hashed_pwd.hexdigest()
			conn.commit()

			# make sure that the table has been created
			res = cur.execute("SELECT name FROM sqlite_master")
			if "users" not in list(res.fetchone()):
				raise RuntimeError("An error occurred whilst creating table 'users' in function create_users_table")
	except Exception as e:
		print(f"[ ERROR ] Failed to create users table: {e}")
		raise

def hash_password(password: str) -> tuple[str, str]:
	"""
	Hashes a password using SHA256 with a randomly generated salt.
	:param password: The original password to be hashed.
	:return: A tuple: (salt, hashed_pwd) both are str.
	"""
	if not isinstance(password, str):
		raise TypeError(f"password must be of type string\n\tProvided: {password}")

	salt = os.urandom(16) # random 16 byte salt

	# hash using SHA256 algorithm
	hashed_password = hashlib.sha256(salt + password.encode()).hexdigest()
	return salt.hex(), hashed_password

def verify_password(stored_salt: str, stored_hashed_password: str, provided_password: str) -> bool:
	"""
	Verifies a provided password against a stored salt and hashed password.
	:param stored_salt: The stored salt in the database
	:param stored_hashed_password: The stored hashed password in the database
	:param provided_password: The password to check if it equals or not
	:return: True if the provided password matches the stored hashed one. False otherwise
	"""
	if not isinstance(stored_salt, str):
		raise TypeError(f"stored_salt must be of type string\n\tProvided: {stored_salt}")
	if not isinstance(stored_hashed_password, str):
		raise TypeError(f"stored_hashed_password must be of type string\n\tProvided: {stored_hashed_password}")
	if not isinstance(provided_password, str):
		raise TypeError(f"provided_password must be of type string\n\tProvided: {provided_password}")

	salt = bytes.fromhex(stored_salt)

	hashed_provided_password = hashlib.sha256(salt + provided_password.encode()).hexdigest()
	return hashed_provided_password == stored_hashed_password


def add_user(user_name: str, salt: str, hashed_password: str, db_name: str=DB_NAME) -> bool:
	"""
	Adds the new user to the database
	:param db_name: The database to connect to
	:param user_name: The user's name
	:param salt: The salt used to hash the password
	:param hashed_password: The user's hashed password based on the given salt and hashing algorithm
	:return: True if user added successfully, False otherwise.
	"""
	if not all(isinstance(arg, str) for arg in [db_name, user_name, salt, hashed_password]):
		raise TypeError("db_name, user_name, salt, and hashed_password must all be strings")

	try:
		with sqlite3.connect(db_name) as conn:
			# usernames are unique
			if check_if_user_exists(user_name, db_name):
				print(f"[ DATABASE ] User '{user_name}' already exists.")
				return False

			cur = conn.cursor()
			cur.execute(
				"INSERT INTO users (name, salt, hashed_pwd) VALUES (?, ?, ?)",
				(user_name, salt, hashed_password)
			)
			conn.commit()
			print(f"[ DATABASE ] User '{user_name}' added successfully.")
			return True
	except Exception as e:
		print(f"[ ERROR ] Failed to add user '{user_name}': {e}")
		return False


def check_if_user_exists(user_name: str, db_name: str=DB_NAME) -> bool:
	"""
	Checks if the provided user exists in the database.
	:param db_name: The database to connect to
	:param user_name: The user's name
	:return: True if the user exists in the database. False otherwise.
	"""
	if not isinstance(db_name, str):
		raise TypeError(f"db_name must be of type string\n\tProvided: {db_name}")
	if not isinstance(user_name, str):
		raise TypeError(f"user_name must be of type string\n\tProvided: {user_name}")

	try:
		with sqlite3.connect(db_name) as conn:
			cur = conn.cursor()
			cur.execute("SELECT COUNT(*) FROM users WHERE name = ?", (user_name,))
			count = cur.fetchone()[0]
			return count > 0
	except Exception as e:
		print(f"[ ERROR ] Failed to check if user exists: {e}")
		return False

def authenticate_user(user_name: str, provided_password: str, db_name: str=DB_NAME) -> bool:
	"""
	Checks if the user's password matches the one in the database.
	:return: True if the user's credentials match the ones in the database. False otherwise
	"""
	if not all(isinstance(arg, str) for arg in [db_name, user_name, provided_password]):
		raise TypeError("db_name, user_name and provided_password must all be strings")

	try:
		with sqlite3.connect(db_name) as conn:
			cur = conn.cursor()
			cur.execute("SELECT salt, hashed_pwd FROM users WHERE name = ?", (user_name,))
			result = cur.fetchone()

			if result is None:
				print(f"[ DATABASE ] User '{user_name}' not found.")
				return False

			stored_salt, stored_hashed_pwd = result
			if verify_password(stored_salt, stored_hashed_pwd, provided_password):
				print(f"[ DATABASE ] User '{user_name}' authenticated successfully.")
				return True
			else:
				print(f"[ DATABASE ] Authentication failed for user '{user_name}'.")
				return False
	except Exception as e:
		print(f"[ ERROR ] Failed to authenticate user '{user_name}': {e}")
		return False
