import { useState, useCallback } from 'react';

const API_BASE = 'http://localhost:8080';

export default function useChat() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const sendMessage = useCallback(async (userText, product) => {
    if (!userText.trim() || isStreaming) return;

    const userMsg = { role: 'user', content: userText };
    const assistantMsg = { role: 'assistant', content: '' };

    // Capture history before adding new messages
    const history = messages
      .filter((m) => m.content)
      .map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText, product, history }),
      });

      if (!response.ok) {
        throw new Error(`Backend returned HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;
          const jsonStr = trimmed.slice(5).trim();
          if (jsonStr === '[DONE]') continue;
          try {
            const parsed = JSON.parse(jsonStr);
            const delta = parsed.choices?.[0]?.delta?.content;
            if (delta) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === 'assistant') {
                  updated[updated.length - 1] = { ...last, content: last.content + delta };
                }
                return updated;
              });
            }
          } catch {
            // skip malformed SSE lines
          }
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === 'assistant' && !last.content) {
          updated[updated.length - 1] = {
            ...last,
            content: `⚠️ Error: ${err.message}. Is the backend running on port 8080?`,
          };
        }
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  }, [messages, isStreaming]);

  return { messages, isStreaming, sendMessage, clearMessages };
}
