"""
Generated from intent: batch_ingest
Generated at: 2026-03-01T00:35:33Z
System version: d11cf4c
Intent hash: 7beae9737fd744eb
"""


def steps(harness):
    harness.click_by_text("24h")
    harness.click_by_selector("#grid > div:nth-of-type(1)")
    harness.click_by_selector("Replace with...")
    harness.fill_by_placeholder("Replace with...", "Lightning Bolt")
    harness.scroll("down")
    harness.fill_by_placeholder("Replace with...", "Black Lotus")
    harness.click_by_text("Batch Ingest")
    harness.click_by_text("Collection")
    harness.fill_by_placeholder("Search cards...", "Armed Response")
    harness.screenshot("final_state")
