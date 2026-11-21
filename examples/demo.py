from neuroformatting import FieldRule, OutputSchema, StreamGuard


def main() -> None:
    schema = OutputSchema(
        fields=[
            FieldRule(name="answer", expected_type=str, required=True),
            FieldRule(
                name="confidence",
                expected_type=float,
                required=True,
                semantic_check=lambda val, ctx: 0.0 <= val <= 1.0,
                error_message="confidence must be between 0.0 and 1.0",
            ),
            FieldRule(
                name="source_id",
                expected_type=str,
                required=True,
                semantic_check=lambda val, ctx: val in ctx.get("allowed_sources", []),
                error_message="source_id is not grounded in allowed context sources",
            ),
        ]
    )

    context = {"allowed_sources": ["doc-101", "doc-204"]}

    # Simulated streamed LLM chunks (with markdown fence + out-of-context source_id)
    streamed_chunks = [
        "```json\n",
        '{"answer": "Schema validation runs before committing output.", ',
        '"confidence": 0.92, ',
        '"source_id": "doc-999"}',
        "\n```",
    ]

    guard = StreamGuard(schema=schema, context=context)
    result = guard.run_stream(streamed_chunks)

    print("Valid:", result.ok)
    print("Errors:", result.errors)
    print("Data:", result.data)


if __name__ == "__main__":
    main()
