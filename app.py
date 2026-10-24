
from flask import Flask, render_template, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)
API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
BASE = "https://api.openweathermap.org/data/2.5/"


def get_icon(weather_id):
    if weather_id < 300:
        return "⛈️"
    if weather_id < 600:
        return "🌧️"
    if weather_id < 700:
        return "❄️"
    if weather_id < 800:
        return "🌫️"
    if weather_id == 800:
        return "☀️"
    return "☁️"


def get_params():
    city = request.args.get("city", "").strip()
    lat = request.args.get("lat")
    lon = request.args.get("lon")

    if lat is not None and lon is not None:
        return {"lat": lat, "lon": lon}
    if city:
        return {"q": city}
    return None


def api_request(endpoint, params):
    params.update({"appid": API_KEY, "units": "metric"})
    response = requests.get(BASE + endpoint, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/weather")
def weather():
    if not API_KEY:
        return jsonify({"error": "Weather API key is not configured."}), 500

    params = get_params()
    if not params:
        return jsonify({"error": "Enter a city or choose your location."}), 400

    try:
        data = api_request("weather", params)
        current = data["main"]

        return jsonify({
            "city": data["name"],
            "country": data["sys"]["country"],
            "temp": current["temp"],
            "feels_like": current["feels_like"],
            "description": data["weather"][0]["description"].title(),
            "icon": get_icon(data["weather"][0]["id"]),
            "humidity": current["humidity"],
            "wind": data["wind"]["speed"],
            "visibility": round(data.get("visibility", 0) / 1000, 1),
            "pressure": current["pressure"]
        })

    except requests.HTTPError as error:
        if error.response.status_code == 404:
            return jsonify({"error": "City not found. Check the spelling."}), 404
        if error.response.status_code == 401:
            return jsonify({"error": "API key invalid or not activated."}), 502
        return jsonify({"error": "Weather service error."}), 502
    except requests.RequestException:
        return jsonify({"error": "Connection failed. Check your internet."}), 502


@app.route("/forecast")
def forecast():
    if not API_KEY:
        return jsonify({"error": "Weather API key is not configured."}), 500

    params = get_params()
    if not params:
        return jsonify({"error": "Enter a city or choose your location."}), 400

    try:
        data = api_request("forecast", params)
        daily = {}

        for item in data["list"]:
            day = item["dt_txt"][:10]
            hour = int(item["dt_txt"][11:13])

            if day not in daily or abs(hour - 12) < abs(
                int(daily[day]["dt_txt"][11:13]) - 12
            ):
                daily[day] = item

        result = []
        for day, item in list(daily.items())[:5]:
            result.append({
                "day": datetime.strptime(day, "%Y-%m-%d").strftime("%a"),
                "temp": item["main"]["temp"],
                "icon": get_icon(item["weather"][0]["id"]),
                "description": item["weather"][0]["description"].title()
            })

        return jsonify({"forecast": result})

    except requests.RequestException:
        return jsonify({"error": "Forecast unavailable."}), 502


if __name__ == "__main__":
    app.run()
