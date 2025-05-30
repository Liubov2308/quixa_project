from flask import Flask, request, jsonify
from datetime import datetime
from pymongo import MongoClient
import os

app = Flask(__name__)

mongo_uri = os.environ.get("MONGO_URI")
client = MongoClient(mongo_uri)

db = client["quixa"]
collection = db["bookings"]

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


@app.route('/find_booking_by_phone', methods=['POST'])
def find_booking_by_phone():
    try:
        data = request.get_json()
        phone = data.get("phoneNumber")
        
        booking = collection.find_one({"phoneNumber": phone})

        if booking:
            return jsonify({
                "returnCode": 200,
                "reservationId": str(booking.get("_id")),
                "queueName": booking.get("queueName"),
                "dateReservation": booking.get("dateReservation"),
                "bookingInfo": booking.get("bookingInfo"),
                "email": booking.get("email")
            })
        else:
            return jsonify({
                "returnCode": 404,
                "error": "Booking not found"
            })

    except Exception as e:
        return jsonify({
            "returnCode": 500,
            "error": str(e)
        }), 500


@app.route('/save_booking', methods=['POST'])
def save_booking():
    try:
        data = request.get_json()

        slot = data.get("bookingInfo")
        queue = data.get("queueName")
        user = data.get("userName")
        phone = data.get("phoneNumber")
        email = data.get("emailUtente")

        timestamp = int(datetime.now().timestamp())

        # Сохраняем бронь
        collection.insert_one({
            "userName": user,
            "queueName": queue,
            "bookingInfo": slot,
            "phoneNumber": phone
            "email": email,
            "dateReservation": timestamp
        })

        return jsonify({"status": "OK", "message": "Booking saved successfully"})

    except Exception as e:
        return jsonify({"status": "KO", "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
