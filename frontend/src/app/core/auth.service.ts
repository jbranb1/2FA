import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { LoginResponse, SetupResponse, TokenResponse, UserProfile } from './api.models';

const API_URL = 'http://localhost:8000/api';
const DEMO_RESET_KEY = 'local-demo-reset';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly storage = typeof sessionStorage === 'undefined' ? null : sessionStorage;
  private readonly accessTokenState = signal(this.storage?.getItem('mfa_access') ?? '');
  private readonly challengeState = signal(this.storage?.getItem('mfa_challenge') ?? '');
  private readonly usernameState = signal(this.storage?.getItem('mfa_username') ?? 'demo');

  readonly authenticated = computed(() => this.accessTokenState().length > 0);
  readonly username = this.usernameState.asReadonly();

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(API_URL + '/auth/login', { username, password }).pipe(
      tap((response) => {
        this.usernameState.set(username);
        this.challengeState.set(response.challenge_token);
        this.storage?.setItem('mfa_username', username);
        this.storage?.setItem('mfa_challenge', response.challenge_token);
      }),
    );
  }

  getSetup(): Observable<SetupResponse> {
    return this.http.post<SetupResponse>(API_URL + '/auth/totp/setup', {
      challenge_token: this.challengeState(),
    });
  }

  confirmEnrollment(code: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(API_URL + '/auth/totp/confirm', {
      challenge_token: this.challengeState(),
      code,
    }).pipe(tap((response) => this.storeAccess(response.access_token)));
  }

  verifyTotp(code: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(API_URL + '/auth/totp/verify', {
      challenge_token: this.challengeState(),
      code,
    }).pipe(tap((response) => this.storeAccess(response.access_token)));
  }

  profile(): Observable<UserProfile> {
    return this.http.get<UserProfile>(API_URL + '/auth/me', { headers: this.authHeaders() });
  }

  logout(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(API_URL + '/auth/logout', {}, {
      headers: this.authHeaders(),
    }).pipe(tap(() => this.clearSession()));
  }

  resetDemo(): Observable<{ message: string }> {
    const headers = new HttpHeaders({ 'X-Demo-Key': DEMO_RESET_KEY });
    return this.http.post<{ message: string }>(API_URL + '/dev/reset-totp', {
      username: this.usernameState() || 'demo',
    }, { headers }).pipe(tap(() => this.clearSession()));
  }

  hasChallenge(): boolean {
    return this.challengeState().length > 0;
  }

  clearSession(): void {
    this.accessTokenState.set('');
    this.challengeState.set('');
    this.storage?.removeItem('mfa_access');
    this.storage?.removeItem('mfa_challenge');
  }

  errorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      return error.error?.detail ?? 'No fue posible comunicarse con el backend.';
    }
    return 'Ocurrió un error inesperado.';
  }

  private storeAccess(token: string): void {
    this.accessTokenState.set(token);
    this.challengeState.set('');
    this.storage?.setItem('mfa_access', token);
    this.storage?.removeItem('mfa_challenge');
  }

  private authHeaders(): HttpHeaders {
    return new HttpHeaders({ Authorization: 'Bearer ' + this.accessTokenState() });
  }
}
