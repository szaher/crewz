// SIMPLE VERSION - Just the auto-play logic

// When streaming stops, speak and restart recognition
if (wasStreaming && !streaming) {
  const contentToSpeak = accumulatedContentRef.current;

  if (contentToSpeak && contentToSpeak.length > 0) {
    // Stop recognition
    if (recognitionRef.current) recognitionRef.current.stop();

    // Speak
    const utterance = new SpeechSynthesisUtterance(contentToSpeak);
    utterance.lang = selectedLanguage.speechCode;

    const voices = window.speechSynthesis.getVoices();
    const voice = voices.find(v => v.lang.startsWith(selectedLanguage.code));
    if (voice) utterance.voice = voice;

    window.speechSynthesis.speak(utterance);

    // Poll until done, then restart recognition
    const checkDone = setInterval(() => {
      if (!window.speechSynthesis.speaking) {
        clearInterval(checkDone);
        setTimeout(() => {
          if (recognitionRef.current) recognitionRef.current.start();
        }, 500);
      }
    }, 100);
  }
}
