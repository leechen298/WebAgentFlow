# WebAgentFlow Prompt Assets

Prompt assets are versioned product runtime assets. Service code loads prompts
by `prompt_id` and `version`; it must not embed long Agent system prompts.

Shared fragments hold product-wide boundaries. Agent folders hold only the
role-specific prompt body and metadata.
