import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { Done } from "./pages/Done";
import { Evidence } from "./pages/Evidence";
import { Inbox } from "./pages/Inbox";
import { LiveInvestigation } from "./pages/LiveInvestigation";
import { Memory } from "./pages/Memory";
import { NewInvestigation } from "./pages/NewInvestigation";
import { Review } from "./pages/Review";

export default function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Inbox />} />
          <Route path="/new" element={<NewInvestigation />} />
          <Route path="/inv/:id" element={<LiveInvestigation />} />
          <Route path="/inv/:id/evidence" element={<Evidence />} />
          <Route path="/inv/:id/review" element={<Review />} />
          <Route path="/inv/:id/done" element={<Done />} />
          <Route path="/memory" element={<Memory />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
