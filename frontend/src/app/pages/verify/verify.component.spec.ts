import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NEVER } from 'rxjs';
import { AuthService } from '../../core/auth.service';
import { VerifyComponent } from './verify.component';

describe('VerifyComponent', () => {
  it('prevents native navigation and verifies a valid TOTP code', async () => {
    let verifiedCode = '';
    const auth = {
      hasChallenge: () => true,
      verifyTotp: (code: string) => {
        verifiedCode = code;
        return NEVER;
      },
      errorMessage: () => 'error',
    };
    await TestBed.configureTestingModule({
      imports: [VerifyComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: auth },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(VerifyComponent);
    fixture.detectChanges();
    const input: HTMLInputElement = fixture.nativeElement.querySelector('#verify-code');
    const form: HTMLFormElement = fixture.nativeElement.querySelector('form');
    input.value = '654321';
    input.dispatchEvent(new Event('input', { bubbles: true }));

    const submitted = form.dispatchEvent(new Event('submit', {
      bubbles: true,
      cancelable: true,
    }));

    expect(submitted).toBe(false);
    expect(verifiedCode).toBe('654321');
  });
});
