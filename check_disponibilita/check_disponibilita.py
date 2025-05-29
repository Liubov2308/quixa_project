from flask import Flask, request, jsonify
from datetime import datetime
import os

app = Flask(__name__)

# Жёстко заданные временные слоты
TIME_SLOTS = [
    "09:00-10:00",
    "10:00-11:00",
    "11:00-12:00"
]

def generate_slot_objects(date_obj, booked_slots=None):
    if booked_slots is None:
        booked_slots = []

    giorni_settimana = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
    day_name = giorni_settimana[date_obj.weekday()]
    date_string = f"{day_name} {date_obj.day} {date_obj.strftime('%B %Y')}"

    return [
        {
            'slot_id': i,
            'time_slot': f"{date_string} alle ore {time}",
            'available': True
        }
        for i, time in enumerate(TIME_SLOTS)
        if i not in booked_slots
    ]

@app.route('/check_disponibilita', methods=['POST'])
def check_disponibilita():
    try:
        data = request.get_json()

        if not data or 'queueName' not in data:
            return jsonify({
                "status": "KO",
                "fasce_disponibilita": [],
                "error": "Missing parameter 'queueName'"
            }), 400

        queue = data['queueName']
        today = datetime.today()
        slots = generate_slot_objects(today)  # Создаём словари слотов

        return jsonify({
            "status": "OK",
            "fasce_disponibilita": slots
        })

    except Exception as e:
        return jsonify({
            "status": "KO",
            "fasce_disponibilita": [],
            "error": f"Server error: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
