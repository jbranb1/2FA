import { Component, OnInit, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { SetupResponse } from '../../core/api.models';
import { AuthService } from '../../core/auth.service';
import { normalizeTotpCode, TOTP_CODE_ERROR } from '../../core/totp-code';

@Component({
  selector: 'app-setup',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './setup.component.html',
})
export class SetupComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly setup = signal<SetupResponse | null>(null);
  readonly loading = signal(true);
  readonly submitting = signal(false);
  readonly error = signal('');
  readonly code = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.pattern(/^\d{6}$/)],
  });

  ngOnInit(): void {
    if (!this.auth.hasChallenge()) {
      void this.router.navigateByUrl('/login');
      return;
    }
    this.auth.getSetup().pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (setup) => this.setup.set(setup),
      error: (error) => this.error.set(this.auth.errorMessage(error)),
    });
  }

  confirm(event: SubmitEvent): void {
    event.preventDefault();
    if (this.submitting()) return;
    this.code.markAsTouched();
    if (this.code.invalid) {
      this.error.set(TOTP_CODE_ERROR);
      return;
    }
    this.error.set('');
    this.submitting.set(true);
    this.auth.confirmEnrollment(this.code.value)
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
