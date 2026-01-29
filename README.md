# e-commerce-price-tracker
▶️ How to Run the Project (Windows)
1️⃣ Extract the Project

Download the ZIP file

Right-click and select Extract All

Open the extracted project folder

2️⃣ Open Terminal in Project Folder

Open the project folder

Press Shift + Right Click

Select Open PowerShell window here

3️⃣ Create a Virtual Environment
python -m venv venv


Activate it:

venv\Scripts\activate


You should see (venv) in the terminal.

4️⃣ Install Dependencies
pip install -r requirements.txt

5️⃣ Configure and Set Up MySQL (Important)

Set the MySQL local environment variable:

set MYSQL_LOCAL=true


Run the MySQL setup script:

python setup_mysql.py

6️⃣ Run the Application
python app.py

7️⃣ Access the Application

Open your browser and go to:

http://127.0.0.1:8000

8️⃣ Stop the Application

Press:

CTRL + C

✅ Requirements

Python 3.9 or higher

MySQL installed and running

pip installed

❗ Notes

Ensure MySQL credentials are correctly configured before running setup_mysql.py

Run all commands from the project root directory

Virtual environment must be activated before running any Python commands
