/**
 * Hard guard: no MVP path may mutate a connected system.
 */
export class MutationRejectedError extends Error {
  readonly code = "MUTATION_REJECTED" as const;

  constructor(message = "Mutation/apply is not implemented. MVP is read-only and advisory-only.") {
    super(message);
    this.name = "MutationRejectedError";
  }
}

export function rejectMutation(_changeSet?: unknown): never {
  throw new MutationRejectedError();
}
