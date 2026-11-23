import { HttpClient, httpResource } from '@angular/common/http';
import { inject, Service } from '@angular/core';
import { Observable } from 'rxjs';
import {
  AttemptFeedback,
  Exercise,
  ExerciseType,
  Explanation,
  LearnerProfile,
  Solution,
  TopicCard,
  TopicSummary,
} from './models';

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

  /** Send one answer of the student and get the feedback of this attempt. */
  answerExercise(id: string, answer: string): Observable<AttemptFeedback> {
    return this.http.post<AttemptFeedback>(`/api/exercises/${encodeURIComponent(id)}/answer`, {
      answer,
    });
  }

  /** Close the exercise and get the solution. */
  solution(id: string): Observable<Solution> {
    return this.http.post<Solution>(`/api/exercises/${encodeURIComponent(id)}/solution`, {});
  }

  /** Ask the backend to prepare exercises in advance. Fire and forget (202). */
  prefetch(topicId: string): Observable<void> {
    return this.http.post<void>(`/api/topics/${encodeURIComponent(topicId)}/prefetch`, null);
  }

  /** Ask the Tutor for a new explanation of a topic. This can take 5 to 15 seconds. */
  explain(topicId: string): Observable<Explanation> {
    return this.http.post<Explanation>(`/api/topics/${encodeURIComponent(topicId)}/explain`, {});
  }

  /** The learning profile of the student. */
  progress() {
    return httpResource<LearnerProfile>(() => '/api/progress');
  }
}
