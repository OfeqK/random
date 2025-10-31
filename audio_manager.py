import os
import tempfile
import threading
import numpy as np
import lameenc
from playsound import playsound
import pyaudio
import sys
from mutagen.mp3 import MP3

CHUNK = 960
FORMAT = pyaudio.paInt16 # 16 bit resolution
CHANNELS = 1 if sys.platform == 'darwin' else 2 # mono
RATE = 16000 # sampling rate = 16 kHz


def play_audio(mp3_bytes):
	"""
	Play audio directly from the mp3 bytes.
	"""
	threading.Thread(target=lambda: play_audio_helper(mp3_bytes), daemon=True).start()

def play_audio_helper(mp3_bytes):
	# create a temporary .mp3 file
	with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
		tmp.write(mp3_bytes)
		tmp_path = tmp.name.replace("\\", "/")
	try:
		playsound(tmp_path)
	finally:
		# Remove the temporary file
		os.remove(tmp_path)

def get_audio_duration_str(mp3_bytes):
	"""
	Gets the duration in seconds as a str representation
	:return:
	"""
	with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
		tmp.write(mp3_bytes)
		tmp_path = tmp.name

	try:
		audio = MP3(tmp_path)
		seconds = int(audio.info.length)
		minutes, seconds = divmod(seconds, 60)
		return f"{minutes}:{seconds:02d}"
	except Exception as e:
		print("Error reading duration:", e)
		return "0:00"
	finally:
		os.remove(tmp_path)


class AudioManager:
	def __init__(self):
		self.p = None
		self.stream = None

		self.recording = False
		self.frames = []

	def start_recording(self):
		"""
		Starts capturing microphone input.
		"""
		if self.recording:
			return

		self.p = pyaudio.PyAudio()
		self.stream = self.p.open(
			format=FORMAT,
			channels=CHANNELS,
			rate=RATE,
			input=True,
			frames_per_buffer=CHUNK
		)
		self.frames = []
		self.recording = True
		print('[ Debug ] Recording audio...')
		threading.Thread(target=self._record).start()
		return

	def _record(self):
		try:
			while self.recording:
				data = self.stream.read(CHUNK, exception_on_overflow=False)
				self.frames.append(data)
		except (OSError, Exception) as e:
			print(f"[ ERROR ] An error occurred whilst recording audio.\n\t Error: {e}")


	def stop_recording(self):
		"""
		Stops recording microphone input.
		:return: The bytes corresponding to what we have recorded.
		"""
		print('[ Debug ] Stopped recording audio...')
		self.recording = False
		self.stream.stop_stream()
		self.stream.close()
		self.p.terminate()

		pcm_data = b"".join(self.frames)
		pcm_array = np.frombuffer(pcm_data, dtype=np.int16)

		# mp3 encoding
		encoder = lameenc.Encoder()
		encoder.set_bit_rate(32)
		encoder.set_in_sample_rate(RATE)
		encoder.set_channels(CHANNELS)
		encoder.set_quality(7)  # 2-highest, 7-fastest
		# Can call this in a loop
		mp3_bytes = encoder.encode(pcm_array.tobytes())
		# Flush when finished encoding the entire stream
		mp3_bytes += encoder.flush()

		print(f"[Debug] PCM size: {len(pcm_data)} bytes")
		print(f"[Debug] MP3 size: {len(mp3_bytes)} bytes")
		return mp3_bytes

		# # Write to memory instead of disk
		# buffer = io.BytesIO()
		# with wave.open(buffer, 'wb') as wf:
		# 	wf.setnchannels(CHANNELS)
		# 	wf.setsampwidth(self.p.get_sample_size(FORMAT))
		# 	wf.setframerate(RATE)
		# 	for data in self.frames:
		# 		wf.writeframes(data)
		#
		# audio_bytes = buffer.getvalue()
		# return audio_bytes
