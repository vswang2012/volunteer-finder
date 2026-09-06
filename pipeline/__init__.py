"""Schema, text normalization, and the merge/diff store.

Nothing in here touches the network -- that's scrapers/. Keeping the split
means the merge logic (the part that must never be wrong) is testable without
mocking a single HTTP call.
"""
