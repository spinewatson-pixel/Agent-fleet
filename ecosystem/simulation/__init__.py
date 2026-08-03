"""Test doubles for verification. NOT the real backend.

Everything in this package exists so the agent chains can be exercised
end-to-end without the claude CLI and without nursing_api. The doubles are
deliberately dumb: they return fixed, obviously synthetic text. They prove the
*wiring* — stage order, carry accumulation, prompt placement, database writes,
scoring — and they prove nothing whatsoever about content quality.

Nothing in the shipped stack imports this package.
"""
