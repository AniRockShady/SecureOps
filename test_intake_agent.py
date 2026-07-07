import uuid
from intake_agent import run_intake_agent

TEST_CASES = [
    "The production database server is completely down, no one can access the customer portal.",
    "I forgot my password and I am locked out of my email account.",
    "My monitor flickers occasionally but I can still work fine.",
    "The shared printer on the third floor is not printing, showing offline status.",
    "Our CRM license expired yesterday and the whole sales team cannot log in.",
]


def run_tests():
    for text in TEST_CASES:
        trace_id = str(uuid.uuid4())
        result = run_intake_agent(
            raw_request=text,
            user_id="test_user",
            company_id="test_company",
            trace_id=trace_id,
        )
        print(f"Input: {text}")
        print(f"  Ticket ID: {result['ticket_id']}")
        print(f"  Category: {result['category']}")
        print(f"  Priority: {result['priority']}")
        print(f"  Affected system: {result['affected_system']}")
        print(f"  Summary: {result['summary']}")
        print()


if __name__ == "__main__":
    run_tests()