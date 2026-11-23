import { HttpClient, httpResource } from '@angular/common/http';
import { inject, Service } from '@angular/core';
import { Observable } from 'rxjs';
import { Exercise, ExerciseType, Feedback, TopicCard, TopicSummary } from './models';

/**
 * The only access point to the backend REST API.
 * Call the resource methods in an injection context (for example, a field initializer).
 */
@Service()
export class Api {
  private readonly http = inject(HttpClient);

  topics() {
    return httpResource<TopicSummary[]>(() => '/api/topics', { defaultValue: [] });
  }

  topic(id: () => string | null) {
    return httpResource<TopicCard>(() => {
      const value = id();
      return value ? `/api/topics/${encodeURIComponent(value)}` : undefined;
    });
  }

  /** Ask the Tutor for a new exercise. This can take 5 to 15 seconds. */
  createExercise(topicId: string, type?: ExerciseType): Observable<Exercise> {
    return this.http.post<Exercise>('/api/exercises', { topic_id: topicId, type });
  }

  /** Send the answer of the student and get the feedback. */
  answerExercise(id: string, answer: string): Observable<Feedback> {
    return this.http.post<Feedback>(`/api/exercises/${encodeURIComponent(id)}/answer`, { answer });
  }

  /** Ask the backend to prepare exercises in advance. Fire and forget (202). */
  prefetch(topicId: string): Observable<void> {
    return this.http.post<void>(`/api/topics/${encodeURIComponent(topicId)}/prefetch`, null);
  }
}
