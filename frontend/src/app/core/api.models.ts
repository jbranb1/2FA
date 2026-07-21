export type NextStep = 'SETUP_REQUIRED' | 'TOTP_REQUIRED';

export interface LoginResponse {
  next_step: NextStep;
  challenge_token: string;
  message: string;
}

export interface SetupResponse {
  qr_data_url: string;
  manual_key: string;
  provisioning_uri: string;
  issuer: string;
  account: string;
  period_seconds: number;
  digits: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  message: string;
}

export interface UserProfile {
  username: string;
  totp_enabled: boolean;
  totp_configured_at: string;
}
