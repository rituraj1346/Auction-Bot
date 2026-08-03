# utils/whatsapp_push.py
import os
import requests
import config

def send_whatsapp_report(file_path):
    if not file_path or not os.path.exists(file_path):
        print("Error: Target file summary missing. Aborting WhatsApp push.")
        return

    headers = {"Authorization": f"Bearer {config.WA_TOKEN}"}
    
    print("Uploading generated file to Meta Asset Engine...")
    upload_url = f"https://graph.facebook.com/v20.0/{config.WA_PHONE_ID}/media"
    
    with open(file_path, "rb") as file_bytes:
        files = {"file": (os.path.basename(file_path), file_bytes, "application/pdf")}
        data = {"messaging_product": "whatsapp"}
        response = requests.post(upload_url, headers=headers, files=files, data=data).json()

    if "id" not in response:
        print(f"Meta cloud upload failure payload: {response}")
        return

    media_id = response["id"]
    
    print(f"Asset registered with Media ID: {media_id}. Dispatching template payload to endpoint...")
    send_url = f"https://graph.facebook.com/v20.0/{config.WA_PHONE_ID}/messages"
    
    payload = {
        "messaging_product": "whatsapp",
        "to": config.SEND_TO_NUMBER,
        "type": "template",
        "template": {
            "name": config.WA_TEMPLATE,
            "language": {
                "code": config.WA_LANG
            },
            "components": [
                {
                    "type": "header",
                    "parameters": [
                        {
                            "type": "document",
                            "document": {
                                "id": media_id,
                                "filename": "Auction_Summary.pdf"
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    headers['Content-Type'] = 'application/json'
    delivery_res = requests.post(send_url, headers=headers, json=payload).json()
    print(f"Network processing message confirmation: {delivery_res}")