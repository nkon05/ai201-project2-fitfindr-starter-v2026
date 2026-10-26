"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. That branch is the graded part of this unit.

Build and test your three tools in tools.py first. Then come here.

    python agent.py          runs both example paths below
"""

import re
import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── query parsing helper ──────────────────────────────────────────────────────

def parse_user_query(query: str) -> dict:
    """
    Parse a natural language query into description, size, and max_price.
    Uses regex patterns to extract constraints, then cleans remaining terms
    for the search description.
    """
    clean_query = query.strip()
    max_price = None
    size = None

    # 1. Extract price (e.g., "under $30", "under 30", "up to $50", "max 25")
    price_match = re.search(
        r"(?:under|below|less than|max(?:imum)?|up to)\s*\$?\s*(\d+(?:\.\d+)?)",
        clean_query,
        re.IGNORECASE,
    )
    if not price_match:
        price_match = re.search(r"\$(\d+(?:\.\d+)?)", clean_query)

    if price_match:
        try:
            max_price = float(price_match.group(1))
        except (ValueError, TypeError):
            max_price = None

    # 2. Extract size (e.g., "size M", "size: XL", "size small", standalone XXS/XS/S/M/L/XL/XXL)
    size_match = re.search(
        r"\bsize\s*[:\-]?\s*([a-zA-Z0-9/]+|\b(?:small|medium|large|extra large)\b)",
        clean_query,
        re.IGNORECASE,
    )
    if not size_match:
        size_match = re.search(
            r"\b(XXS|XS|S|M|L|XL|XXL|2XL|3XL)\b",
            clean_query,
            re.IGNORECASE,
        )

    if size_match:
        raw_size = size_match.group(1).strip()
        size_mapping = {
            "small": "S",
            "medium": "M",
            "large": "L",
            "extra large": "XL",
        }
        size = size_mapping.get(raw_size.lower(), raw_size.upper())

    # 3. Clean query into a keywords description by stripping extracted tokens & filler
    cleaned_desc = clean_query
    if price_match:
        cleaned_desc = cleaned_desc.replace(price_match.group(0), " ")
    if size_match:
        cleaned_desc = cleaned_desc.replace(size_match.group(0), " ")

    filler_patterns = [
        r"\blooking for\b",
        r"\bi want\b",
        r"\bfind me\b",
        r"\bsearch for\b",
        r"\bunder\b",
        r"\bsize\b",
    ]
    for pattern in filler_patterns:
        cleaned_desc = re.sub(pattern, " ", cleaned_desc, flags=re.IGNORECASE)

    cleaned_desc = re.sub(r"\s+", " ", cleaned_desc).strip()

    return {
        "description": cleaned_desc if cleaned_desc else query.strip(),
        "size": size,
        "max_price": max_price,
    }


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for in natural language.
        wardrobe: a wardrobe dict.

    Returns:
        The session dict. If session["error"] is not None, the run ended early.
    """
    session = new_session(query, wardrobe)
    iteration_count = 0

    try:
        # Step 1: Parse user query and save to session
        iteration_count += 1
        trace.check_iterations(iteration_count)

        session["parsed"] = parse_user_query(session["query"])

        # Step 2: Read from session["parsed"] to run search_listings
        search_inputs = {
            "description": session["parsed"]["description"],
            "size": session["parsed"]["size"],
            "max_price": session["parsed"]["max_price"],
        }
        search_output = search_listings(**search_inputs)
        session["search_results"] = search_output
        trace.step("search_listings", inputs=search_inputs, returned=search_output)

        # ── BRANCH RULE ──────────────────────────────────────────────────────────
        # If search_listings returns an empty list, put a helpful message in session
        # naming what to change, and stop. Do NOT proceed to suggest_outfit.
        if not session["search_results"]:
            critique = []
            parsed = session["parsed"]
            if parsed.get("max_price") is not None:
                critique.append(f"raising your price ceiling above ${parsed['max_price']:.2f}")
            if parsed.get("size") is not None:
                critique.append(f"widening your size filter beyond '{parsed['size']}'")
            if parsed.get("description"):
                critique.append(f"using broader keywords than '{parsed['description']}'")

            suggestions = ", ".join(critique) if critique else "loosening your search criteria"
            session["error"] = (
                f"No items matched your search criteria. Try {suggestions}."
            )
            return session
        # ─────────────────────────────────────────────────────────────────────────

        # Step 3: Pick the first item from session["search_results"] and store it
        session["selected_item"] = session["search_results"][0]

        # Step 4: Read session["selected_item"] and session["wardrobe"] for suggest_outfit
        iteration_count += 1
        trace.check_iterations(iteration_count)

        outfit_inputs = {
            "new_item": session["selected_item"],
            "wardrobe": session["wardrobe"],
        }
        outfit_output = suggest_outfit(**outfit_inputs)
        session["outfit_suggestion"] = outfit_output
        trace.step("suggest_outfit", inputs=outfit_inputs, returned=outfit_output)

        # Step 5: Read session["outfit_suggestion"] and session["selected_item"] for create_fit_card
        iteration_count += 1
        trace.check_iterations(iteration_count)

        fit_card_inputs = {
            "outfit": session["outfit_suggestion"],
            "new_item": session["selected_item"],
        }
        fit_card_output = create_fit_card(**fit_card_inputs)
        session["fit_card"] = fit_card_output
        trace.step("create_fit_card", inputs=fit_card_inputs, returned=fit_card_output)

    except ModelUnavailable as e:
        session["error"] = f"Model service temporarily unavailable: {e}"
        return session
    except Exception as e:
        session["error"] = f"Agent stopped due to an error: {str(e)}"
        return session

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )