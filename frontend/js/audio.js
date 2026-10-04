/**
 * audio.js - Omi Ambient Voice Capture & Web Speech / Web Audio Engine (v2.2)
 * Manages live microphone streams, Web Audio analyser for waveform visuals,
 * and SpeechRecognition with resilient fallback & explicit permission handling.
 */

let recognition = null;
let isRecording = false;
let audioContext = null;
let analyser = null;
let mediaStream = null;
let dataArray = null;

export function setupVoiceCapture(callbacks = {}) {
  const {
    onTranscript,
    onResult,
    onStatus,
    onStart,
    onEnd,
    onError
  } = callbacks;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  async function startAudioStream() {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });

        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (AudioContextClass) {
          audioContext = new AudioContextClass();
          if (audioContext.state === 'suspended') {
            await audioContext.resume();
          }
          const source = audioContext.createMediaStreamSource(mediaStream);
          analyser = audioContext.createAnalyser();
          analyser.fftSize = 64;
          analyser.smoothingTimeConstant = 0.8;
          source.connect(analyser);
          dataArray = new Uint8Array(analyser.frequencyBinCount);
        }
      }
    } catch (err) {
      console.warn('Microphone audio stream could not be initialized:', err);
      // Non-fatal: SpeechRecognition might still work independently
    }
  }

  function stopAudioStream() {
    if (mediaStream) {
      mediaStream.getTracks().forEach(t => t.stop());
      mediaStream = null;
    }
    if (audioContext) {
      audioContext.close().catch(() => {});
      audioContext = null;
      analyser = null;
      dataArray = null;
    }
  }

  function handleTranscript(text) {
    const clean = text.trim();
    if (onTranscript) onTranscript(clean);
    if (onResult) onResult(clean);
  }

  function notifyStatus(status) {
    if (onStatus) onStatus(status);
  }

  // Initialize SpeechRecognition if available
  if (SpeechRecognition) {
    try {
      recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        isRecording = true;
        notifyStatus('Listening (Speak into mic)...');
        if (onStart) onStart();
      };

      recognition.onresult = (event) => {
        let fullTranscript = '';
        for (let i = 0; i < event.results.length; ++i) {
          fullTranscript += event.results[i][0].transcript + ' ';
        }
        handleTranscript(fullTranscript);
      };

      recognition.onerror = (e) => {
        console.warn('SpeechRecognition error:', e.error, e);
        let errorMsg = `Microphone error: ${e.error}`;

        if (e.error === 'not-allowed') {
          errorMsg = 'Microphone permission denied. Please allow microphone access in your browser address bar.';
        } else if (e.error === 'no-speech') {
          // Soft warning, don't necessarily kill recording immediately
          notifyStatus('Listening (no speech detected yet)...');
          return;
        } else if (e.error === 'network') {
          errorMsg = 'Speech recognition network error. Please verify your connection or type text.';
        } else if (e.error === 'audio-capture') {
          errorMsg = 'No microphone device was detected on your system.';
        }

        isRecording = false;
        stopAudioStream();
        notifyStatus('Idle (Error)');
        if (onError) onError({ error: e.error, message: errorMsg });
        if (onEnd) onEnd();
      };

      recognition.onend = () => {
        isRecording = false;
        stopAudioStream();
        notifyStatus('Idle');
        if (onEnd) onEnd();
      };
    } catch (e) {
      console.error('Failed to construct SpeechRecognition:', e);
      recognition = null;
    }
  }

  return {
    supported: Boolean(SpeechRecognition),
    isRecording: () => isRecording,
    getAudioFrequencyData: () => {
      if (analyser && dataArray) {
        analyser.getByteFrequencyData(dataArray);
        return dataArray;
      }
      return null;
    },
    toggle: async () => {
      if (!SpeechRecognition) {
        notifyStatus('Web Speech not supported');
        const fallbackText = "Sarah (CFO): I will approve the $45k GPU cluster budget by Wednesday, and let's schedule an executive sync tomorrow at 3 PM.";
        handleTranscript(fallbackText);
        if (onError) onError({
          error: 'not_supported',
          message: 'Speech Recognition is not supported in this browser. Inserted demo voice memo into input!'
        });
        return;
      }

      if (isRecording) {
        try {
          if (recognition) recognition.stop();
        } catch (_) {}
        stopAudioStream();
        isRecording = false;
        notifyStatus('Idle');
        if (onEnd) onEnd();
      } else {
        try {
          notifyStatus('Requesting Mic Access...');
          await startAudioStream();
          if (recognition) {
            recognition.start();
          }
        } catch (err) {
          console.error('Failed to start recording:', err);
          isRecording = false;
          stopAudioStream();
          notifyStatus('Idle (Mic Error)');
          let msg = err.message || 'Could not start voice recording.';
          if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
            msg = 'Microphone permission was blocked. Please enable microphone permissions in your browser URL bar!';
          }
          if (onError) onError({ error: err.name || 'start_error', message: msg });
        }
      }
    }
  };
}
