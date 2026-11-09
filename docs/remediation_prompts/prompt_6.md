# COS-REC-05 — Simple Research Case and Data Management

**Role:** Senior Full-Stack Engineer, Clinical Data Engineer and Form UX Designer

**Mission:** Deliver a complete, understandable case-creation and data-entry workflow.

Reuse existing case creation, patient profile, observation storage, authorization, revision and chart services.

## Tasks

1. Simplify the existing Research Cases page.
2. Make "New Research Case" the clear primary action for authorized users.
3. Replace unnecessary technical language with plain-language field labels.
4. Implement or repair the existing structured case-creation form.
5. Provide a usable patient/research profile editor.
6. Make clinical-data entry understandable and manageable.
7. Verify saving, editing, correction history and reopening.
8. Keep project and patient authorization enforced by the backend.
9. Correct loading states that hang after refresh.
10. Do not silently create records that claim to be authentic clinical observations.

## Example new-case journey

The user clicks:

**New Research Case**

The form asks:

- **Case title:** Breast Cancer Research Example A
- **Case reference:** DEMO-001
- **Record type:** Artificial demonstration
- **Research project:** Select from authorized projects
- **Description:** Optional short explanation

Only collect values supported by the existing domain contracts.

If the current schema requires a registered source, the form must provide an appropriate authorized source-selection workflow rather than inventing a source or bypassing eligibility checks.

The user clicks:

**Create Case**

Expected result:

A success confirmation and immediate navigation to the saved case's Overview.

## Example observation entry

Within that case, the user chooses:

**Add Observation → Laboratory Result**

The form asks:

- Observation type: Hemoglobin
- Measured value: 12.3
- Unit: g/dL
- Recorded date: 1 November 2026
- Evidence source: Select eligible artificial demonstration source

The entry must be labeled synthetic if it is artificial.

After saving:

- The observation appears in the case history.
- It appears in the appropriate chart.
- Refreshing the page retains it.
- An authorized correction to 12.4 retains the previous revision.

## Important authorization distinction

Do not turn a public synthetic demo session into an administrator session.

Research-case creation must still require the appropriate project role.

Where a visitor cannot create a case, explain how authorized access is obtained and provide a separate safe demo.

## Acceptance gate

Through a real browser:

1. Create Case A.
2. Save and reopen its profile.
3. Save an artificial observation.
4. Correct that observation.
5. Refresh the browser.
6. Verify the latest value and retained revision.
7. Create Case B.
8. Verify Case B cannot access Case A's protected information.
9. Sign out and verify access is revoked.

Do not mark complete if a form only renders or if saving requires manually editing the database.

Record HTTP and browser evidence.
