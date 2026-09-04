import { createFileRoute } from "@tanstack/react-router";

import { ChatView } from "@/components/nova/chat-view";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Nova AI — Your everyday AI assistant" },
      {
        name: "description",
        content:
          "Nova AI is a fast, focused chat assistant for writing, analysis, and research — with file uploads and threaded conversations.",
      },
      { property: "og:title", content: "Nova AI — Your everyday AI assistant" },
      {
        property: "og:description",
        content: "Chat, upload files, and organize threads in a calm, focused AI workspace.",
      },
    ],
  }),
  component: NewChatPage,
});

function NewChatPage() {
  return <ChatView chatId={null} />;
}
