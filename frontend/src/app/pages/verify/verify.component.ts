import { Component, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/auth.service';
import { normalizeTotpCode, TOTP_CODE_ERROR } from '../../core/totp-code';

@Component({
  selector: 'app-verify',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './verify.component.html',
})
export class VerifyComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly submitting = signal(false);
  readonly error = signal('');
  readonly code = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.pattern(/^\d{6}$/)],
  });

  constructor() {
    if (!this.auth.hasChallenge()) void this.router.navigateByUrl('/login');
  }

  verify(event: SubmitEvent): void {
    event.preventDefault();
    if (this.submitting()) return;
    this.code.markAsTouched();
    if (this.code.invalid) {
      this.error.set(TOTP_CODE_ERROR);
      return;
    }
    this.error.set('');
    this.submitting.set(true);
    this.auth.verifyTotp(this.code.value)
      .pipe(finalize(() => this.submitting.set(false)))
      .subscribe({
        next: () => void this.router.navigateByUrl('/home'),
        error: (error) => this.error.set(this.auth.errorMessage(error)),
      });
  }

  onCodeInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    const normalized = normalizeTotpCode(input.value);
    input.value = normalized;
    this.code.setValue(normalized);
    this.error.set('');
  }
}
