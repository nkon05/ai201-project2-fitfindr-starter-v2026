"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""
import re
import config  # noqa: F401 — you'll use this in search_listings
from generate import generate
from utils.data_loader import load_listings

# ── Helper for Size Matching ──────────────────────────────────────────────────

def _matches_size(target_size: str, listing_size: str | None) -> bool:
    """
    Check if a listing matches the requested size.
    Splits compound/composite sizes like "S/M" or "M, L" using delimiters,
    avoiding false positives like 's' in 'us 9' or 'l' in 'xl'.
    """
    if not listing_size:
        return False

    norm_target = target_size.strip().lower()
    # Split listing size into discrete tokens on slashes, commas, spaces, dashes
    tokens = [t.strip().lower() for t in re.split(r"[/,\s\-]+", listing_size) if t.strip()]
    return norm_target in tokens


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.
    """
    all_listings = load_listings()
    query_words = set(re.findall(r"\w+", description.lower()))

    scored_listings = []
    limit = getattr(config, "SEARCH_RESULT_LIMIT", 10)

    for item in all_listings:
        # 1. Price filter
        if max_price is not None:
            item_price = item.get("price")
            if item_price is None or float(item_price) > max_price:
                continue

        # 2. Size filter (token-aware match)
        if size is not None:
            if not _matches_size(size, item.get("size")):
                continue

        # 3. Keyword scoring over title, description, category, style_tags, colors, and brand
        searchable_text = " ".join([
            str(item.get("title", "")),
            str(item.get("description", "")),
            str(item.get("category", "")),
            " ".join(item.get("style_tags", []) or []),
            " ".join(item.get("colors", []) or []),
            str(item.get("brand", "") or ""),
        ]).lower()

        listing_words = set(re.findall(r"\w+", searchable_text))
        score = len(query_words.intersection(listing_words))

        # 4. Drop listings scoring zero
        if score > 0:
            scored_listings.append((score, item))

    # 5. Sort by score descending and return up to limit
    scored_listings.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored_listings[:limit]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.
    """
    items = wardrobe.get("items", []) if isinstance(wardrobe, dict) else []

    item_title = new_item.get("title", "Unknown Item")
    item_category = new_item.get("category", "Clothing")
    item_color = ", ".join(new_item.get("colors", [])) or "N/A"
    item_style = ", ".join(new_item.get("style_tags", [])) or "Vintage/Thrift"

    # Step 1 & 2: Empty wardrobe fallback -> general styling advice
    if not items:
        prompt = (
            f"You are a personal stylist. The user is considering purchasing this thrifted item:\n"
            f"- Title: {item_title}\n"
            f"- Category: {item_category}\n"
            f"- Colors: {item_color}\n"
            f"- Style: {item_style}\n\n"
            "The user's wardrobe is currently empty. Provide 2 general, versatile outfit ideas "
            "and styling suggestions on how to style this item with wardrobe essentials."
        )
        return generate(prompt)

    # Step 3: Specific combinations naming wardrobe pieces
    wardrobe_list = []
    for piece in items:
        p_name = piece.get("name") or piece.get("title", "Item")
        p_cat = piece.get("category", "General")
        p_color = piece.get("color") or ", ".join(piece.get("colors", [])) or ""
        wardrobe_list.append(f"- {p_name} ({p_cat}, {p_color})")

    wardrobe_str = "\n".join(wardrobe_list)

    prompt = (
        f"You are a personal stylist. The user found this thrifted item:\n"
        f"- Title: {item_title} ({item_category}, Colors: {item_color}, Style: {item_style})\n\n"
        f"The user already owns these items in their wardrobe:\n"
        f"{wardrobe_str}\n\n"
        "Suggest 1-2 distinct outfits that combine the thrifted item with specific pieces "
        "they already own. Mention the specific pieces from their wardrobe by name."
    )
    return generate(prompt)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.
    """
    # 1. Guard against empty or whitespace-only outfit
    if not outfit or not outfit.strip():
        return (
            f"Snagged this {new_item.get('title', 'piece')} for ${new_item.get('price', 0):.2f} "
            f"on {new_item.get('platform', 'thrift')}! Still brainstorming how to style it, but the vibe is unmatched."
        )

    title = new_item.get("title", "thrift find")
    price = new_item.get("price", 0.0)
    platform = new_item.get("platform", "online thrift")
    tags = ", ".join(new_item.get("style_tags", []))

    prompt = (
        f"Write a catchy, authentic social post caption (2 to 4 sentences) sharing a thrift find.\n"
        f"Item: {title}\n"
        f"Price: ${price:.2f}\n"
        f"Platform: {platform}\n"
        f"Style Tags: {tags}\n"
        f"Planned Outfit Styling:\n{outfit}\n\n"
        "Requirements:\n"
        "- Exactly 2 to 4 sentences.\n"
        "- Mention the item, its price, and the platform once each.\n"
        "- Sound like an authentic post by someone excited about their find, not a corporate product listing.\n"
        "- Capture the vibe and how it fits into the outfit."
    )
    return generate(prompt)
