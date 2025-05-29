from flask import Flask, request, jsonify
from datetime import datetime
import random
import os

app = Flask(__name__)

time_slots = ["11:00", "14:00", "16:00"]

def generate_slots(date_obj, count=3):
    giorni_settimana = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    day_name = giorni_settimana[date_obj.weekday()]
    return [
        f"{day_name} {date_obj.day} {date_obj.strftime('%B %Y')} alle ore {time}"
        for time in time_slots[:count]
    ]

@app.route('/check_disponibilita', methods=['POST'])
def check_disponibilita():
    data = request.get_json()

    queue = data.get('queueName')
    response_set = data.get('responseSet', 1)

    # Определим дату прямо здесь
    today = datetime.today()
    date_str = today.strftime("%Y-%m-%d")

    # Имитация ошибки
    if random.choice([True, False, True]):
        slots = generate_slots(today)

        return jsonify({
            "status": "OK",
            "fasce_disponibilita": slots if random.choice([True, False]) or response_set == 2 else []
        })
    else:
        return jsonify({
            "status": "KO",
            "fasce_disponibilita": []
        })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

