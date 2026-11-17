
import argparse
import serial
from datetime import datetime


def read_serial(port, baudrate):
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=1
        )

        print(f"Connected to {port}")
        print(f"Baudrate: {baudrate}")
        print("Listening for serial data... (CTRL+C to stop)\n")

        while True:
            data = ser.readline()

            if data:
                message = data.decode("utf-8", errors="replace").strip()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                print(f"[{timestamp}] {message}", flush=True)

    except serial.SerialException as e:
        print(f"Serial error: {e}")

    except KeyboardInterrupt:
        print("\nStopped by user.")

    finally:
        if "ser" in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read serial data and print to terminal"
    )

    parser.add_argument(
        "--port", "-p",
        required=True,
        help="Serial port path (e.g. /dev/ttyUSB0)"
    )

    parser.add_argument(
        "--baudrate", "-b",
        type=int,
        default=38400,
        help="Serial baudrate (default: 38400)"
    )

    args = parser.parse_args()

    read_serial(args.port, args.baudrate)
