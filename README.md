# Touchless Smart Room Terminal 

An end-to-end IoT smart display prototype built with an ESP32, an 8x8 LiDAR array, and a Python Flask backend. This project serves as a comprehensive exploration of hardware-software integration, translating raw serial depth data into a responsive, gesture-controlled web interface.



https://github.com/user-attachments/assets/86408e40-5635-4533-af0b-c0dc78bdeb2a



## System Overview

This terminal functions as a modern room clock and information hub, entirely controlled by touchless hand gestures. The ESP32 handles physical sensor polling and spatial mapping, streaming state data over a serial connection to a local server. The Python/Flask backend acts as a bridge, delivering a dynamic HTML/CSS/JavaScript UI that updates in real-time via asynchronous API calls and local state loops.

## Core Features

*   **Spatial Gesture Navigation:** Utilizes a VL53L5CX 8x8 Time-of-Flight (ToF) sensor to map physical space into interaction zones. Supports four distinct gestures: Left Hover, Right Hover, Close Hover (Click/Enter), and Far Hover (Back).
*   **Dynamic Information HUD:** Displays a real-time clock, local temperature (Open-Meteo API), and dynamic Islamic prayer times (Aladhan API). APIs are queried dynamically based on coordinate data for precision routing.
*   **Intelligent Sleep Mode:** A PIR sensor monitors ambient room motion. The terminal automatically enters a low-power, screen-dimming sleep state after 5 minutes of inactivity and wakes instantly upon detecting movement.
*   **Customizable Interface:** Includes a settings menu to toggle between Light and Dark themes, and cycle through localized regional data (Riyadh, Jeddah, Dammam).
*   **Zero-Delay Mini-Game:** An integrated 8x10 grid arcade game demonstrating low-latency input translation from hardware sensors directly to frontend canvas rendering.

## Hardware Architecture

*   **Microcontroller:** ESP32
*   **LiDAR Sensor:** SparkFun VL53L5CX (8x8 Multi-Zone ToF Imager)
*   **Motion Sensor:** Standard PIR Sensor
*   **Schematics:** Please refer to `circuit_diagram.pdf` for complete wiring details, power distribution, and component integration.

<img width="1024" height="572" alt="Circuit Diagram" src="https://github.com/user-attachments/assets/1e72e89a-248d-425a-a5ea-8d90e421b692" />


## Software Stack

The project is divided into three distinct execution layers:

1.  **Hardware Level (`main.ino`):** Written in C++, this layer configures the I2C communication for the LiDAR, captures the 64-zone depth matrix, and transmits a comma-separated serial string at 115200 baud alongside the PIR state.
2.  **Backend Server (`app.py`):** A multithreaded Python application. One thread continuously listens to the serial port, applies custom debounce logic (`DWELL_TIME`), and translates raw distance arrays into distinct gesture states. The second thread runs a Flask web server, serving the UI and providing a JSON endpoint (`/data`) for the frontend.
3.  **Frontend Interface (HTML/JS/CSS):** A strictly local, single-page application. It utilizes a 100ms polling heartbeat to read system states from the backend, manipulating the DOM to switch screens and trigger interactions without page refreshes.

## Technical Highlights & Problem Solving

*   **Array Flattening & Memory Optimization:** Converted a 1D serial data stream into a 2D spatial grid using modulo and integer division logic, allowing precise region-of-interest mapping for gestures while adhering to the ESP32's memory constraints.
*   **Software Debouncing:** Implemented hardware noise mitigation in Python by tracking zone entry times, ensuring gestures only trigger after a sustained dwell time to prevent ghost inputs.
*   **Robust API Routing:** Upgraded string-based API queries to precise GPS coordinate fetching to resolve silent failure states when public APIs failed to match localized text queries.

## Setup & Execution

1.  **Hardware:** Wire the ESP32, VL53L5CX, and PIR sensor according to the provided circuit diagram.
2.  **Firmware:** Flash `main.ino` to the ESP32 using the Arduino IDE. Note the COM port.
3.  **Backend:** Install Python dependencies (`pip install flask pyserial`).
4.  **Run:** Update the `PORT` variable in `app.py` to match your ESP32's COM port. Execute the script (`python app.py`).
5.  **Interface:** Open `http://localhost:5000` in any web browser on the host machine.

## How to Use (User Guide)

The terminal requires no physical touch. The interface is navigated entirely through spatial hand gestures mapped by the Time-of-Flight sensor:

*   **Close Hover (Distance < 50mm, Center):** Acts as a "Click" or "Enter". Use this to open menus, toggle settings, or shoot in the arcade game.
*   **Left/Right Hover (Distance 150mm - 350mm, Edges):** Acts as a directional swipe. Use this to cycle through the settings menu (Theme, Region, Back) or move your ship in the game.
*   **Far Hover (Distance > 350mm, Center):** Acts as a "Back" button to immediately return to the main clock screen from anywhere.
*   **Hold to Confirm:** To prevent accidental ghost inputs when walking past, hold your hand in the targeted gesture zone for a fraction of a second (0.2s) to register the command.
*   **Wake from Sleep:** If the screen goes dark, simply walk near the device. The motion sensor will automatically wake the terminal.
