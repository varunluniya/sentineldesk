# Ticket Escalation Policy

## Rule 1: SLA breach risk
A ticket older than 48 hours escalates. The boundary is applied literally: 47.9 hours does not escalate, 48.01 does.

## Rule 2: Premium tier
Every ticket from a premium-tier customer escalates, because of the contractual priority in premium agreements.

## Rule 3: Genuine legal threat
Escalate when the customer threatens legal or regulatory action against the company: suing, a lawyer or advocate, a legal notice,
court, a consumer forum or commission, the banking ombudsman, small claims, filing a case or FIR, or a complaint to a regulator (RBI, SEBI, IRDAI) or the police.
A passing mention is not a threat: the company's own legal team, a negated statement ("I'm not going to sue"), a person named Sue, or a food court.
When a live model is configured, it classifies intent as well. If the model and the rules disagree, escalate and mark the ticket for a human check.

## Rule 4: High refund
A refund request above 5,000 escalates because of the financial exposure. The boundary is applied literally.

## Rule 5: Repeat contact
A customer opening their third ticket within 7 days escalates. A pattern of repeat contact signals the problem is not being solved at first touch,
and repeat contacts drive churn more than any single ticket does.

## Precedents
When an agent corrects the legal-threat judgement on a ticket, that ticket becomes a precedent.
A new ticket that closely resembles a precedent where escalation was needed also escalates.
A precedent can add an escalation or a human check. It never silently removes one.

## Policy changes
Numeric thresholds (48 hours, 5,000) and tier rules are policy. Agent overrides are tracked per rule,
and a high override rate is reported for the support lead to review. Thresholds are never changed automatically.
