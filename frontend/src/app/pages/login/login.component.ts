import { Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/auth.service';

@Component({ selector: 'app-login', imports: [ReactiveFormsModule], templateUrl: './login.component.html' })
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly loading = signal(false);
  readonly resetting = signal(false);
  readonly error = signal('');
  readonly notice = signal('');
  readonly form = new FormGroup({
    username: new FormControl('demo', { nonNullable: true, validators: [Validators.required] }),
    password: new FormControl('Demo2FA!2026', { nonNullable: true, validators: [Validators.required] }),
  });

  submit(): void {
    if (this.form.invalid || this.loading()) return;
    this.error.set('');
    this.notice.set('');
    this.loading.set(true);
    const { username, password } = this.form.getRawValue();
    this.auth.login(username, password).pipe(finalize(() => this.loading.set(false))).subscribe({
      next: (response) => {
        const route = response.next_step === 'SETUP_REQUIRED' ? '/mfa/setup' : '/mfa/verify';
        void this.router.navigateByUrl(route);
      },
      error: (error) => this.error.set(this.auth.errorMessage(error)),
    });
  }

  resetDemo(): void {
    if (this.resetting()) return;
    this.error.set('');
    this.notice.set('');
    this.resetting.set(true);
    this.auth.resetDemo().pipe(finalize(() => this.resetting.set(false))).subscribe({
      next: (response) => this.notice.set(response.message),
      error: (error) => this.error.set(this.auth.errorMessage(error)),
    });
  }
}
