from werkzeug.security import generate_password_hash

# password = "1234"  # Replace with the actual password you want to use
password = input("Enter password: ")
hashed_password = generate_password_hash(password)
with open("./static/hashed.txt", "a") as file:
    file.write(password+", "+hashed_password+"\n")

print("Hashed password:", hashed_password)