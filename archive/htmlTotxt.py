import os

def rename_html_to_txt(html_folder, txt_folder):
    """
    Renames all HTML files in a folder to TXT files and moves them to another folder.
    Overwrites existing files if necessary.
    """
    if not os.path.exists(txt_folder):
        os.makedirs(txt_folder)

    for filename in os.listdir(html_folder):
        if filename.endswith(".html"):
            old_path = os.path.join(html_folder, filename)
            new_filename = filename[:-5] + ".txt"
            new_path = os.path.join(txt_folder, new_filename)

            try:
                if os.path.exists(new_path):
                    os.remove(new_path)
                os.rename(old_path, new_path)
                print(f"Renamed '{filename}' to '{new_filename}'")
            except Exception as e:
                print(f"Error renaming '{filename}': {e}")

def rename_python_to_txt(python_folder, txt_folder, files):
    """
    Renames selected Python files to TXT files and moves them to another folder.
    Overwrites existing files if necessary.
    """
    if not os.path.exists(txt_folder):
        os.makedirs(txt_folder)

    for filename in files:
        if filename.endswith(".py"):
            old_path = os.path.join(python_folder, filename)
            new_filename = filename[:-3] + ".txt"
            new_path = os.path.join(txt_folder, new_filename)

            try:
                if os.path.exists(new_path):
                    os.remove(new_path)
                os.rename(old_path, new_path)
                print(f"Renamed '{filename}' to '{new_filename}'")
            except Exception as e:
                print(f"Error renaming '{filename}': {e}")

# if __name__ == "__main__":
#     html_folder = "./templates"
#     txt_folder = "./ai"
#     python_folder = "."
#     files = ["app.py"]

#     rename_html_to_txt(html_folder, txt_folder)
#     rename_python_to_txt(python_folder, txt_folder, files)
#     print("Renaming complete.")
