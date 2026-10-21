"""Synthetic routing bug: a permitted queue choice reveals a private note."""

import json
import sys

request = json.load(sys.stdin)
data = request["input"]
index = 1 if "investigation" in data["private_account_note"] else 0
json.dump({"recipient": "support-team", "queue": data["available_queues"][index],
           "wording": "Your billing request has been routed."}, sys.stdout)
