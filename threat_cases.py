"""Labelled legal-threat texts: (text, is_genuine_threat, note)."""

THREAT_CASES = [
    ("I'm going to have my lawyer look at the contract you sent me.", True, "lawyer, casual"),
    ("If this isn't fixed I will sue you.", True, "sue"),
    ("See you in court.", True, "court"),
    ("We will take legal action if not resolved by Friday.", True, "legal action"),
    ("I will send you a legal notice by Monday.", True, "legal notice (India)"),
    ("Taking this to the consumer forum next week.", True, "consumer forum (India)"),
    ("My advocate will be in touch.", True, "advocate (India)"),
    ("Escalating to the banking ombudsman today.", True, "ombudsman"),
    ("I will file a complaint with the RBI.", True, "regulator"),
    ("Lodging an FIR against your delivery agent.", True, "FIR"),
    ("I spoke to your legal team last month about an unrelated licensing question.", False, "incidental 'legal'"),
    ("Sue from your billing team was really helpful.", False, "person named Sue"),
    ("I'm not going to sue, I just want my refund.", False, "negated"),
    ("I met your rep at the food court yesterday.", False, "food court"),
    ("No lawyers needed, just fix it please.", False, "negated lawyers"),
    ("I will file a complaint about this delay.", False, "service complaint, not legal"),
    ("My package arrived a day late, no big deal.", False, "benign"),
    ("This is the legal limit for the refund, right?", False, "'legal' as adjective"),
    ("Please pass this to your legal department for the GST invoice.", False, "routine legal dept"),
    ("Can you tell me if your app is legal to use in the UAE?", False, "question about legality"),
]

# Written AFTER the classifier was finalised and never used to tune it.
# Reported honestly: v2 misses some of these. Agent overrides (precedents)
# and the live-model intent check are the designed path to close them.
HELD_OUT = [
    ("You will be hearing from my attorney.", True, "attorney"),
    ("I am filing a lawsuit tomorrow.", True, "lawsuit"),
    ("I have already contacted a consumer court lawyer.", True, "consumer court"),
    ("We are going to drag your company to court over this.", True, "drag to court"),
    ("Is there a court date for my traffic fine that you can see?", False, "court date question"),
    ("Thanks Sue, that fixed it!", False, "name Sue"),
    ("I would never take legal action over something this small.", False, "negated"),
    ("The legal name on my account is wrong, please update it.", False, "legal name"),
    ("Complaint registered with the IRDAI, reference attached.", True, "regulator, passive voice"),
    ("My brother is a lawyer and says this is fine.", False, "third-party lawyer"),
]
