from reusable_helpers.agents.payload_redaction import PayloadRedactor, RegexRedactionRule

payload = {
    "customer": {"email": "alice@example.test", "api_key": "example-key"},
    "messages": ["Email alice@example.test"],
    "active": True,
}
redactor = PayloadRedactor(
    sensitive_fields=["api_key"],
    text_rules=[RegexRedactionRule(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[EMAIL]")],
)

result = redactor.redact(payload)
print(result.value)
print(f"Replacements: {result.replacements}")
