import type { RouteObject } from "react-router-dom";

import { InstrumentGovernancePage } from "./InstrumentGovernancePage";
import { InstrumentResultsPage } from "./InstrumentResultsPage";

export const instrumentGovernanceRoutes: RouteObject[] = [
  { path: "/admin/instrument-governance", element: <InstrumentGovernancePage /> },
  { path: "/teacher/instrument-results", element: <InstrumentResultsPage /> },
];
