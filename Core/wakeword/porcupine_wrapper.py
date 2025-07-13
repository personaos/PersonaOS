# personaos/wakeword/porcupine_wrapper.py

import pvporcupine
import pyaudio
import struct
import os

class PorcupineWakeWord:
    def __init__(self, config):
        self.access_key = config.get("access_key")
        self.keyword_path = config.get("keyword_path")  # path to .ppn file
        self.sensitivity = config.get("sensitivity", 0.65)

        self.porcupine = pvporcupine.create(
            access_key=self.access_key,
            keyword_paths=[self.keyword_path],
            sensitivities=[self.sensitivity]
        )

        self.pa = pyaudio.PyAudio()
        self.audio_stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length
        )

    def listen(self):
        try:
            pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
            result = self.porcupine.process(pcm)
            return result >= 0
        except Exception as e:
            print(f"[WakeWord] Error: {e}")
            return False

    def cleanup(self):
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        if self.pa:
            self.pa.terminate()
        if self.porcupine:
            self.porcupine.delete()
