# Hangboard issue reporting

Hang Ten accepts text-only hangboard corrections through a public Tally form.
Reporters do not need a GitHub account. Tally sends each submission to Zapier,
which creates a labelled issue in `Asherlc/hang-ten` through a maintainer-owned
GitHub connection.

## Live configuration

- Published Tally form URL: `https://tally.so/r/XxbJG4`
- GitHub repository: `Asherlc/hang-ten`
- GitHub label: `hangboard-report`
- Zap: Tally **New Submission** → GitHub **Create Issue**

The form URL is public configuration, not a secret. Set the same published URL
as `HANGBOARD_REPORT_FORM_URL` in both iOS and Android release builds. A blank
or invalid value must keep the report action unavailable.

## Immutable form contract

Create and publish a Tally form titled **Report a Hang Ten hangboard issue**.
Keep it text-only: do not add upload, screenshot, email, name, device ID,
location, or workout-history questions.

Add these required visible fields in this order:

1. **Category** — single choice with exactly these values:
   - `Incorrect hold/specification`
   - `Missing or incorrect board`
   - `Other`
2. **Title** — short text.
3. **Description** — long text.

Add `/recaptcha` immediately above Submit. Do not add any other visible field.

Add these eight Tally hidden fields with the exact lowercase names below. They
are populated through URL query parameters and must not appear as editable
questions:

| Hidden field | Meaning |
| --- | --- |
| `board_id` | Stable board package identifier. |
| `board_name` | Display name of the selected board. |
| `manufacturer` | Board manufacturer. |
| `presentation_id` | Stable identifier of the selected physical presentation. |
| `presentation_name` | Display name of the selected physical presentation. |
| `platform` | Exactly `iOS` or `Android`. |
| `app_version` | Public app version. |
| `build` | App build number. |

Phone portrait or landscape orientation is a layout concern and is not form
data. Do not add interface orientation, physical-device identifiers, or extra
query keys to this contract.

## GitHub label

Create `hangboard-report` in `Asherlc/hang-ten`. This repository currently uses
color `#1D76DB` and description “Reports about hangboard data or
specifications.” Verify it without exposing any credentials:

```sh
rtk gh label list --repo Asherlc/hang-ten --search hangboard-report
```

## Zapier mapping

Create a free, two-step Zap:

1. Trigger: Tally — **New Submission**, using the published form above.
2. Action: GitHub — **Create Issue** in `Asherlc/hang-ten`.

Map the Tally **Title** answer directly to the GitHub issue title. Apply the
`hangboard-report` label and use this body template, mapping each placeholder to
the same-named Tally answer or hidden field:

```markdown
## Category
{{Category}}

## Description
{{Description}}

## Hangboard context

| Field | Value |
| --- | --- |
| Board ID | `{{board_id}}` |
| Board | {{board_name}} |
| Manufacturer | {{manufacturer}} |
| Presentation ID | `{{presentation_id}}` |
| Presentation | {{presentation_name}} |
| Platform | {{platform}} |
| App version | {{app_version}} |
| Build | {{build}} |

_Submitted through the public Hang Ten hangboard report form._
```

Use a maintainer-owned GitHub connection. Zapier's current GitHub OAuth flow
requests `user`, `user:email`, `public_repo`, `repo`, `notifications`, `gist`,
and `read:org`, which is broader than the repository issue access this action
needs. Review and explicitly accept that scope before authorizing it; otherwise
use a repository-scoped intermediary instead. Never place a GitHub token in
Tally, either app, a build setting, this document, or another repository file.

Turn the Zap on only after its test action creates an issue with the correct
repository and label. The Zapier free plan is sufficient for this two-step
workflow, subject to the account's current task allowance.

## Release configuration

Use the exact published form URL for both clients:

```text
HANGBOARD_REPORT_FORM_URL=https://tally.so/r/<published-form-id>
```

The clients append only the eight hidden query keys through their platform URL
APIs. Treat configuration as invalid unless it is HTTPS and its host is
`tally.so` or a subdomain of `tally.so`.

## Acceptance test

Use an audited board with more than one source-supported physical presentation.
Select a non-default presentation in the app, open the report form, and submit
a clearly marked verification response with these checks:

1. Category is one of the three contract values; Title and Description are
   required; the reCAPTCHA appears immediately before Submit.
2. The form has exactly the eight expected context values. None are editable.
3. The submission creates one issue in `Asherlc/hang-ten` with the entered Title
   as its title.
4. The issue body contains Category, Description, `board_id`, `board_name`,
   `manufacturer`, `presentation_id`, `presentation_name`, `platform`,
   `app_version`, and `build`, without an interface-orientation field.
5. The issue has the `hangboard-report` label.
6. Repeat the launch check on both iOS and Android in portrait and landscape;
   the selected physical presentation and all eight context values remain the
   same.

Record the test issue URL and the date here after the live workflow is enabled:

- Verification issue: **Pending GitHub OAuth authorization and Zap activation.**

If a submission does not create an issue, leave the Zap off and inspect its
task history. Re-test from Tally before enabling the client build configuration.
