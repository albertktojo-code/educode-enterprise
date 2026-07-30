export type InstrumentDashboard = {
  licenses: number;
  protocols: number;
  norm_groups: number;
  imports: number;
  interpretations: number;
};

export type RomanGonzalezTemplate = {
  template_code: string;
  name: string;
  support_level: string;
  requires_license: boolean;
  protected_items_included: boolean;
  allowed_configuration: string[];
  notice: string;
};

export type LicenseSummary = {
  id: string;
  instrument_id: string;
  status: string;
  license_holder: string;
  valid_from?: string | null;
  valid_until?: string | null;
};
