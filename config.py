import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]

MODEL_PRO = "gemini-2.5-flash"
MODEL_FLASH = "gemini-2.5-flash"

#RESOLUTION_CONFIDENCE_THRESHOLD = 0.75

# Confidence threshold for auto-resolution vs escalation.
# Empirically tuned against gemini-embedding-001 output on the seeded
# knowledge base, not an assumed value. General-purpose embedding models
# (including Google's) produce cosine similarity scores for genuinely
# related but non-identical text in roughly the 0.55 to 0.80 range, rather
# than near 1.0. A true match between a ticket summary and a relevant
# article will rarely score above 0.80, since the two texts describe the
# same problem using different structure and vocabulary, not the same
# text twice. Unrelated text (a coffee machine ticket against IT articles)
# still scored 0.601 in testing, meaning the model captures general topical
# closeness (both are "something broken in an office") even without a
# real conceptual match. This narrows the usable separation band and is
# why the threshold sits at 0.65 rather than a higher, more intuitive-looking
# number like 0.75, which would incorrectly reject genuine matches.


RESOLUTION_CONFIDENCE_THRESHOLD = 0.65