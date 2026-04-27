"""
core/face_auth.py
─────────────────
Face Authentication — identifies and verifies the user via webcam.
Leverages your existing OpenCV experience from the gesture project.

INSTALL:
    pip install opencv-python face-recognition numpy
    # face-recognition requires dlib — on Windows install wheel:
    # pip install dlib-binary

USAGE:
    auth = FaceAuth()
    auth.enroll("Praneeth")    # run once to register your face
    result = auth.verify()     # returns True/False
"""

import os
import cv2
import numpy as np
from core.logger import log
from core.config import CONFIG


class FaceAuth:
    """
    Face recognition gate for JARVIS.

    Modes:
        enabled=True  → webcam face must match enrolled face
        enabled=False → always returns True (bypass for development)
    """

    ENCODINGS_PATH = "data/face_encodings.npy"
    NAMES_PATH     = "data/face_names.npy"

    def __init__(self):
        self.enabled = CONFIG.get("face_auth_enabled", False)
        self.encodings = []
        self.names     = []

        if self.enabled:
            self._load_encodings()
        else:
            log.info("FaceAuth disabled (set face_auth_enabled=true in config to enable).")

    # ──────────────────────────────────────────────────────
    def verify(self) -> bool:
        """
        Attempt to verify the user's face.
        Returns True if recognised or if auth is disabled.
        """
        if not self.enabled:
            return True

        if not self.encodings:
            log.warning("No enrolled faces. Run auth.enroll('YourName') first.")
            return True  # fail-open during development

        try:
            import face_recognition
        except ImportError:
            log.warning("face_recognition not installed. Bypassing face auth.")
            return True

        cap = cv2.VideoCapture(0)
        recognised = False
        name_found = "Unknown"

        log.info("FaceAuth: scanning for face...")
        for _ in range(30):          # try for ~3 seconds (30 frames)
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, locations)

            for enc in encodings:
                matches = face_recognition.compare_faces(self.encodings, enc, tolerance=0.5)
                if True in matches:
                    idx  = matches.index(True)
                    name_found = self.names[idx]
                    recognised = True
                    break

            if recognised:
                break

        cap.release()

        if recognised:
            log.info(f"FaceAuth: verified as '{name_found}'.")
        else:
            log.warning("FaceAuth: face not recognised.")

        return recognised

    # ──────────────────────────────────────────────────────
    def enroll(self, name: str, num_samples: int = 20):
        """
        Capture webcam images and save face encodings.
        Run this ONCE to register your face.

        Args:
            name        : your name (e.g. "Praneeth")
            num_samples : number of face images to capture
        """
        try:
            import face_recognition
        except ImportError:
            log.error("face_recognition not installed. Run: pip install face-recognition")
            return

        log.info(f"Enrolling face for: {name}")
        cap = cv2.VideoCapture(0)
        captured = []

        while len(captured) < num_samples:
            ret, frame = cap.read()
            if not ret:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb)
            encs = face_recognition.face_encodings(rgb, locs)

            if encs:
                captured.append(encs[0])
                cv2.putText(frame, f"Captured {len(captured)}/{num_samples}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            cv2.imshow("Enrolling — press Q to cancel", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        if captured:
            self.encodings.extend(captured)
            self.names.extend([name] * len(captured))
            self._save_encodings()
            log.info(f"Enrolled {len(captured)} samples for '{name}'.")
        else:
            log.warning("Enrollment failed — no face detected.")

    # ──────────────────────────────────────────────────────
    def _save_encodings(self):
        os.makedirs("data", exist_ok=True)
        np.save(self.ENCODINGS_PATH, np.array(self.encodings))
        np.save(self.NAMES_PATH,     np.array(self.names))

    def _load_encodings(self):
        if os.path.exists(self.ENCODINGS_PATH) and os.path.exists(self.NAMES_PATH):
            self.encodings = list(np.load(self.ENCODINGS_PATH, allow_pickle=True))
            self.names     = list(np.load(self.NAMES_PATH,     allow_pickle=True))
            log.info(f"FaceAuth: loaded {len(self.encodings)} face encodings.")
        else:
            log.warning("No face encodings found. Run enroll() to register your face.")
