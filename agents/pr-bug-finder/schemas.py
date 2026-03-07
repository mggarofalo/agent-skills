"""JSON schema contracts for structured output between hunter and challenger agents."""

BUG_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "bugs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique bug identifier, e.g. BUG-001",
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                    "category": {
                        "type": "string",
                        "description": "Bug category, e.g. logic-error, race-condition, null-deref, security, resource-leak, off-by-one, type-error, missing-validation",
                    },
                    "description": {
                        "type": "string",
                        "description": "Clear, concise description of the bug",
                    },
                    "justification": {
                        "type": "string",
                        "description": "Detailed reasoning for why this is a bug, referencing specific code",
                    },
                    "location": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "line_start": {"type": "integer"},
                            "line_end": {"type": "integer"},
                        },
                        "required": ["file", "line_start", "line_end"],
                    },
                    "in_scope": {
                        "type": "boolean",
                        "description": "True if the bug is in code changed by the diff, false if in surrounding context",
                    },
                    "suggested_fix": {
                        "type": "string",
                        "description": "Optional suggested fix for the bug",
                    },
                },
                "required": [
                    "id",
                    "severity",
                    "category",
                    "description",
                    "justification",
                    "location",
                    "in_scope",
                ],
            },
        },
        "summary": {
            "type": "string",
            "description": "Brief overall summary of findings",
        },
    },
    "required": ["bugs", "summary"],
}

CHALLENGE_REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "challenges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "bug_id": {
                        "type": "string",
                        "description": "The bug ID being challenged, e.g. BUG-001",
                    },
                    "verdict": {
                        "type": "string",
                        "enum": ["confirmed", "rejected", "follow-up"],
                        "description": "confirmed = real bug in scope; rejected = not a real bug; follow-up = real issue but pre-existing or out of scope, recommend as a separate defect report",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Detailed reasoning for the verdict, referencing specific code",
                    },
                    "revised_severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Revised severity if different from original (only when verdict is confirmed)",
                    },
                    "severity_change_reasoning": {
                        "type": "string",
                        "description": "Reasoning for severity change, if any",
                    },
                },
                "required": ["bug_id", "verdict", "reasoning"],
            },
        },
        "summary": {
            "type": "string",
            "description": "Brief overall summary of challenge results",
        },
    },
    "required": ["challenges", "summary"],
}
