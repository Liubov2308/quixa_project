from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# Подключение к локальной MongoDB (если меняем на облако - изменим строку позже)
client = MongoClient("mongodb+srv://admin:admin123@cluster0.mfgmbey.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

db = client["quixa"]
collection = db["quixa_collection"]

@app.route("/check_polizza", methods=["POST"])
def check_polizza():
    data = request.json
    numero = data.get("numero_polizza")

    polizza = collection.find_one({"numero_polizza": numero})

    if not polizza:
        return jsonify({"status": 404, "error": "Polizza non trovata"})

    today = datetime.utcnow()
    stato = polizza["stato"]
    scadenza = datetime.fromisoformat(polizza["data_scadenza"].replace("Z", ""))

    if stato == "attiva":
        tipo_cliente = "CLIENT"
    elif stato == "preventivo" and scadenza > today:
        tipo_cliente = "PROSPECT GREEN"
    else:
        tipo_cliente = "PROSPECT RED"

    return jsonify({
        "status": 200,
        "tipo_cliente": tipo_cliente,
        "polizza_prefix": numero[:4]
    })

if __name__ == "__main__":
    app.run(debug=True)
