import pvporcupine
import pyaudio
import struct
import threading

class PorcupineHotword:
    def __init__(self, keyword_paths=None, sensitivities=None):
        self.porcupine = pvporcupine.create(
            keyword_paths=keyword_paths,
            sensitivities=sensitivities or [0.5]
        )
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )
        self.running = False
        self.callback = None  # to be set to function called on hotword detect

    def start(self, callback):
        self.callback = callback
        self.running = True
        threading.Thread(target=self._process_audio, daemon=True).start()

    def _process_audio(self):
        while self.running:
            pcm = self.stream.read(self.porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
            result = self.porcupine.process(pcm_unpacked)
            if result >= 0:
                if self.callback:
                    self.callback()  # Hotword detected!

    def stop(self):
        self.running = False
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
        self.porcupine.delete()
