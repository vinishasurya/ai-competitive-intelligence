"""Shared model-call helpers: structured parsing + usage/cost accounting."""

import anthropic

from app import config


class Usage:
    """Accumulates token usage and cost across the model calls of one run."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost_cents = 0.0

    def add(self, model: str, usage) -> None:
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cost_cents += config.estimate_cost_cents(
            model, usage.input_tokens, usage.output_tokens
        )


def parse(model: str, system: str, user: str, output_format, usage: Usage,
          max_tokens: int = 8000):
    """One structured-output call; the response is validated against output_format."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    kwargs = {}
    if model == config.MODEL_PROFILER:
        kwargs["thinking"] = {"type": "adaptive"}
    response = client.messages.parse(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_format=output_format,
        **kwargs,
    )
    usage.add(model, response.usage)
    return response.parsed_output
