from flask import Flask, request, jsonify
from datetime import datetime, timedelta

app = Flask(__name__)

# Sample storage (replace with DB in production)
waste_items = []
next_id = 1

@app.route("/add_waste", methods=["POST"])
def add_waste():
    global next_id
    data = request.json
    item = {
        "id": next_id,
        "waste_type": data["waste_type"],
        "quantity": float(data["quantity"]),
        "location": data["location"],
        "pickup_time": data["pickup_time"],  # ISO string
        "email": data["email"],
        "status": "pending"
    }
    waste_items.append(item)
    next_id += 1
    return jsonify({"success": True, "item": item})

@app.route("/waste_items", methods=["GET"])
def get_waste_items():
    return jsonify(waste_items)

@app.route("/accept_waste", methods=["POST"])
def accept_waste():
    data = request.json
    for item in waste_items:
        if item["id"] == data["waste_id"]:
            item["status"] = "accepted"
            item["recycler_email"] = data["recycler_email"]
    return jsonify({"success": True})

@app.route("/admin_summary", methods=["GET"])
def admin_summary():
    days = request.args.get("days", type=int)
    filtered = waste_items
    if days:
        cutoff = datetime.now() - timedelta(days=days)
        filtered = [
            i for i in waste_items
            if datetime.fromisoformat(i["pickup_time"]) >= cutoff
        ]

    by_generator, by_type = {}, {}
    for i in filtered:
        by_generator[i["email"]] = by_generator.get(i["email"], 0) + i["quantity"]
        by_type[i["waste_type"]] = by_type.get(i["waste_type"], 0) + i["quantity"]

    return jsonify({"by_generator": by_generator, "by_type": by_type})

if __name__ == "__main__":
    app.run(debug=True)
