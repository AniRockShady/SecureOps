import uuid
from intake_agent import run_intake_agent
from knowledge_retrieval_agent import run_knowledge_retrieval_agent
from resolution_agent import run_resolution_agent
from knowledge_extraction_agent import run_knowledge_extraction_agent


def run_flywheel_test():
    # Step 1: a ticket that will not match the original seed articles well,
    # forcing an escalation, followed by a manual resolution being fed to
    # the extraction agent as if a human resolved it after escalation.
    trace_id = str(uuid.uuid4())
    text = "The office badge reader at the main entrance is not scanning employee ID cards."

    intake_result = run_intake_agent(
        raw_request=text,
        user_id="test_user",
        company_id="test_company",
        trace_id=trace_id,
    )
    print(f"Ticket created: {intake_result['ticket_id']}, category: {intake_result['category']}")

    retrieval_result = run_knowledge_retrieval_agent(
        ticket_id=intake_result["ticket_id"],
        category=intake_result["category"],
        summary=intake_result["summary"],
        trace_id=trace_id,
    )
    print(f"Retrieval confidence: {retrieval_result['confidence']:.3f}")

    # Simulate a human-provided resolution, since this ticket is expected
    # to escalate rather than auto-resolve.
    manual_resolution = (
        "The badge reader firmware was out of date. Technician updated the "
        "firmware via the access control management console and re-synced "
        "the device with the identity provider. Reader is now scanning "
        "correctly."
    )

    extraction_result = run_knowledge_extraction_agent(
        ticket_id=intake_result["ticket_id"],
        summary=intake_result["summary"],
        resolution_text=manual_resolution,
        trace_id=trace_id,
    )
    print(f"Article created: {extraction_result['article_created']}, article ID: {extraction_result['article_id']}")
    print()

    # Step 2: a new, similarly worded ticket submitted afterward should now
    # find the newly created article in the knowledge base.
    trace_id_2 = str(uuid.uuid4())
    follow_up_text = "Front door badge scanner is unresponsive when employees try to enter."

    intake_result_2 = run_intake_agent(
        raw_request=follow_up_text,
        user_id="test_user",
        company_id="test_company",
        trace_id=trace_id_2,
    )
    print(f"Follow-up ticket created: {intake_result_2['ticket_id']}, category: {intake_result_2['category']}")

    retrieval_result_2 = run_knowledge_retrieval_agent(
        ticket_id=intake_result_2["ticket_id"],
        category=intake_result_2["category"],
        summary=intake_result_2["summary"],
        trace_id=trace_id_2,
    )
    print(f"Follow-up retrieval confidence: {retrieval_result_2['confidence']:.3f}")
    for match in retrieval_result_2["matched_articles"]:
        print(f"  Match: {match['article_id']} (title: {match['title']}, score: {match['similarity_score']:.3f})")


if __name__ == "__main__":
    run_flywheel_test()
