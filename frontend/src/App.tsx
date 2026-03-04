import { Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Layout } from "./components/Layout";
import { Algorithm } from "./pages/Algorithm";
import { Dashboard } from "./pages/Dashboard";
import { History } from "./pages/History";
import { Settings } from "./pages/Settings";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route
          index
          element={
            <ErrorBoundary pageName="Dashboard">
              <Dashboard />
            </ErrorBoundary>
          }
        />
        <Route
          path="algorithm"
          element={
            <ErrorBoundary pageName="Algorithm">
              <Algorithm />
            </ErrorBoundary>
          }
        />
        <Route
          path="history"
          element={
            <ErrorBoundary pageName="History">
              <History />
            </ErrorBoundary>
          }
        />
        <Route
          path="settings"
          element={
            <ErrorBoundary pageName="Settings">
              <Settings />
            </ErrorBoundary>
          }
        />
      </Route>
    </Routes>
  );
}
