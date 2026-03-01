"""
Generated from intent: collection_modal_close
Generated at: 2026-02-28T23:35:29Z
System version: d11cf4c
Intent hash: f6e5c44e1ec1f7e9
"""


def steps(harness):
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(1) > td:nth-of-type(1)")
    harness.click_by_text("×")
    harness.screenshot("final_state")
