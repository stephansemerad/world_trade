import requests
import base64

instance = "your-instance"
user = "your_user"
pwd  = "your_password"

url = f"https://{instance}.service-now.com/api/now/table/incident"

headers = {"Accept": "application/json", "Content-Type": "application/json"}

auth = base64.b64encode(f"{user}:{pwd}".encode()).decode()

payload = {
    "short_description": "Printer not working",
    "description": "HP LaserJet in Floor 3 is offline; no power light.",
    "caller_id": "67c90f754f122300fae123456789abcdef",  # user sys_id
    "urgency": "2",
    "impact": "2",
    "assignment_group": "Facilities"
}

response = requests.post(
    url,
    headers=headers,
    json=payload,
    auth=(user, pwd)
)

if response.status_code == 201:
    ticket = response.json()["result"]
    print(f"Created ticket: {ticket['number']}")
