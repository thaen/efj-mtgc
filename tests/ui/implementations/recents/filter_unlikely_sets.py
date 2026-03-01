"""
Generated from intent: filter_unlikely_sets
Generated at: 2026-03-01T00:27:50Z
System version: d11cf4c
Intent hash: 4ff517cac28d62e9
"""


def steps(harness):
    harness.click_by_text("24h")
    harness.click_by_text("Arenson's Aura")
    harness.click_by_selector("#acc-candidates-3 > div:nth-of-type(1)")
    harness.screenshot("final_state")
