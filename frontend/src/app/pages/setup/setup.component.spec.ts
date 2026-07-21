import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NEVER, of } from 'rxjs';
import { AuthService } from '../../core/auth.service';
import { SetupComponent } from './setup.component';

describe('SetupComponent', () => {
  it('prevents native navigation and confirms a valid TOTP code', async () => {
    let confirmedCode = '';
    const auth = {
      hasChallenge: () => true,
      getSetup: () => of({
        qr_data_url: 'data:image/svg+xml;base64,PHN2Zy8+',
        manual_key: 'SECRET',
        provisioning_uri: 'otpauth://totp/MFA%20Lab:demo',
        issuer: 'MFA Lab',
        account: 'demo',
        period_seconds: 30,
        digits: 6,
      }),
      confirmEnrollment: (code: string) => {
        confirmedCode = code;
        return NEVER;
      },
      errorMessage: () => 'error',
    };
    await TestBed.configureTestingModule({
      imports: [SetupComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: auth },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(SetupComponent);
    fixture.detectChanges();
    const input: HTMLInputElement = fixture.nativeElement.querySelector('#setup-code');
    const form: HTMLFormElement = fixture.nativeElement.querySelector('form');
    input.value = '123456';
    input.dispatchEvent(new Event('input', { bubbles: true }));

    const submitted = form.dispatchEvent(new Event('submit', {
      bubbles: true,
      cancelable: true,
    }));

    expect(submitted).toBe(false);
    expect(confirmedCode).toBe('123456');
  });
});
