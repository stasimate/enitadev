import { Routes } from '@angular/router';
import { StudyPage } from './features/study/study-page';

export const routes: Routes = [
  { path: '', component: StudyPage },
  {
    path: 'progressi',
    loadComponent: () => import('./features/progress/progress-page').then((m) => m.ProgressPage),
  },
  { path: '**', redirectTo: '' },
];
