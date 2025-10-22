/**
 * Voice Call Modal - Enables hands-free conversation with AI
 * Features:
 * - Continuous speech recognition
 * - Auto-send messages
 * - Auto-play AI responses
 * - Multi-language support
 */

'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

export interface Language {
  code: string;
  name: string;
  flag: string;
  speechCode: string; // For Web Speech API
  voiceName?: string; // Preferred voice name
}

export const SUPPORTED_LANGUAGES: Language[] = [
  { code: 'en', name: 'English', flag: '🇺🇸', speechCode: 'en-US', voiceName: 'Google US English' },
  { code: 'es', name: 'Spanish', flag: '🇪🇸', speechCode: 'es-ES', voiceName: 'Google español' },
  { code: 'fr', name: 'French', flag: '🇫🇷', speechCode: 'fr-FR', voiceName: 'Google français' },
  { code: 'de', name: 'German', flag: '🇩🇪', speechCode: 'de-DE', voiceName: 'Google Deutsch' },
  { code: 'zh', name: 'Chinese', flag: '🇨🇳', speechCode: 'zh-CN', voiceName: 'Google 普通话（中国大陆）' },
  { code: 'ja', name: 'Japanese', flag: '🇯🇵', speechCode: 'ja-JP', voiceName: 'Google 日本語' },
  { code: 'ar', name: 'Arabic', flag: '🇸🇦', speechCode: 'ar-SA', voiceName: 'Google العربية' },
  { code: 'ru', name: 'Russian', flag: '🇷🇺', speechCode: 'ru-RU', voiceName: 'Google русский' },
  { code: 'pt', name: 'Portuguese', flag: '🇧🇷', speechCode: 'pt-BR', voiceName: 'Google português do Brasil' },
  { code: 'it', name: 'Italian', flag: '🇮🇹', speechCode: 'it-IT', voiceName: 'Google italiano' },
  { code: 'ko', name: 'Korean', flag: '🇰🇷', speechCode: 'ko-KR', voiceName: 'Google 한국의' },
  { code: 'hi', name: 'Hindi', flag: '🇮🇳', speechCode: 'hi-IN', voiceName: 'Google हिन्दी' },
];

interface VoiceCallModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSendMessage: (content: string) => Promise<void>;
  streamingContent: string;
  isThinking: boolean;
  sending: boolean;
  streaming: boolean;
}

export default function VoiceCallModal({
  isOpen,
  onClose,
  onSendMessage,
  streamingContent,
  isThinking,
  sending,
  streaming,
}: VoiceCallModalProps) {
  const [selectedLanguage, setSelectedLanguage] = useState<Language>(SUPPORTED_LANGUAGES[0]);
  const [isCallActive, setIsCallActive] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [callDuration, setCallDuration] = useState(0);
  const [availableVoices, setAvailableVoices] = useState<SpeechSynthesisVoice[]>([]);

  const recognitionRef = useRef<any>(null);
  const callStartTimeRef = useRef<number>(0);
  const durationIntervalRef = useRef<number>();
  const ttsPollingIntervalRef = useRef<number>(); // Poll TTS status
  const lastResponseRef = useRef<string>('');
  const onSendMessageRef = useRef(onSendMessage);
  const isRecognitionRunningRef = useRef(false);
  const isCallActiveRef = useRef(false);
  const wasSendingRef = useRef(false);
  const wasStreamingRef = useRef(false);
  const accumulatedContentRef = useRef<string>('');
  const hasSpokenRef = useRef(false);

  // Keep refs up to date
  useEffect(() => {
    onSendMessageRef.current = onSendMessage;
  }, [onSendMessage]);

  useEffect(() => {
    isCallActiveRef.current = isCallActive;
  }, [isCallActive]);

  // Load available voices
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const loadVoices = () => {
        const voices = window.speechSynthesis.getVoices();
        setAvailableVoices(voices);
      };

      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    // Stop old recognition if it exists
    const wasRunning = isRecognitionRunningRef.current;
    if (recognitionRef.current && wasRunning) {
      try {
        recognitionRef.current.stop();
      } catch (err) {
        console.error('Failed to stop old recognition:', err);
      }
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true; // Keep listening
    recognition.interimResults = true;
    recognition.lang = selectedLanguage.speechCode;

    recognition.onstart = () => {
      isRecognitionRunningRef.current = true;
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      if (finalTranscript) {
        // Auto-send when user finishes speaking
        const message = finalTranscript.trim();
        if (message) {
          setTranscript('');
          void onSendMessageRef.current(message);
        }
      } else {
        setTranscript(interimTranscript);
      }
    };

    recognition.onerror = (event: any) => {
      isRecognitionRunningRef.current = false;
      console.error('Speech recognition error:', event.error);

      // Don't restart on these errors
      if (event.error === 'aborted' || event.error === 'not-allowed') {
        return;
      }

      // Check if language is supported
      if (event.error === 'language-not-supported') {
        console.error(`Language ${selectedLanguage.speechCode} is not supported by your browser`);
        alert(`Speech recognition for ${selectedLanguage.name} is not supported by your browser. Try Chrome or Edge with the language pack installed.`);
        return;
      }

      // For other errors like 'no-speech', let onend handle the restart
    };

    recognition.onend = () => {
      isRecognitionRunningRef.current = false;
      setIsListening(false);

      // Auto-restart if call is active and not speaking
      if (isCallActive && !isSpeaking) {
        setTimeout(() => {
          if (isCallActive && !isRecognitionRunningRef.current && !isSpeaking) {
            try {
              recognition.start();
            } catch (err) {
              console.error('[VoiceCall] Failed to restart:', err);
            }
          }
        }, 300);
      }
    };

    recognitionRef.current = recognition;

    // If call was active and recognition was running, restart with new language
    if (isCallActive && wasRunning && !isSpeakingRef.current) {
      setTimeout(() => {
        try {
          recognition.start();
        } catch (err) {
          console.error('Failed to start recognition with new language:', err);
        }
      }, 300);
    }

    return () => {
      if (isRecognitionRunningRef.current) {
        recognition.stop();
        isRecognitionRunningRef.current = false;
      }
    };
  }, [selectedLanguage, isCallActive]); // Removed isSpeaking from dependencies

  // Accumulate streaming content and auto-play when complete
  useEffect(() => {
    if (!isCallActive) {
      return;
    }

    // Continuously accumulate content while it's streaming
    if (streaming && streamingContent && streamingContent.length > 0) {
      accumulatedContentRef.current = streamingContent;
      hasSpokenRef.current = false;
    }

    // Detect when streaming transitions from true to false (stream completed!)
    const wasStreaming = wasStreamingRef.current;
    wasStreamingRef.current = streaming;

    if (wasStreaming && !streaming) {
      const contentToSpeak = accumulatedContentRef.current;

      if (contentToSpeak && contentToSpeak.length > 0 && !hasSpokenRef.current) {
        hasSpokenRef.current = true;
        accumulatedContentRef.current = '';

        // Stop recognition
        if (recognitionRef.current && isRecognitionRunningRef.current) {
          recognitionRef.current.stop();
          isRecognitionRunningRef.current = false;
        }

        // Speak
        const utterance = new SpeechSynthesisUtterance(contentToSpeak);
        utterance.lang = selectedLanguage.speechCode;

        const voices = window.speechSynthesis.getVoices();
        const voice = voices.find(v => v.lang.startsWith(selectedLanguage.code));
        if (voice) utterance.voice = voice;

        window.speechSynthesis.speak(utterance);

        // Calculate timeout: ~200ms per word + 2 second buffer
        const words = contentToSpeak.split(/\s+/).length;
        const timeoutMs = (words * 200) + 2000;

        // Force restart after timeout (Chrome bug: speaking never goes false)
        setTimeout(() => {
          if (isCallActiveRef.current && recognitionRef.current && !isRecognitionRunningRef.current) {
            try {
              recognitionRef.current.start();
              isRecognitionRunningRef.current = true;
            } catch (e) {
              console.error('[VoiceCall] Failed to restart recognition:', e);
            }
          }
        }, timeoutMs);
      }
    }
  }, [streaming, streamingContent, isCallActive, selectedLanguage]);

  const startCall = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
      return;
    }

    setIsCallActive(true);
    isCallActiveRef.current = true;
    setTranscript('');
    setIsSpeaking(false);
    accumulatedContentRef.current = '';
    hasSpokenRef.current = false;
    callStartTimeRef.current = Date.now();

    // Start duration counter
    durationIntervalRef.current = window.setInterval(() => {
      setCallDuration(Math.floor((Date.now() - callStartTimeRef.current) / 1000));
    }, 1000);

    // Start listening
    try {
      recognitionRef.current.start();
    } catch (err) {
      console.error('Failed to start recognition:', err);
    }
  };

  const endCall = () => {
    setIsCallActive(false);
    isCallActiveRef.current = false;
    setIsListening(false);
    setIsSpeaking(false);

    // Clear polling
    if (ttsPollingIntervalRef.current) {
      clearInterval(ttsPollingIntervalRef.current);
    }

    // Stop recognition and TTS
    if (recognitionRef.current) recognitionRef.current.stop();
    if (typeof window !== 'undefined') window.speechSynthesis.cancel();

    // Clear duration counter
    if (durationIntervalRef.current) clearInterval(durationIntervalRef.current);
    setCallDuration(0);
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              Voice Call
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-6 space-y-6">
          {/* Language Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Select Language {isCallActive && '(changing will restart recognition)'}
            </label>
            <div className="grid grid-cols-3 gap-2 max-h-64 overflow-y-auto">
              {SUPPORTED_LANGUAGES.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => setSelectedLanguage(lang)}
                  disabled={isCallActive && isSpeaking}
                  className={`p-3 rounded-lg border-2 transition-all ${
                    selectedLanguage.code === lang.code
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                  } ${isCallActive && isSpeaking ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                    <div className="text-2xl mb-1">{lang.flag}</div>
                    <div className="text-xs font-medium text-gray-900 dark:text-gray-100">
                      {lang.name}
                    </div>
                  </button>
                ))}
              </div>
            </div>

          {/* Call Interface */}
          {isCallActive && (
            <div className="space-y-4">
              {/* Status Indicator */}
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 mb-4">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-12 h-12 text-white">
                    <path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
                    <path d="M5.5 9.643a.75.75 0 00-1.5 0V10c0 3.06 2.29 5.585 5.25 5.954V17.5h-1.5a.75.75 0 000 1.5h4.5a.75.75 0 000-1.5h-1.5v-1.546A6.001 6.001 0 0016 10v-.357a.75.75 0 00-1.5 0V10a4.5 4.5 0 01-9 0v-.357z" />
                  </svg>
                </div>
                <div className="text-lg font-medium text-gray-900 dark:text-gray-100">
                  {selectedLanguage.flag} {selectedLanguage.name}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  {formatDuration(callDuration)}
                </div>
              </div>

              {/* Status Messages */}
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 min-h-[100px]">
                {isSpeaking && (
                  <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400">
                    <svg className="w-5 h-5 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 3.75a2 2 0 10-4 0v8.5a2 2 0 104 0v-8.5zM17.25 8a.75.75 0 00-1.5 0v4a2.5 2.5 0 01-5 0V8a.75.75 0 00-1.5 0v4a4 4 0 008 0V8z" />
                    </svg>
                    <span className="text-sm font-medium">AI is speaking...</span>
                  </div>
                )}
                {isListening && !isSpeaking && (
                  <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                    <svg className="w-5 h-5 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4z" />
                    </svg>
                    <span className="text-sm font-medium">Listening...</span>
                  </div>
                )}
                {transcript && (
                  <div className="mt-2 text-sm text-gray-700 dark:text-gray-300 italic">
                    "{transcript}"
                  </div>
                )}
                {sending && (
                  <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400 mt-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent"></div>
                    <span className="text-sm">Sending...</span>
                  </div>
                )}
                {isThinking && (
                  <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400 mt-2">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                    </div>
                    <span className="text-sm">Thinking...</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-800 flex justify-center">
          {!isCallActive ? (
            <button
              onClick={startCall}
              className="px-8 py-3 bg-green-600 hover:bg-green-700 text-white rounded-full font-medium transition-colors flex items-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                <path fillRule="evenodd" d="M2 3.5A1.5 1.5 0 013.5 2h1.148a1.5 1.5 0 011.465 1.175l.716 3.223a1.5 1.5 0 01-1.052 1.767l-.933.267c-.41.117-.643.555-.48.95a11.542 11.542 0 006.254 6.254c.395.163.833-.07.95-.48l.267-.933a1.5 1.5 0 011.767-1.052l3.223.716A1.5 1.5 0 0118 15.352V16.5a1.5 1.5 0 01-1.5 1.5H15c-1.149 0-2.263-.15-3.326-.43A13.022 13.022 0 012.43 8.326 13.019 13.019 0 012 5V3.5z" clipRule="evenodd" />
              </svg>
              Start Call
            </button>
          ) : (
            <button
              onClick={endCall}
              className="px-8 py-3 bg-red-600 hover:bg-red-700 text-white rounded-full font-medium transition-colors flex items-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
                <path fillRule="evenodd" d="M2 3.5A1.5 1.5 0 013.5 2h1.148a1.5 1.5 0 011.465 1.175l.716 3.223a1.5 1.5 0 01-1.052 1.767l-.933.267c-.41.117-.643.555-.48.95a11.542 11.542 0 006.254 6.254c.395.163.833-.07.95-.48l.267-.933a1.5 1.5 0 011.767-1.052l3.223.716A1.5 1.5 0 0118 15.352V16.5a1.5 1.5 0 01-1.5 1.5H15c-1.149 0-2.263-.15-3.326-.43A13.022 13.022 0 012.43 8.326 13.019 13.019 0 012 5V3.5z" clipRule="evenodd" />
              </svg>
              End Call
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
