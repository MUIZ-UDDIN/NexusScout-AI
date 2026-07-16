export interface Lead {
  id: string;
  section_id: string | null;
  name: string;
  website: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  status: string;
  search_query: string | null;
  created_at: string;
}

export interface LeadStats {
  total: number;
  enriched: number;
  failed: number;
}
