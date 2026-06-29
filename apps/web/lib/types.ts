export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Org {
  id: string;
  name: string;
  slug: string;
  plan: string;
}

export interface Branch {
  id: string;
  org_id: string;
  name: string;
  address: string | null;
  timezone: string;
}

export interface Link {
  id: string;
  org_id: string;
  branch_id: string | null;
  code: string;
  slug: string | null;
  type: string;
  is_active: boolean;
}

export interface Destination {
  id: string;
  smartlink_id: string;
  label: string;
  url: string;
  kind: string;
  priority: number;
  weight: number;
  is_active: boolean;
}

export interface Media {
  id: string;
  smartlink_id: string;
  medium_type: string;
  serial: string | null;
}

export interface Member {
  id: string;
  user_id: string;
  org_id: string;
  email: string;
  role: string;
}

export const DESTINATION_KINDS = [
  "review_2gis",
  "google_maps",
  "apple_maps",
  "yandex_maps",
  "instagram",
  "whatsapp",
  "telegram",
  "url",
] as const;

export const MEDIUM_TYPES = [
  "nfc_card",
  "nfc_stand",
  "nfc_sticker",
  "qr_stand",
  "business_card",
] as const;
