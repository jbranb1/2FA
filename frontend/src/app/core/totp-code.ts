export const TOTP_CODE_LENGTH = 6;
export const TOTP_CODE_ERROR = 'Ingresa los 6 dígitos que muestra Google Authenticator.';

export function normalizeTotpCode(value: string): string {
  return value.replace(/\D/g, '').slice(0, TOTP_CODE_LENGTH);
}
