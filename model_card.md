# Model Card — PawPal AI Scheduler

## 1. Model & System Overview

| Field | Details |
|---|---|
| Base LLM | Llama 3.3 70B Versatile (via Groq API) |
| System type | RAG + Agentic Workflow |
| Original base project | Module 2 — PawPal Pet Service Scheduler |
| Language | Python 3.10+ |

---

## 2. Original Base Project

**Project name:** PawPal Pet Service Scheduler (Module 2)

The original system was a rule-based task scheduler that accepted a list of pet care
tasks (feeding, walking, grooming, medication) and an owner's available time, then
used a priority queue (heapq) to generate a basic daily plan. It had no AI integration,
no knowledge retrieval, and no mechanism to validate whether generated schedules were
safe for pets with specific health conditions.

---

## 3. New AI Features Added

### Retrieval-Augmented Generation (RAG)
A curated knowledge base (`Data/petcare_rules.txt`) contains 23 veterinary-informed
rules covering feeding, exercise, medication timing, and health conditions. Before
calling the LLM, the retriever module searches this file using keyword matching and
injects only the relevant rules into the prompt. This grounds every schedule in
domain knowledge rather than relying solely on the model's general training.

### Agentic Workflow
The system follows a transparent 4-step pipeline printed to the terminal:
- **Step 1 — Analyze:** Validates the pet profile and task list
- **Step 2 — Retrieve:** Searches the knowledge base for relevant rules (RAG)
- **Step 3 — Plan:** Calls the LLM with pet info + retrieved rules to generate a schedule
- **Step 4 — Evaluate:** Runs deterministic safety checks on the output

If evaluation fails, violation feedback is injected back into the next LLM call
(up to 3 retries), completing the agentic self-correction loop.

### Guardrails (Reliability)
A deterministic evaluator layer (`evaluator.py`) checks every generated schedule for:
- Exercise scheduled too soon after feeding (bloat risk for dogs)
- Exercise duration exceeding safe limits for heart conditions or hip dysplasia
- Medication not paired with a meal
- Missing tasks that the LLM failed to schedule

---

## 4. Intended Use

Helps pet owners generate safe, prioritized daily care schedules that respect
veterinary guidelines. Designed as a learning/portfolio project demonstrating
RAG and agentic AI patterns.

**Not intended** as a substitute for professional veterinary advice.

---

## 5. AI Collaboration During Development

### Helpful AI suggestion
When designing the `retriever.py` keyword matching logic, Claude suggested matching
in both directions — checking if the search term appears in the keyword AND if the
keyword appears in the search term. This correctly caught cases like "hip dysplasia"
matching a rule keyword of "dysplasia" that a one-direction check would have missed.

### Flawed AI suggestion
Early in the project, Copilot generated a complete README describing a fully working
RAG + agentic system with polished sample outputs — before any of that code had been
written. The README was entirely aspirational and fictional. I had to recognize that
the documented outputs were hallucinated, discard the README, build the actual system
first, and only then document what it truly does. This was the most important lesson
of the project: always build first, document what actually exists.

---

## 6. Limitations and Biases

- **Species coverage:** The knowledge base covers dogs and cats only. Birds, reptiles,
  and exotic pets are not supported and would receive incorrect or irrelevant rules.
- **Keyword retrieval is broad:** The current matcher can return too many rules because
  it uses simple string matching. A vector-embedding retriever would be more precise.
- **No memory between runs:** The system cannot learn from past schedules or improve
  over time without manual updates to the knowledge base.
- **LLM output format variability:** Gemini occasionally returns time strings in
  slightly different formats (e.g. "7:00am" vs "07:00 AM"). The parser handles this
  gracefully but it is a known inconsistency.
- **Weight and breed data underused:** The pet profile includes weight and breed fields
  that the knowledge base does not yet have specific rules for.

---

## 7. Potential Misuse and Prevention

- **Risk:** A user follows an AI-generated schedule for a pet with a serious condition
  (diabetes, post-surgery recovery) without consulting a vet.
- **Prevention:** Every output should include a visible disclaimer:
  *"This schedule is AI-generated and does not replace professional veterinary advice.
  Always consult your veterinarian for pets with medical conditions."*
- **Risk:** The knowledge base is edited to include incorrect rules, producing
  dangerous schedules.
- **Prevention:** The knowledge base file should be version-controlled and any
  changes reviewed before deployment.

---

## 8. Testing Results

| Test | Description | Result |
|---|---|---|
| TC-01 | Healthy dog — valid schedule | ✅ PASS |
| TC-02 | Dog walked 10 min after feeding — bloat risk | ✅ PASS (correctly flagged) |
| TC-03 | Dog with heart condition — 30 min walk | ✅ PASS (correctly flagged) |
| TC-04 | Senior dog — 20 min walk under limit | ✅ PASS |
| TC-05 | Empty schedule returned by LLM | ✅ PASS (correctly flagged) |
| TC-06 | Cat with arthritis — medication near meal | ✅ PASS |
| TC-07 | Dog with hip dysplasia — 25 min walk | ✅ PASS (correctly flagged) |
| TC-08 | LLM forgets to include a task | ✅ PASS (correctly flagged) |

**Summary:** 8/8 tests passed after one bug fix during development.

**Bug found during testing:** The `evaluate_schedule` function was not treating
`MISSING` task violations as hard failures — only `VIOLATION` prefixed messages
caused a failure. This meant a schedule missing an entire task would still "pass."
Fixed by adding `MISSING` to the failure condition check (one line change).

**What this showed:** Running the test harness immediately caught an integration
bug that manual testing would likely have missed. Deterministic tests are essential
when working with LLMs because they provide a stable anchor — at least one layer
of the system always behaves predictably.

---

## 9. What This Project Taught Me

**About AI:** Reliable AI systems are built around the model, not just with it.
The LLM generates creative, context-aware schedules, but without retrieval to
ground it and guardrails to validate it, the outputs are not trustworthy. The
biggest reliability improvements came from better architecture decisions, not
better prompts.

**About problem-solving:** Designing the evaluator first — defining what "correct"
looks like before writing the planner — made every subsequent decision clearer and
faster. Separation of concerns (each module has one job) made debugging fast: any
issue could be isolated to retrieval, planning, or evaluation within minutes.

**About documentation:** AI tools like Copilot are eager to help with documentation
but will describe a system that does not exist yet. Documentation must follow
implementation, never precede it, because copilot gave me some suggestions which are not 
practical for this project.

---

## 10. Future Improvements

- Replace keyword retrieval with sentence-embedding vector search for more
  precise rule matching
- Expand the knowledge base to cover birds, reptiles, and common exotic pets
- Add a simple web front-end (Streamlit) so non-technical users can input pet
  profiles without editing Python code
- Support multi-day schedule generation with recurring task tracking
- Add a confidence score to each schedule entry based on how many rules applied
