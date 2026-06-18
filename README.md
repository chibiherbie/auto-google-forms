# Auto Google Forms

CLI and backend core for controlled Google Forms that the user owns
or is authorized to test.

This project is not intended for inflating results in third-party surveys,
bypassing CAPTCHA, rate limits, or other protection mechanisms.

## CLI

Start the interactive menu:

```bash
uv run python main.py
```

The menu can:

- load a public form by URL;
- choose one of the saved forms;
- show information and validate the config;
- update or run the selected form;
- create an example JSON config.

Adding and updating already load the public Google Form HTML page. Single-choice
questions, dropdowns, checkboxes, and grids are supported. Each grid row is
stored as a separate question with `group_title` and its own ID. Forms that
require Google sign-in are not supported yet.

The HTML parser is isolated as an external adapter: the public page structure is
not a stable Google API.

## Config Format

For `type: "single_choice"`, the sum of `count` values for the question must
exactly match `total_responses`.

For `type: "checkbox"`, each `count` defines how many responses should include
that specific option. The sum can be greater than `total_responses`, but each
individual `count` cannot exceed it.

```json
{
  "schema_version": 1,
  "form": {
    "id": "example-form-id",
    "title": "Example survey",
    "source_url": "https://docs.google.com/forms/d/e/example",
    "questions": [
      {
        "id": "entry.123456",
        "title": "Choose one",
        "type": "single_choice",
        "required": true,
        "options": ["A", "B"]
      }
    ]
  },
  "response_plan": {
    "total_responses": 10,
    "answers": {
      "entry.123456": [
        {"value": "A", "count": 6},
        {"value": "B", "count": 4}
      ]
    }
  }
}
```

The JSON file stores a snapshot of the form structure. When a form is updated,
the parser adapter should update the `form` section, preserve compatible user
targets from `response_plan`, and clearly report conflicts for removed or
changed questions. Question IDs are stored in the submission-ready
`entry.<numeric_id>` format. Older configs with numeric IDs must be imported
again.
