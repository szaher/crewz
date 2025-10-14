'use client';

// Dynamic chat route that reuses the ChatRoot UI.
// ChatRoot detects the sessionId from the pathname (/chat/[sessionId]).

import ChatRoot from '../ChatRoot';

export default function SessionChatPage() {
  return <ChatRoot />;
}
