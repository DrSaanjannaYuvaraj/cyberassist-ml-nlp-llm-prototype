# CyberAssist project delivery log

## Purpose
Demonstrate AI-assisted email and security-alert analysis through
an authenticated API and browser interface.

## Completed milestones
- Synthetic email baseline and error analysis.
- Public dataset preparation with duplicate/conflicting-label handling.
- Logistic regression and PyTorch classifier comparison.
- Held-out email test evaluation.
- Independent LLM explanations and security-alert analysis.
- API and dashboard integration.
- Password hashing, expiring sessions and record ownership checks.
- Saved analyses, human reviews, history and deletion.
- Email-address masking and validation impact assessment.
- Simulated external-system API integration.
- Alert quality evaluation and repeated-input timing check.

## Verified results
- Email test set: 2,624 records.
- Logistic regression test accuracy: 97.94%.
- PyTorch test accuracy: 98.82%.
- PyTorch test false positives: 13; false negatives: 18.
- Masking validation: 387 affected emails; zero changed predictions.
- Six-alert evaluation: 4 reference matches, 2 responses with
  unsupported claims and 1 exact-quotation failure.
- Repeated alert: 5 consistent assessments, no failures,
  median 8.702 seconds.

## Current limitations
- Public dataset labels were not independently verified.
- Near-duplicates and related messages may remain across splits.
- LLM evaluation is small and synthetic.
- Redaction covers selected email-address patterns only.
- API sessions and login throttling are in-memory.
- Single-process analysis supports one API analysis at a time.
- No production deployment or actual Centerprise integration.
- No commercial staff adoption or measured productivity improvement.

## Remaining milestones
- Record actual AWS expenditure and operating assumptions.
- Prepare a user guide and demonstration script.
- Conduct a small user-training session and collect feedback.
- Document deployment, retention and recovery requirements.

## Risks and responses
- Unsupported LLM claims: expose evidence and require human review.
- Sensitive data: use synthetic demo inputs and limited redaction.
- Access leakage: enforce ownership checks on stored records.
- Compute expense: track actual AWS usage and stop unused instances.
- Overstated findings: distinguish measured results from proposed benefits.
