/**
 * audio.js - Web Speech API & Omi Voice Capture Engine
 */
let recognition = null;
let isRecording = false;

export function setupVoiceCapture({ onStart, onResult, onEnd, onError }) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  
  if (!SpeechRecognition) {
    return {
      supported: false,
      toggle: () => alert("Web Speech API is not supported in this browser. Please type voice text into the input.")
    };
  }

  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;

  recognition.onstart = () => {
    isRecording = true;
    if (onStart) onStart();
  };

  recognition.onresult = (event) => {
    let transcript = '';
    for (let i = 0; i < event.results.length; ++i) {
      transcript += event.results[i][0].transcript + ' ';
    }
    if (onResult) onResult(transcript.trim());
  };

  recognition.onerror = (e) => {
    isRecording = false;
    if (onError) onError(e);
  };

  recognition.onend = () => {
    isRecording = false;
    if (onEnd) onEnd();
  };

  return {
    supported: true,
    toggle: () => {
      if (isRecording) {
        recognition.stop();
      } else {
        recognition.start();
      }
    },
    isRecording: () => isRecording
  };
}
