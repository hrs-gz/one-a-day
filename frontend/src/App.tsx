import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Algorithm } from "./pages/Algorithm";
import { Dashboard } from "./pages/Dashboard";

export function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="algorithm" element={<Algorithm />} />
      </Route>
    </Routes>
  );
}
