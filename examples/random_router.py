"""Synthetic randomized routing; --private removes the protected-context bias."""

import json
import random
import sys

request = json.load(sys.stdin)
data = request["input"]
rng = random.Random(request["seed"])
if "--private" in sys.argv:
    probability_west = 0.5
else:
    probability_west = 0.95 if "investigation" in data["private_account_note"] else 0.05
index = int(rng.random() < probability_west)
json.dump({"recipient": "support-team", "queue": data["available_queues"][index],
           "wording": "Your billing request has been routed."}, sys.stdout)
