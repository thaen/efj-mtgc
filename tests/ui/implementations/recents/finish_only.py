"""
Generated from intent: finish_only
Generated at: 2026-03-01T00:28:16Z
System version: d11cf4c
Intent hash: fb07598291a61f30
"""


def steps(harness):
    harness.click_by_text("24h")
    harness.click_by_selector("#grid > div:nth-of-type(2) > div:nth-of-type(1) > span:nth-of-type(1)")
    harness.screenshot("final_state")
