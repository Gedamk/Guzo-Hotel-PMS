# guzo_backend/modules/flask_app.py
from flask import Flask, request, jsonify
from modules.booking_handler import handle_booking

app = Flask(__name__)

@app.route("/book", methods=["POST"])
def web_booking():
    data = request.json
    try:
        handle_booking(
            data["hotel_name"],
            data["guest_name"],
            data["check_in"],
            data["check_out"],
            data["room"],
            source="Website",
            contact=data.get("contact", "")
        )
        return jsonify({"status": "success", "message": "Booking received ÃÂÃÂÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)
