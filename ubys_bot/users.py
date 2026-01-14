"""User configuration for UBYS Bot.

Add your users here or use users_config.json file.
Format:
{
    "name": "student_id",
    "password": "password",
    "sapid": "sap_id_url"
}

Get your SAPID URL:
1. Go to https://ubys.omu.edu.tr/
2. Login with your student ID and password
3. Click "Dersler" (Courses)
4. Copy the URL from the address bar
"""

# Example user list (replace with your actual data)
user_list = [
    {
        "name": "YOUR_STUDENT_ID",
        "password": "YOUR_PASSWORD",
        "sapid": "https://ubys.omu.edu.tr/AIS/Student/Class/Index?sapid=YOUR_SAPID_HERE"
    }
]

