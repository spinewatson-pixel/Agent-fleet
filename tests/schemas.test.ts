import { describe, expect, it } from "vitest";
import {
  CanonicalOrganizationSchema,
  KnowledgeObjectSchema,
  OrganizationSchema,
} from "../src/core/schemas/entities.js";
import { SCHEMA_VERSION } from "../src/core/schemas/common.js";
import { KNOWLEDGE_OBJECTS } from "../src/core/knowledge/knowledgeObjects.js";
import { nowIso } from "../src/core/util/ids.js";

describe("schemas", () => {
  it("validates organization entity with metadata", () => {
    const ts = nowIso();
    const org = OrganizationSchema.parse({
      id: "org_1",
      schemaVersion: SCHEMA_VERSION,
      createdAt: ts,
      updatedAt: ts,
      name: "Test",
      owners: ["a"],
    });
    expect(org.environment).toBe("unknown");
    expect(org.schemaVersion).toBe(SCHEMA_VERSION);
  });

  it("validates knowledge objects fixture", () => {
    expect(KNOWLEDGE_OBJECTS.length).toBeGreaterThanOrEqual(6);
    for (const ko of KNOWLEDGE_OBJECTS) {
      expect(() => KnowledgeObjectSchema.parse(ko)).not.toThrow();
    }
  });

  it("rejects canonical org without organization name", () => {
    const ts = nowIso();
    expect(() =>
      CanonicalOrganizationSchema.parse({
        schemaVersion: SCHEMA_VERSION,
        organization: {
          id: "x",
          schemaVersion: SCHEMA_VERSION,
          createdAt: ts,
          updatedAt: ts,
          name: "",
        },
      }),
    ).toThrow();
  });
});
