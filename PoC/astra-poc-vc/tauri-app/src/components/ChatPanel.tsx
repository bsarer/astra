import React from "react";
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

export function ChatPanel() {
  return (
    <div className="aios-chat-panel">
      <CopilotChat
        labels={{
          title: "Astra",
          initial: "Hi Mike — ask me anything or say \"show me my dashboard\".",
          placeholder: "Ask Astra anything…",
        }}
      />
    </div>
  );
}
