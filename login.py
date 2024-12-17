#login sesame
from vosk import Model, KaldiRecognizer, SetLogLevel
import pyaudio
import os
import sys
import wave
import json
import pyaudio
import subprocess
import hashlib
print("[info] imports done")

var_audiofromfile = False
var_testingmode = False
var_printguesses = True
var_filename = 'audio.wav'
var_secret = 'three'

for arg in sys.argv:
    if 'TESTING' in arg:
        var_testingmode = True
if len(sys.argv) >= 0:
    for arg in sys.argv:
        print('Argument: '+str(arg))
if len(sys.argv) > 1:
    if '.wav' in sys.argv[1]:
        var_audiofromfile = True
        var_filename = str(sys.argv[1])
    else:
        var_secret = sys.argv[1]
if len(sys.argv) > 2:
    var_secret = sys.argv[2]

def generate_md5(word):
    return hashlib.md5(word.encode()).hexdigest()

def check_includes_secret(input_text,secret_hash):
    words = input_text.upper().split()
    for word in words:
        if generate_md5(word) == var_secret:
            print("[SECRET] logged in with secret "+str(input_text))
            return True
        else:
            continue

def strip_to_text_partial(text):
    return text[17:(len(text)-3)]

def record_audio(filename="audio.wav", duration=5, channels=1, rate=44100, chunk=1024):
    audio = pyaudio.PyAudio()
    stream = audio.open(format=pyaudio.paInt16, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)

    print("Recording...")
    frames = [stream.read(chunk) for _ in range(0, int(rate / chunk * duration))]
    print("Recording finished.")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))

    print(f"[info] Audio saved as {filename}")


SAMPLE_RATE = 16000
SetLogLevel(0)
model = Model(lang="en-us")
rec = KaldiRecognizer(model, SAMPLE_RATE)
if not var_audiofromfile:
    print("[info] starting recording audio process")
    record_audio() #records an audio and saves it to audio.wav, replaces if audio file already present
    print("[info] done recording audio process")
else:
    print("[info] fetching audio from file...")
    var_filename = 'file.wav'

with subprocess.Popen(["ffmpeg", "-loglevel", "quiet", "-i",
                            str(var_filename),
                            "-ar", str(SAMPLE_RATE) , "-ac", "1", "-f", "s16le", "-"],
                            stdout=subprocess.PIPE) as process:

    while True:
        data = process.stdout.read(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            text = (strip_to_text_partial(rec.Result()))
            if var_printguesses:
                print(text)
            if check_includes_secret(text,var_secret):
                print("SECRET FOUND!")
                exit()
            #print(rec.Result())
        else:
            text = (strip_to_text_partial(rec.PartialResult()))
            if var_printguesses:
                print(text)
            if check_includes_secret(text, var_secret):
                print("SECRET FOUND!")
                exit()
            #print(rec.PartialResult())
    print("[SECRET] passphrase or voice not recognized")
if not var_audiofromfile:
    os.remove("audio.wav")
