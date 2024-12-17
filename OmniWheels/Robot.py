#Import Library
from flask import Flask, render_template, Response, request, jsonify
import cv2
import numpy as np
from time import sleep
from gpiozero import Motor

# Setup Motor driver
motor1 = Motor(23, 24)
motor2 = Motor(27, 22)
motor3 = Motor(25, 8)

# Pengaturan Kecepatan Motor
TURN_SPEED = 0.3  # Reduced speed for turning

#Setup Server
app = Flask(__name__)

#Setup warna pertama untuk di tracking saat baru mulai(disini menggunakan biru)
lower_color = np.array([37, 38, 146]) #Range awal
upper_color = np.array([77, 255, 255]) #Range akhir

# Parameter kamera
KNOWN_WIDTH = 5.0
FOCAL_LENGTH = 350 #focal_length spesifikasi kamera

# Status letak warna yang di tracking
current_direction = "center"

def rotateLeft():
    #motor1.value = TURN_SPEED
    #motor2.value = TURN_SPEED
    motor3.value = TURN_SPEED

def rotateRight():
   #motor1.value = -TURN_SPEED
   #motor2.value = -TURN_SPEED
    motor3.value = -TURN_SPEED

def maju():
    motor1.value = TURN_SPEED
    motor2.value = TURN_SPEED

def mundur():
    motor1.value = -TURN_SPEED
    motor2.value = -TURN_SPEED

def stop():
    motor1.stop()
    motor2.stop()
    motor3.stop()

def control_motors(direction):
    """Control motors based on detected direction"""
    if direction == "move left":
        rotateLeft()
    elif direction == "move right":
        rotateRight()
    elif direction == "center":
        stop()

# Kalkulasi jarak benda ke kamera
def calculate_distance(apparent_width):
    """Calculate distance using the width of the object."""
    if apparent_width == 0:
        return float('inf')
    return (KNOWN_WIDTH * FOCAL_LENGTH) / apparent_width

def generate_frames():
    global current_direction
    camera = cv2.VideoCapture(0) #Menyalakan kamera

    width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera resolution: {width}x{height}")

    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Mirror kamera
            frame = cv2.flip(frame, 1)

            # Ubah frame ke format warna HSV
            hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Buat masking untuk warna yang di track
            mask = cv2.inRange(hsv_frame, lower_color, upper_color)

            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                # Tracking untuk benda terbesar
                largest_contour = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)


                center_x, center_y = x + w // 2, y + h // 2
                # Gambar kotak pendeteksi
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

                # Gambar axis pendeteksi
                cv2.line(frame, (center_x, 0), (center_x, frame.shape[0]), (0, 255, 0), 2)  # Y-axis
                cv2.line(frame, (0, center_y), (frame.shape[1], center_y), (0, 0, 255), 2)  # X-axis

                # Hitung jarak
                distance = calculate_distance(w)

                cv2.putText(frame, f"Distance: {distance:.2f} cm", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Width: {w} px", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                # Menentukan pergerakan robot
                frame_width = frame.shape[1]
                if center_x < frame_width // 3:
                    current_direction = "move left"
                elif center_x > 2 * frame_width // 3:
                    current_direction = "move right"
                else:
                    current_direction = "center"

                # Kontrol motor untuk mengikuti letak objek
                control_motors(current_direction)

                # Menampilkan arah
                cv2.putText(frame, f"Direction: {current_direction}", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            else:
                current_direction = "center"
                stop()


            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/set_color', methods=['POST'])
def set_color():
    global lower_color, upper_color
    color = request.json.get('color')

    # Range Warna
    if color == "red":
        lower_color = np.array([160, 59, 102])
        upper_color = np.array([179, 255, 255])
    elif color == "green":
        lower_color = np.array([37, 146, 38])
        upper_color = np.array([77, 255, 255])
    elif color == "blue":
        lower_color = np.array([45, 43, 118])
        upper_color = np.array([179, 255, 255])

    return jsonify({"status": "success", "color": color})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)
