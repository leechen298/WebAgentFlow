import exampleSkillSchemaJson from './example-skill.json';

export interface SkillSchema {
  skill: string;
  version: string;
  steps: unknown[];
}

export const exampleSkillSchema: SkillSchema = exampleSkillSchemaJson;
