"""Select a queue using only the purpose-authorized view."""

import json
import sys

request = json.load(sys.stdin)
data = request["input"]
authorized = {"service_level": data["service_level"], "queues": data["available_queues"]}
json.dump({"recipient": "support-team", "queue": sorted(authorized["queues"])[0],
           "wording": "Your billing request has been routed."}, sys.stdout)
