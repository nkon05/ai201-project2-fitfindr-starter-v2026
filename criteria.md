# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
The search tool relies on straightforward keyword overlap rather than semantic vector embeddings, so certain natural-language query variations or synonyms may return a score of zero despite relevant items existing. Allowing 1 out of 5 to fail accounts for lexical mismatch and occasional model formatting hiccups while still holding the end-to-end pipeline accountable.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This is a deterministic code branch rather than an LLM guessing game: `search_listings` explicitly returns an empty list `[]` when no items match, so the control loop has a strict boolean condition to guard the next call. Because checking `if not results:` involves no probabilistic model generation, anything less than 100% reliability indicates a core logic bug.

---

## 3. Something about state

When `search_listings` returns one or more results, the dictionary passed as `new_item` into `suggest_outfit` has an `id` that matches the `id` of `session["selected_item"]` — in 5 of 5 tries.

**Why this target:**
Passing data across tools through agent session state is purely deterministic state management. If the agent hallucinates an arbitrary item ID or pulls a stale dictionary from a previous query, the entire downstream outfit recommendation becomes irrelevant, making a strict 5 of 5 requirement essential.


---

## 4. Something about the fit card

Across 5 runs using different valid listings and outfits, the generated fit card contains between 2 and 4 sentences, explicitly cites the item's price and platform, and produces a unique opening sentence for each distinct item — in at least 4 of 5 runs.

**Why this target:**
Because `create_fit_card` calls an LLM with non-zero temperature, phrasing naturally varies and the model might occasionally omit a requested detail like the platform or spill into a fifth sentence. A 4 of 5 target ensures the prompt instructions and grounding constraints are robust without failing the entire suite over an isolated generative quirk.


---

## 5. Your choice

Given a valid matching listing but a wardrobe where `wardrobe["items"]` is an empty list `[]`, `suggest_outfit` returns general standalone styling advice without throwing an exception or returning an empty string, and `create_fit_card` completes successfully — in 5 of 5 tries.

**Why this target:**
Thrift platforms frequently have first-time users who have not yet added pieces to their digital closet. The empty check (`if not wardrobe.get("items"):`) is explicit Python branch logic that can be handled deterministically with a fallback styling prompt, so it should never crash or return empty output.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
