"""
Generated from intent: recent_accordion_toggle
Generated at: 2026-03-01T00:27:13Z
System version: d11cf4c
Intent hash: 5edcf5e695dfe275
"""


def steps(harness):
    harness.click_by_text("24h")
    harness.click_by_text("Foil")
    harness.click_by_text("Foil")
    harness.screenshot("final_state")
