from flask import Flask, request, jsonify
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
import os
import re
from flask_cors import CORS
import calendar
from datetime import datetime

app = Flask(__name__)
CORS(app)

mongo_uri = os.environ.get("MONGO_URI")
client = MongoClient(mongo_uri)

db = client["quixa"]
collection = db["bookings"]
available_slots = db["available_slots"]

def normalize_phone(phone):
    # Удаляем все символы, кроме цифр
    phone = str(phone)
    digits_only = re.sub(r"\D", "", phone)

    # Если начинается с 39 — уже есть код страны
    if digits_only.startswith("39"):
        return "+" + digits_only
    else:
        return "+39" + digits_only.lstrip("0")

def parse_booking_info(text):
    try:
        # "Lunedì 3 Giugno 2025 alle ore 10:00"
        parts = text.split(" alle ore ")
        if len(parts) != 2:
            return None, None

        time_part = parts[1].strip()
        date_part = parts[0].strip()

        # Удаляем день недели (первое слово)
        tokens = date_part.split(" ")
        if len(tokens) < 4:
            return None, None

        day = int(tokens[1])
        month_str = tokens[2]
        year = int(tokens[3])

        italian_months = {
            "Gennaio": 1, "Febbraio": 2, "Marzo": 3, "Aprile": 4,
            "Maggio": 5, "Giugno": 6, "Luglio": 7, "Agosto": 8,
            "Settembre": 9, "Ottobre": 10, "Novembre": 11, "Dicembre": 12
        }

        month = italian_months.get(month_str)
        if not month:
            return None, None

        dt = datetime(year, month, day)
        formatted_date = dt.strftime("%Y-%m-%d")

        return formatted_date, time_part

    except Exception as e:
        print("Errore nel parse_booking_info:", e)
        return None, None

        
@app.route('/check_disponibilita', methods=['POST'])
def check_disponibilita():
    try:
        data = request.get_json()
        queue = data['queueName']

        slots = list(db.available_slots.find({
            "queueName": queue,
            "$expr": {"$lt": ["$booked", "$total"]}
        }).sort([("date", 1),("time", 1)]).limit(3))

        italian_weekdays = {
            0: "Lunedì", 1: "Martedì", 2: "Mercoledì", 3: "Giovedì",
            4: "Venerdì", 5: "Sabato", 6: "Domenica"
        }

        italian_months = {
            1: "Gennaio", 2: "Febbraio", 3: "Marzo", 4: "Aprile",
            5: "Maggio", 6: "Giugno", 7: "Luglio", 8: "Agosto",
            9: "Settembre", 10: "Ottobre", 11: "Novembre", 12: "Dicembre"
        }

        result = []
        for slot in slots:
            date_obj = datetime.strptime(slot["date"], "%Y-%m-%d")
            weekday = italian_weekdays[date_obj.weekday()]
            day = date_obj.day
            month = italian_months[date_obj.month]
            year = date_obj.year
            hour = slot["time"].split("-")[0] 

            descrizione = f"{weekday} {day} {month} {year} alle ore {hour}"
            
            available = slot["total"] - slot["booked"]
            
            result.append({
                "slot": descrizione,
                "available": available,
                "total": slot["total"]
            })

        return jsonify({"status": "OK", "fasce_disponibilita": result})

    except Exception as e:
        return jsonify({"status": "KO", "fasce_disponibilita": [], "error": str(e)}), 500


@app.route('/find_booking_by_phone', methods=['POST'])
def find_booking_by_phone():
    try:
        data = request.get_json()
        phone = data.get("phoneNumber")

        normalized_phone = normalize_phone(phone)
        booking = collection.find_one({"phoneNumber": normalized_phone})

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
        normalized_phone = normalize_phone(phone)
        email = data.get("emailUtente")
        birthDate = data.get("birthDate")
        userInfo = data.get("userInfo")
        timestamp = int(datetime.now().timestamp())
        
        date_part, time_part = parse_booking_info(slot) # "2025-06-05|10:00-11:00"
        

        slot_entry = db.available_slots.find_one({
            "date": date_part,
            "time": time_part,
            "queueName": queue
        })

        if not slot_entry or slot_entry["booked"] >= slot_entry["total"]:
            return jsonify({"status": "KO", "message": "Slot not available"}), 400

        db.available_slots.update_one({"_id": slot_entry["_id"]}, {"$inc": {"booked": 1}})

        # Сохраняем бронь
        collection.insert_one({
            "userName": user,
            "queueName": queue,
            "bookingInfo": slot,
            "phoneNumber": normalized_phone,
            "email": email,
            "birthDate": birthDate,
            "userInfo": userInfo,
            "date": date_part,
            "time": time_part,
            "dateReservation": timestamp
        })

        return jsonify({"status": "OK", "message": "Booking saved successfully"})

    except Exception as e:
        return jsonify({"status": "KO", "error": str(e)}), 500

@app.route('/delete_booking', methods=['POST'])
def delete_booking():
    try:
        data = request.get_json()
        reservation_id = data.get("reservationId")
        # Преобразуем строку в ObjectId
        obj_id = ObjectId(reservation_id)
        booking = collection.find_one({"_id": obj_id})
        
        # Пытаемся удалить бронь
        result = collection.delete_one({"_id": obj_id})

        if result.deleted_count == 1:
            db.available_slots.update_one(
                {
                    "date": booking["date"],
                    "time": booking["time"],
                    "queueName": booking["queueName"]
                },
                {"$inc": {"booked": -1}}
            )
            return jsonify({"returnCode": 200, "message": "Booking deleted successfully"})

    except Exception as e:
        return jsonify({"returnCode": 500, "message": f"Server error: {str(e)}"}), 500


@app.route('/create_slot', methods=['POST'])
def create_slot():
    data = request.get_json()

    slot = {
        "date": data["date"],  # формат YYYY-MM-DD
        "time": data["time"],  # формат HH:MM-HH:MM
        "queueName": data["queueName"],
        "total": int(data["total"]),
        "booked": 0
    }

    existing = db.available_slots.find_one({
        "date": slot["date"],
        "time": slot["time"],
        "queueName": slot["queueName"]
    })

    if existing:
        return jsonify({"status": "KO", "message": "Slot already exists"}), 400

    db.available_slots.insert_one(slot)
    return jsonify({"status": "OK", "message": "Slot created"})


@app.route('/admin_slots', methods=['GET'])
def get_admin_slots():
    date = request.args.get("date")
    queue = request.args.get("queueName")

    query = {}
    if date:
        query["date"] = date
    if queue:
        query["queueName"] = queue

    slots = list(db.available_slots.find(query))

    return jsonify([
        {
            "date": s["date"],
            "time": s["time"],
            "queueName": s["queueName"],
            "total": s["total"],
            "booked": s["booked"],
            "available": s["total"] - s["booked"]
        }
        for s in slots
    ])


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
