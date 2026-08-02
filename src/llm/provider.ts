/**
 * LLM provider boundary. Disabled by default for MVP.
 * Deterministic engines must not call this path.
 */

export interface LlmMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface LlmProvider {
  readonly name: string;
  readonly enabled: boolean;
  complete(messages: LlmMessage[]): Promise<string>;
}

export class DisabledLlmProvider implements LlmProvider {
  readonly name = "disabled";
  readonly enabled = false;

  async complete(_messages: LlmMessage[]): Promise<string> {
    throw new Error(
      "LLM provider is disabled by default. MVP engines are deterministic and must not require LLM completion.",
    );
  }
}

export const defaultLlmProvider: LlmProvider = new DisabledLlmProvider();
