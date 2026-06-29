import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';
import { HomeComponent } from './pages/home/home.component';
import { LoginComponent } from './pages/login/login.component';
import { SetupComponent } from './pages/setup/setup.component';
import { VerifyComponent } from './pages/verify/verify.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent, title: 'Ingreso | MFA Lab' },
  { path: 'mfa/setup', component: SetupComponent, title: 'Configurar TOTP | MFA Lab' },
  { path: 'mfa/verify', component: VerifyComponent, title: 'Verificar TOTP | MFA Lab' },
  { path: 'home', component: HomeComponent, canActivate: [authGuard], title: 'Sesión protegida | MFA Lab' },
  { path: '', pathMatch: 'full', redirectTo: 'login' },
  { path: '**', redirectTo: 'login' },
];
