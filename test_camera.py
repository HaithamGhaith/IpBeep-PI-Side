from picamera2 import Picamera2
import cv2
import time

def main():
    # Initialize camera
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (640, 480)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.configure("preview")
    picam2.start()
    
    print("Camera started. Press 'q' to quit.")
    
    try:
        while True:
            # Capture frame
            frame = picam2.capture_array()
            
            # Convert to BGR for OpenCV
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Display frame
            cv2.imshow('Camera Test', frame)
            
            # Break loop on 'q' press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except KeyboardInterrupt:
        print("\nStopping camera...")
    finally:
        # Cleanup
        cv2.destroyAllWindows()
        picam2.stop()
        print("Camera stopped.")

if __name__ == "__main__":
    main() 