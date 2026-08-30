# Hangboard Issue Reporting Design

## Goal

Let anyone report an issue with a Hang Ten hangboard without needing a GitHub
account. Each submitted report becomes a triage-ready GitHub issue in
`Asherlc/hang-ten`.

## Scope

Ship the report entry point in both iOS and Android. Reports are text-only in
this release. The form collects no contact information and has no attachment
support.

Platform parity is required: when an iOS hangboard-facing flow is added or
changed for this feature, Android must expose the equivalent capability and
destination rather than a reduced alternative. Existing repository board data
is a review-target inventory only, never evidence for physical orientation,
hold usability, or presentation assignment.

## Architecture

Tally hosts the public report form. Its URL accepts URL-encoded hidden fields,
which each app supplies when opening the system browser:

| Hidden field | Source |
| --- | --- |
| `board_id` | Canonical selected board ID |
| `board_name` | Selected board display name |
| `manufacturer` | Selected board manufacturer |
| `presentation_id` | Selected board face or variant ID |
| `presentation_name` | Selected board face or variant display name |
| `platform` | `iOS` or `Android` |
| `app_version` | Installed app marketing version |
| `build` | Installed build/version code |

The visible Tally fields are a required category, title, and description. The
category values are `Incorrect hold/specification`, `Missing or incorrect
board`, and `Other`. Tally reCAPTCHA is placed immediately before Submit.

A two-step Zap uses Tally's new-submission trigger and GitHub's create-issue
action. It creates an issue in `Asherlc/hang-ten`, applies the
`hangboard-report` label, uses the submitted title, and formats the body as
Markdown containing the category, description, and hidden board/app context.
The Zap's GitHub connection is a maintainer-owned credential; reporters do not
authenticate with GitHub.

## App Behavior

Each hangboard detail page includes a `Report a hangboard issue` action with
brief supporting copy that says it opens a report form. iOS adds the action to
its existing hold-specification detail screen. Android adds a board-details
screen, reached from the selected-board card, and presents the action there so
the two platforms provide the same board-specific destination. A board with
multiple presentations offers its face or variant selector on both platforms;
the active physical presentation is included in the report context. Both detail
screens remain usable in portrait and landscape, with no report control clipped
or hidden. The apps open the form in the system browser, not an embedded web view.
The form URL is platform configuration rather than a UI literal. If it is
absent or malformed, the action is unavailable. If opening the valid URL fails,
the app presents a retryable error.

The iOS and Android URL builders use exactly the hidden-field names above and
URL-encode every value. They add no device identifier, account data, device
orientation, workout history, or location data.

## Catalog orientation audit

Before the reporting action ships, audit each existing catalog package against
independently discovered primary manufacturer evidence. For every candidate
physical product, manually review the complete current manufacturer product
page, gallery, manuals, numbered hold guides, and directly linked images. The
repository's package, assets, and prior source audit can identify a review
target but cannot establish a fact or substitute for this research.

Record the reviewed URLs, date, exact image/view roles, physical revision,
supported faces/sides/mounting orientations, and hold-to-presentation mappings
in a new source audit. A visible hold that is usable only after a physical
rotation, inversion, reversal, or face change must be represented by the
corresponding clearly named presentation and scoped to it. Do not infer a
physical orientation, grip fact, measurement, or geometry solely from an image;
when primary evidence is incomplete, record the limitation and omit the
unsupported presentation or field. Different physical revisions remain
separate packages; faces, sides, and orientations of the same revision remain
presentations of one package.

## Provisioning

Before enabling the app action:

1. Complete and validate the independent catalog orientation audit.
2. Create and publish the Tally form with the three visible fields, eight hidden
   fields, and reCAPTCHA.
3. Create the `hangboard-report` label in `Asherlc/hang-ten`.
4. Connect the maintainer-owned GitHub credential to Zapier and configure the
   two-step Tally-to-GitHub Zap.
5. Set the published form URL in both app configurations.
6. Submit a test report and verify the resulting issue body and label.

Tally is free for the needed form features and unlimited submissions under its
fair-use policy. Zapier's free tier permits a two-step Zap and 100 successful
actions per month, so each created issue consumes one task. If the free task
limit is reached, Zapier holds subsequent Zap runs; maintainers must upgrade or
replay held reports after capacity returns.

## Failure Handling

The apps can only report browser-launch failures; after a browser hand-off,
Tally and Zapier own delivery. Tally's validation and reCAPTCHA prevent blank
and basic automated submissions. Zapier failures must be monitored in its Zap
history and replayed there when appropriate. The public form must not promise
that every report is immediately visible on GitHub.

## Testing

- Catalog tests verify every audited physical orientation has a source-audit
  mapping and every presentation-scoped hold belongs to supported evidence.
- iOS unit tests verify complete report URL construction and encoding for every
  audited presentation, and UI tests verify the detail-page action is visible
  only with configuration in portrait and landscape.
- Android unit tests verify the same URL contract for every audited
  presentation, and UI tests verify the new board-details destination, its
  presentation selector, and report action in both layouts.
- A documented manual provisioning test submits a representative form response
  and verifies a labelled GitHub issue with the expected Markdown body.

## Non-goals

- In-app issue submission or a new backend.
- Reporter GitHub authentication.
- Screenshots, file uploads, email collection, or reporter follow-up.
- Automatic duplicate detection or issue prioritization.
