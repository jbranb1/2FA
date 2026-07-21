import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { UserProfile } from '../../core/api.models';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-home',
  imports: [DatePipe],
  templateUrl: './home.component.html',
})
export class HomeComponent implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  readonly profile = signal<UserProfile | null>(null);
  readonly error = signal('');
  readonly resetting = signal(false);

  ngOnInit(): void {
    this.auth.profile().subscribe({
      next: (profile) => this.profile.set(profile),
      error: (error) => {
        this.auth.clearSession();
        this.error.set(this.auth.errorMessage(error));
        void this.router.navigateByUrl('/login');
      },
    });
  }

  logout(): void {
    this.auth.logout().subscribe({
      next: () => void this.router.navigateByUrl('/login'),
      error: () => {
        this.auth.clearSession();
        void this.router.navigateByUrl('/login');
      },
    });
  }

  reset(): void {
    if (this.resetting()) return;
    this.resetting.set(true);
    this.auth.resetDemo().pipe(finalize(() => this.resetting.set(false))).subscribe({
      next: () => void this.router.navigateByUrl('/login'),
      error: (error) => this.error.set(this.auth.errorMessage(error)),
    });
  }
}
