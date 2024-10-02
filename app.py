from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['UPLOADED_PHOTOS_DEST'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
socketio = SocketIO(app)

class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bus_number = db.Column(db.String(150), unique=True, nullable=False)
    photo_filename = db.Column(db.String(150), nullable=False)

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

with app.app_context():z
    db.create_all()

driver_location = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/driver')
def driver():
    return render_template('driver.html')

@app.route('/passenger')
def passenger():
    return render_template('passenger.html')

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'photo' in request.files and 'bus_number' in request.form:
        photo = request.files['photo']
        bus_number = request.form['bus_number']
        filename = secure_filename(photo.filename)
        file_path = os.path.join(app.config['UPLOADED_PHOTOS_DEST'], filename)
        photo.save(file_path)
        driver = Driver(bus_number=bus_number, photo_filename=filename)
        db.session.add(driver)
        db.session.commit()
        driver_location[bus_number] = None
        return jsonify(success=True, message="Image and bus number uploaded successfully.")
    return jsonify(success=False, message="Image upload failed.")

@app.route('/set_location', methods=['POST'])
def set_location():
    data = request.get_json()
    bus_number = data.get('bus_number')
    if bus_number in driver_location:
        location = data['location']
        driver = Driver.query.filter_by(bus_number=bus_number).first()
        new_location = Location(driver_id=driver.id, latitude=location['latitude'], longitude=location['longitude'])
        db.session.add(new_location)
        db.session.commit()
        driver_location[bus_number] = location
        print(f"Broadcasting location update: {location} for bus number {bus_number}")
        socketio.emit('location_update', {'location': location, 'bus_number': bus_number}, broadcast=True)
        return jsonify(success=True)
    return jsonify(success=False, message="Driver not authenticated.")

@app.route('/stop_location', methods=['POST'])
def stop_location():
    data = request.get_json()
    bus_number = data.get('bus_number')
    if bus_number in driver_location:
        driver_location[bus_number] = None
        socketio.emit('location_update', {'location': None, 'bus_number': bus_number}, broadcast=True)
        return jsonify(success=True, message="Location sharing stopped.")
    return jsonify(success=False, message="Driver not authenticated.")

@app.route('/verify_bus_number', methods=['POST'])
def verify_bus_number():
    data = request.get_json()
    bus_number = data.get('bus_number')
    if bus_number in driver_location:
        return jsonify(success=True)
    return jsonify(success=False, message="Bus number not found.")

@socketio.on('connect')
def handle_connect():
    for bus_number, location in driver_location.items():
        if location:
            emit('location_update', {'location': location, 'bus_number': bus_number})

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOADED_PHOTOS_DEST']):
        os.makedirs(app.config['UPLOADED_PHOTOS_DEST'])
    socketio.run(app, debug=True)
