import React from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { Dashboard } from "./components/Dashboard";
import { ChatPanel } from "./components/ChatPanel";

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 24, color: "#ef4444", fontFamily: "monospace" }}>
          <h2>React Error</h2>
          <pre>{this.state.error.message}</pre>
          <pre>{this.state.error.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  return (
    <ErrorBoundary>
      <CopilotKit runtimeUrl="/api/copilotkit" agent="astra_agent">
        <div className="aios-layout">
          <Dashboard />
          <ChatPanel />
        </div>
      </CopilotKit>
    </ErrorBoundary>
  );
}

export default App;
