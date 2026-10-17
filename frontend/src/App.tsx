import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { AccessGate } from "./components/AccessGate";
import { AppShell } from "./components/AppShell";
import { Capa } from "./pages/Capa";
import { Complaints } from "./pages/Complaints";
import { Dashboard } from "./pages/Dashboard";
import { Done } from "./pages/Done";
import { Evidence } from "./pages/Evidence";
import { LiveInvestigation } from "./pages/LiveInvestigation";
import { Memory } from "./pages/Memory";
import { NewInvestigation } from "./pages/NewInvestigation";
import { Plant } from "./pages/Plant";
import { Review } from "./pages/Review";

// Lifecycle order (left to right = the quality engineer's working sequence): see the
// state (Dashboard) -> pick the work (Complaints) -> act on it (CAPA) -> remember it
// (Memory) -> check the evidence (Plant). "/" now lands on the Dashboard, not the
// inbox -- every other investigation-flow route (/new, /inv/:id/*) is unchanged.
export default function App() {
  return (
    <AccessGate>
      <BrowserRouter>
        <AppShell>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/complaints" element={<Complaints />} />
            <Route path="/capa" element={<Capa />} />
            <Route path="/memory" element={<Memory />} />
            <Route path="/plant" element={<Plant />} />
            <Route path="/new" element={<NewInvestigation />} />
            <Route path="/inv/:id" element={<LiveInvestigation />} />
            <Route path="/inv/:id/evidence" element={<Evidence />} />
            <Route path="/inv/:id/review" element={<Review />} />
            <Route path="/inv/:id/done" element={<Done />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AppShell>
      </BrowserRouter>
    </AccessGate>
  );
}
