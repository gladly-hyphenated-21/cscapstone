#!/usr/bin/env python3
"""
Voice-based Login System

This script implements a voice-based authentication system using the Vosk speech recognition model.
It can process both real-time audio input and pre-recorded WAV files.

usage: ./login.py <optinal: .wav file> 
"""

import os
import sys
import wave
import json
import logging
import hashlib
from typing import Optional
from pathlib import Path
from dataclasses import dataclass

from vosk import Model, KaldiRecognizer, SetLogLevel
import pyaudio
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration settings for the voice login system."""
    audio_from_file: bool = False
    testing_mode: bool = False
    print_guesses: bool = True
    filename: str = '.audio.wav'
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

def main():
    """Main function."""
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
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
