import { createFileRoute } from "@tanstack/react-router";

import { ChatView } from "@/components/nova/chat-view";

export const Route = createFileRoute("/c/$chatId")({
  head: () => ({
    meta: [
      { title: "Conversation — Nova AI" },
      {
        name: "description",
        content: "Continue your Nova AI conversation with full history, files, and model controls.",
      },
      { property: "og:title", content: "Conversation — Nova AI" },
      {
        property: "og:description",
        content: "Pick up where you left off in this Nova AI thread.",
      },
    ],
  }),
  component: ChatPage,
});

function ChatPage() {
  const { chatId } = Route.useParams();
  return <ChatView chatId={chatId} />;
}
