import msal
import requests

CLIENT_ID = "4961fe44-d43d-4be6-863e-6bb9e2f68416"

AUTHORITY = "https://login.microsoftonline.com/common"

SCOPES = [
    "User.Read",
    "Mail.ReadWrite"
]

app = msal.PublicClientApplication(
    CLIENT_ID,
    authority=AUTHORITY
)

flow = app.initiate_device_flow(scopes=SCOPES)

if "user_code" not in flow:
    raise Exception("Could not create device login flow")

print(flow["message"])

result = app.acquire_token_by_device_flow(flow)

if "access_token" not in result:
    print("Authentication failed:")
    print(result)
    raise SystemExit(1)

print("\nMicrosoft Graph authentication successful!")

access_token = result["access_token"]

headers = {
    "Authorization": f"Bearer {access_token}"
}

response = requests.get(
    "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
    "?$top=10"
    "&$orderby=receivedDateTime%20DESC"
    "&$select=id,subject,from,receivedDateTime",
    headers=headers
)

print("\nGraph response status:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit(1)

data = response.json()

print("\nLatest emails:\n")

for message in data.get("value", []):
    sender = message.get("from", {}).get("emailAddress", {}).get("address")

    print("--------------------------------")
    print("Subject:", message.get("subject"))
    print("From:", sender)
    print("Received:", message.get("receivedDateTime"))
