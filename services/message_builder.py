from services.decision import decide_action
from services.llm import generate_message
from services.prompt_builder import build_prompt
from store import contexts


def build_message_rule(merchant, trigger):
    action = decide_action(merchant)

    identity = merchant.get("identity", {})
    performance = merchant.get("performance", {})
    signals = merchant.get("signals", [])
    offers = merchant.get("offers", [])
    history = merchant.get("conversation_history", [])
    customer_data = merchant.get("customer_aggregate", {})
    subscription = merchant.get("subscription", {})

    name = identity.get("owner_first_name", "there")
    ctr = performance.get("ctr", 0)

    stale = any("stale_posts" in s for s in signals)
    low_ctr = any("ctr_below_peer_median" in s for s in signals)

    interested_topic = ""
    for msg in history:
        body = msg.get("body", "").lower()
        if "whitening" in body and "whitening" not in interested_topic:
            interested_topic += "whitening"
        if "aligners" in body:
            interested_topic = f"{interested_topic} and aligners" if interested_topic else "aligners"

    active_offer = None
    for offer in offers:
        if offer.get("status") == "active":
            active_offer = offer.get("title")
            break

    high_risk = customer_data.get("high_risk_adult_count", 0)

    if stale and low_ctr:
        return (
            f"{name}, your CTR ({ctr:.1%}) is currently below similar clinics "
            f"and your last post appears outdated.\n\n"
            f"You previously showed interest in {interested_topic} content.\n\n"
            f"I can generate 3 ready-to-publish posts and promote "
            f"your active offer ({active_offer}) to "
            f"{high_risk} high-intent customers.\n\n"
            f"Generate campaign drafts?"
        )

    if action == "renewal":
        days = subscription.get("days_remaining", 0)
        lapsed = customer_data.get("lapsed_180d_plus", 0)
        return (
            f"{name}, your Pro plan expires in {days} days and recent performance has declined.\n\n"
            f"You currently have no active offers and {lapsed} past customers have not returned recently.\n\n"
            f"I can help create a renewal strategy, a new patient offer, and a re-engagement campaign.\n\n"
            f"Would you like me to prepare it?"
        )

    if action == "offer":
        return (
            f"{name}, you currently have no active offers.\n\n"
            f"Creating a limited-time promotion could help increase visibility and attract new customers.\n\n"
            f"Would you like me to suggest an offer?"
        )

    if action == "performance":
        views_change = performance.get("delta_7d", {}).get("views_pct", 0)
        return (
            f"{name}, your business visibility has dropped over the last week ({views_change:.0%}).\n\n"
            f"I can identify the biggest causes and suggest actions to improve discovery and lead generation.\n\n"
            f"Would you like a performance review?"
        )

    if action == "growth":
        return (
            f"{name}, your business is outperforming similar businesses in your area.\n\n"
            f"Views and customer engagement are growing.\n\n"
            f"I noticed local demand trends that could help you attract even more customers.\n\n"
            f"Would you like a growth campaign suggestion?"
        )

    if action == "winback":
        lapsed = customer_data.get("lapsed_90d_plus", 0)
        return (
            f"{name}, your subscription has expired and business visibility appears to have declined.\n\n"
            f"You also have {lapsed} past customers who have not returned recently.\n\n"
            f"I can prepare a win-back campaign and profile recovery plan.\n\n"
            f"Would you like me to prepare it?"
        )

    if action == "trial":
        days = subscription.get("days_remaining", 0)
        return (
            f"{name}, your trial ends in {days} days.\n\n"
            f"You already have an active promotion and local demand opportunities available.\n\n"
            f"I can help create a campaign before the trial expires.\n\n"
            f"Would you like suggestions?"
        )

    return f"Hi {name}, I found a few growth opportunities for your business. Would you like a quick review?"


def build_message(merchant, trigger):
    try:
        action = decide_action(merchant)
        category_slug = merchant.get("category_slug")
        category = contexts["category"].get(category_slug, {})

        customer_id = trigger.get("customer_id")
        customer = contexts["customer"].get(customer_id) if customer_id else None

        category["recommended_action"] = action
        prompt = build_prompt(
            category=category,
            merchant=merchant,
            trigger=trigger,
            customer=customer
        )

        ai_message = generate_message(prompt)
        if ai_message and len(ai_message.strip()) > 20:
            return ai_message
    except Exception:
        pass

    return build_message_rule(merchant, trigger)