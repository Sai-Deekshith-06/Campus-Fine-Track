#!/bin/bash

# clear
# export dir_path="c:/Desktop/RTFP/new"         # change the path to project where it is residing from root

# cd "$dir_path"

# # Create virtual environment (first time only)
# if [ ! -d "venv" ]; then
#   python -m venv venv
#   echo "Virtual environment created."
# else
#   echo "Virtual environment already exists."
# fi

# # Activate virtual environment (if not already activated)
# if [ -z "$VIRTUAL_ENV" ]; then
#     echo "Virtual environment not active. Activating..."
#     source venv/Scripts/activate
# fi

python.exe -m pip install --upgrade pip

# install all requirements
# pip install -r requirements.txt

# Check and install requirements
while IFS= read -r line; do
    # Ignore comments and empty lines
    if [[ "$line" != "#"* && -n "$line" ]]; then
        package=$(echo "$line" | sed 's/==.*//') # Extract package name
        if pip show "$package" > /dev/null 2>&1; then
            echo "Package '$package' is installed."
        else
            echo "Package '$package' is not installed. Installing..."
            pip install "$line"
            if [ $? -eq 0 ]; then
                echo "Package '$package' installed successfully."
            else
                echo "Failed to install '$line'."
            fi
        fi
    fi
done < requirements.txt
echo "Requirement check and installation complete."

# source code of flask server i.e, 'app.py', to start the server we use,
python app.py