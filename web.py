from flask import Flask, request, render_template, jsonify
import subprocess
import os

#login.py
import os
import sys
import wave
import logging
import hashlib
from dataclasses import dataclass

from vosk import Model, KaldiRecognizer, SetLogLevel
import pyaudio
import subprocess
#login.py

app = Flask(__name__)

# login.py stuff
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration settings for the voice login system."""
    audio_from_file: bool = True
    testing_mode: bool = False
    print_guesses: bool = True
    filename: str = 'uploads/uploaded_audio.wav'
    secret: str = 'seven'
    sample_rate: int = 16000
    record_duration: int = 5
    channels: int = 1
    chunk_size: int = 1024

def parse_arguments() -> Config:
    """Parse command line arguments and return configuration."""
    config = Config()

    if len(sys.argv) > 1:
        for arg in sys.argv:
            if '.wav' in arg:
                config.audio_from_file = True
                config.filename = arg
            else:
                config.secret = arg
                logger.info('secret has changed to cli input')
    
    if len(sys.argv) > 2:
        config.secret = sys.argv[2]
        logger.info('secret has changed to cli input')

    logger.info('config created')
    return config    

def generate_md5(word: str) -> str:
    """Generate MD5 hash of input word."""
    return hashlib.md5(word.encode()).hexdigest()

def check_includes_secret(input_text: str, secret_hash: str) -> bool:
    """Check if input text contains the secret phrase."""
    try:
        words = input_text.upper().split()
        for word in words:
            if generate_md5(word) == generate_md5(Config.secret.upper()):
                logger.info('FOUND SECRET')
                return True
    except Exception as e:
        logger.error(f"Error checking secret: {e}")
        return False

def strip_to_text_partial(text: str) -> str:
    """Extract the text content from JSON response."""
    try:
        return text[17:(len(text)-3)]
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        return ""

def record_audio(config: Config) -> bool:
    """Record audio from microphone."""
    try:
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=config.channels,
            rate=config.sample_rate,
            input=True,
            frames_per_buffer=config.chunk_size
        )

        logger.info("Recording started...")
        frames = [
            stream.read(config.chunk_size)
            for _ in range(0, int(config.sample_rate / config.chunk_size * config.record_duration))
        ]
        logger.info("Recording finished.")

        stream.stop_stream()
        stream.close()
        audio.terminate()

        with wave.open(config.filename, 'wb') as wf:
            wf.setnchannels(config.channels)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(config.sample_rate)
            wf.writeframes(b''.join(frames))

        logger.info(f"Audio saved as {config.filename}")
        return True
    except Exception as e:
        logger.error(f"Error recording audio: {e}")
        return False

def process_audio(config: Config, model: Model) -> bool:
    """Process audio file and check for secret phrase."""
    try:
        rec = KaldiRecognizer(model, config.sample_rate)
        
        ffmpeg_process = subprocess.Popen(
            [
                "ffmpeg", "-loglevel", "quiet",
                "-i", str(config.filename),
                "-ar", str(config.sample_rate),
                "-ac", "1", "-f", "s16le", "-"
            ],
            stdout=subprocess.PIPE
        )

        while True:
            data = ffmpeg_process.stdout.read(4000)
            if len(data) == 0:
                break

            if rec.AcceptWaveform(data):
                text = strip_to_text_partial(rec.Result())
                if config.print_guesses:
                    logger.info(f"Recognized: {text}")
                if check_includes_secret(text, config.secret):
                    logger.info("Secret phrase recognized!")
                    return True
            else:
                text = strip_to_text_partial(rec.PartialResult())
                if config.print_guesses and text:
                    logger.info(f"Partial: {text}")
                if check_includes_secret(text, config.secret):
                    logger.info("Secret phrase recognized!")
                    return True

        logger.warning("Secret phrase not recognized")
        return False
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return False
#login.py

def my_python_function_to_run(audio_file_path):
    """
    This function is called when audio is submitted.
    Replace its content with your actual voice processing logic.
    
    Args:
        audio_file_path (str): The path to the saved audio file.
        
    Returns:
        dict: A dictionary with 'status' ('success' or 'error') and 'message'.
    """
    print(f"Python function 'my_python_function_to_run' called with audio file: {audio_file_path}")

    #### FROM LOGIN.PY ####
    config = parse_arguments()
    
    # Initialize Vosk
    SetLogLevel(0)
    if not os.path.exists("model"):
        logger.error("Please download the model from https://alphacephei.com/vosk/models and unpack as 'model' in the current folder.")
        sys.exit(1)
    
    model = Model(lang="en-us")
    
    # Record or use existing audio
    if not config.audio_from_file:
        logger.info("Starting audio recording")
        if not record_audio(config):
            sys.exit(1)
    else:
        logger.info("Using existing audio file")
    
    # Process audio
    success = process_audio(config, model)

    
    
    # Cleanup
    if not config.audio_from_file and os.path.exists(".audio.wav"):
        os.remove(".audio.wav")
    
    #sys.exit(0 if success else 1)

    if success:
        print("something worked....")
        return {"status": "success", "message": "Voiceprint verified by Python!"}
    else:
        return {"status": "error", "message": "Python: Verification failed. Please try again."}

@app.route('/')
def web(name=None): # The 'name' parameter is from your original code, not used here
    return render_template('index.html')

@app.route('/process_audio', methods=['POST'])
def process_audio_route():
    if 'audio_data' not in request.files:
        return jsonify({"status": "error", "message": "No audio file part in the request"}), 400
    
    file = request.files['audio_data']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    if file:
        uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        filename = "uploaded_audio.wav" # You might want unique filenames in a real app
        filepath = os.path.join(uploads_dir, filename)
        try:
            file.save(filepath)
        except Exception as e:
            print(f"Error saving file: {e}")
            return jsonify({"status": "error", "message": f"Could not save audio file: {e}"}), 500
            
        # Call your target Python function
        processing_result = my_python_function_to_run(filepath)
        
        return jsonify(processing_result)

    return jsonify({"status": "error", "message": "Unknown error processing audio"}), 500

if __name__ == '__main__':
    app.run(debug=True) # debug=True is for development