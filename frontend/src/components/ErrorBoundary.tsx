import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  pageName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (!this.state.hasError) {
      return this.props.children;
    }
    const page = this.props.pageName ? ` on the ${this.props.pageName} page` : "";
    return (
      <div
        role="alert"
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "1rem",
          padding: "3rem 1.5rem",
          color: "var(--ink-gray)",
          textAlign: "center",
        }}
      >
        <p style={{ fontSize: "0.95rem", margin: 0 }}>
          Something went wrong{page}.
        </p>
        <button
          onClick={this.handleReset}
          style={{
            fontSize: "0.85rem",
            padding: "6px 16px",
            backgroundColor: "var(--accent)",
            color: "#fff",
            border: "none",
            borderRadius: "var(--radius-md)",
            cursor: "pointer",
          }}
        >
          Try again
        </button>
      </div>
    );
  }
}
