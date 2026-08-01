import { api } from "../../lib/api";
import type { InstrumentDashboard, LicenseSummary, RomanGonzalezTemplate } from "./types";

const BASE = "/instrument-governance";

export const instrumentGovernanceApi = {
  dashboard: () => api.get<InstrumentDashboard>(`${BASE}/dashboard`),
  licenses: () => api.get<LicenseSummary[]>(`${BASE}/licenses`),
  romanGonzalezTemplate: () =>
    api.get<RomanGonzalezTemplate>(`${BASE}/templates/roman-gonzalez`),
};
