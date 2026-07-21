import { normalizeTotpCode } from './totp-code';

describe('normalizeTotpCode', () => {
  it('accepts a six-digit code', () => {
    expect(normalizeTotpCode('123456')).toBe('123456');
  });

  it('removes the visual space used by authenticator apps', () => {
    expect(normalizeTotpCode('123 456')).toBe('123456');
  });

  it('drops non-digits and limits the result to six digits', () => {
    expect(normalizeTotpCode('12-34-5678')).toBe('123456');
  });
});
